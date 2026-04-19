"""Service Microsoft Graph : OAuth (MSAL) + appels REST via httpx.

Design :
- `MicrosoftOAuthService` gère le flux de consentement (authorize URL +
  exchange du code).
- `MicrosoftGraphService` est instancié avec un access token valide, fourni
  par l'appelant (route ou worker). Le token est résolu via
  `MicrosoftIntegrationService.get_valid_access_token` pour l'auto-refresh.
"""

from typing import Any

import httpx
import msal

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.microsoft_integration import (
    MicrosoftIntegrationError,
    MicrosoftIntegrationService,
)
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class MicrosoftOAuthService:
    """Gère le flux OAuth 'authorization code' pour les comptes Microsoft 365."""

    def __init__(self) -> None:
        s = SettingsService()
        self._client_id = s.get_platform("microsoft.client_id")
        self._client_secret = s.get_platform("microsoft.client_secret")
        self._tenant_id = s.get_platform("microsoft.tenant_id") or "common"
        self._redirect_uri = s.get_platform("microsoft.redirect_uri")
        self._scopes = s.get_platform("microsoft.graph_scopes").split()

        if not self._client_id or not self._client_secret:
            raise MicrosoftIntegrationError(
                "Microsoft 365 non configuré — renseigner microsoft.client_id et "
                "microsoft.client_secret dans l'admin plateforme."
            )

        self._app = msal.ConfidentialClientApplication(
            client_id=self._client_id,
            client_credential=self._client_secret,
            authority=f"https://login.microsoftonline.com/{self._tenant_id}",
        )

    def build_authorize_url(self, state: str) -> str:
        return self._app.get_authorization_request_url(
            scopes=self._scopes,
            state=state,
            redirect_uri=self._redirect_uri,
        )

    def exchange_code(self, code: str) -> dict[str, Any]:
        """Échange le code d'autorisation contre des tokens MSAL."""
        result = self._app.acquire_token_by_authorization_code(
            code=code,
            scopes=self._scopes,
            redirect_uri=self._redirect_uri,
        )
        if "error" in result:
            logger.error("ms.oauth.exchange_error", error=result.get("error_description"))
            raise MicrosoftIntegrationError(result.get("error_description", "Échec OAuth"))
        return result


class MicrosoftGraphService:
    """Wrapper REST minimal — reçoit un access token déjà valide."""

    def __init__(self, access_token: str) -> None:
        if not access_token:
            raise MicrosoftIntegrationError("Access token manquant")
        self._token = access_token
        self._client = httpx.AsyncClient(
            base_url=GRAPH_BASE,
            timeout=30,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def _get(self, path: str, **params: Any) -> dict[str, Any]:
        r = await self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    async def list_upcoming_events(
        self, start: str, end: str, top: int = 50
    ) -> list[dict[str, Any]]:
        data = await self._get(
            "/me/calendarView",
            startDateTime=start,
            endDateTime=end,
            **{"$orderby": "start/dateTime", "$top": top},
        )
        return data.get("value", [])

    async def list_sent_messages(self, top: int = 20) -> list[dict[str, Any]]:
        """Derniers messages envoyés (sentItems) — pour auto-détecter la signature."""
        data = await self._get(
            "/me/mailFolders/sentitems/messages",
            **{
                "$top": top,
                "$orderby": "sentDateTime desc",
                "$select": "id,subject,body,sentDateTime",
            },
        )
        return data.get("value", [])

    async def list_inbox_messages(self, top: int = 25) -> list[dict[str, Any]]:
        data = await self._get(
            "/me/mailFolders/inbox/messages",
            **{"$top": top, "$orderby": "receivedDateTime desc"},
        )
        return data.get("value", [])

    async def list_inbox_since(
        self, since_iso: str, top: int = 200
    ) -> list[dict[str, Any]]:
        """Messages inbox reçus depuis une date donnée — pour l'import historique."""
        data = await self._get(
            "/me/mailFolders/inbox/messages",
            **{
                "$top": top,
                "$orderby": "receivedDateTime desc",
                "$filter": f"receivedDateTime ge {since_iso}",
                "$select": "id,conversationId,subject,from,receivedDateTime,bodyPreview",
            },
        )
        return data.get("value", [])

    async def get_message(self, message_id: str) -> dict[str, Any]:
        """Récupère le détail d'un message (headers + body)."""
        return await self._get(f"/me/messages/{message_id}")

    async def list_conversation_messages(
        self, conversation_id: str, top: int = 5, exclude_id: str | None = None
    ) -> list[dict[str, Any]]:
        """Messages d'un même fil de discussion (conversationId), du plus récent au plus ancien.

        Utilisé pour injecter l'historique complet lors de la rédaction d'un brouillon.
        """
        if not conversation_id:
            return []
        data = await self._get(
            "/me/messages",
            **{
                "$filter": f"conversationId eq '{conversation_id}'",
                "$orderby": "receivedDateTime desc",
                "$top": top + (1 if exclude_id else 0),
                "$select": "id,subject,from,receivedDateTime,bodyPreview,body",
            },
        )
        items = data.get("value", [])
        if exclude_id:
            items = [m for m in items if m.get("id") != exclude_id]
        return items[:top]

    async def create_reply_draft(self, message_id: str) -> dict[str, Any]:
        """Crée un brouillon de réponse dans Outlook et le renvoie."""
        r = await self._client.post(f"/me/messages/{message_id}/createReply")
        r.raise_for_status()
        return r.json()

    async def update_message_body(
        self, message_id: str, html_body: str
    ) -> dict[str, Any]:
        """Patche le body d'un message (typiquement un brouillon qu'on vient de créer)."""
        r = await self._client.patch(
            f"/me/messages/{message_id}",
            json={"body": {"contentType": "HTML", "content": html_body}},
        )
        r.raise_for_status()
        return r.json()

    async def send_mail(
        self, to: str, subject: str, html_body: str, save_to_sent: bool = True
    ) -> None:
        """Envoie un email depuis la BAL de l'utilisateur courant (via /me/sendMail)."""
        payload = {
            "message": {
                "subject": subject,
                "body": {"contentType": "HTML", "content": html_body},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": save_to_sent,
        }
        r = await self._client.post("/me/sendMail", json=payload)
        r.raise_for_status()

    async def resolve_user_id(self, email: str) -> str | None:
        """Retourne l'id Azure AD d'un user par email, ou None si introuvable."""
        try:
            r = await self._client.get(f"/users/{email}")
            r.raise_for_status()
            return r.json().get("id")
        except httpx.HTTPStatusError:
            return None

    async def create_online_meeting(
        self, *, subject: str, start_iso: str, end_iso: str
    ) -> dict[str, Any]:
        """Crée une réunion Teams ad-hoc et renvoie joinUrl + id."""
        payload = {
            "subject": subject,
            "startDateTime": start_iso,
            "endDateTime": end_iso,
        }
        r = await self._client.post("/me/onlineMeetings", json=payload)
        r.raise_for_status()
        return r.json()

    async def create_planner_task(
        self,
        *,
        plan_id: str,
        title: str,
        due_date_iso: str | None = None,
        assignee_user_id: str | None = None,
        bucket_id: str | None = None,
    ) -> dict[str, Any]:
        """Crée une tâche dans un plan Microsoft Planner.

        `plan_id` et `bucket_id` s'obtiennent via l'UI Planner ou Graph :
        `/me/planner/plans`, `/planner/plans/{id}/buckets`.
        """
        body: dict[str, Any] = {"planId": plan_id, "title": title}
        if bucket_id:
            body["bucketId"] = bucket_id
        if due_date_iso:
            body["dueDateTime"] = due_date_iso
        if assignee_user_id:
            body["assignments"] = {
                assignee_user_id: {"@odata.type": "#microsoft.graph.plannerAssignment", "orderHint": " !"}
            }
        r = await self._client.post("/planner/tasks", json=body)
        r.raise_for_status()
        return r.json()

    @classmethod
    async def for_user(cls, tenant_id: str, user_id: str) -> "MicrosoftGraphService":
        """Construit une instance en résolvant le token via l'IntegrationService."""
        token = MicrosoftIntegrationService().get_valid_access_token(tenant_id, user_id)
        return cls(token)
