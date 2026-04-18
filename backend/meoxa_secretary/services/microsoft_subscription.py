"""Gestion des souscriptions Microsoft Graph (push notifications).

Flux :
1. Après un OAuth MS réussi, on crée 2 subscriptions (mail + calendar) pour l'utilisateur.
2. Microsoft envoie un POST de validation à `notification_url` avec `validationToken` — on doit
   le renvoyer en clair sous 10s. Géré par l'endpoint webhook, pas ici.
3. Microsoft envoie ensuite les notifications de changement. Notre endpoint queue un job
   Celery qui va fetch les nouvelles données via Graph API.
4. Un beat Celery renouvelle les subscriptions qui expirent dans < 24h (PATCH avec nouveau
   `expirationDateTime`).
"""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from meoxa_secretary.config import get_settings
from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.subscription import GraphResourceType, GraphSubscription
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationService

logger = get_logger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"

# Durée max accordée par Microsoft pour les resources mail/calendar (3 jours).
# On prend 2 jours 23h pour laisser une marge.
SUBSCRIPTION_TTL = timedelta(days=2, hours=23)
RENEWAL_THRESHOLD = timedelta(hours=24)

RESOURCE_PATHS: dict[GraphResourceType, str] = {
    GraphResourceType.MAIL: "/me/mailFolders('inbox')/messages",
    GraphResourceType.CALENDAR: "/me/events",
    GraphResourceType.RECORDINGS: "/me/drive/root",
}


class MicrosoftSubscriptionService:
    def __init__(self) -> None:
        self._integration = MicrosoftIntegrationService()
        self._settings = get_settings()

    @property
    def notification_url(self) -> str:
        """URL publique vers laquelle Graph enverra les notifications."""
        return f"{self._settings.backend_url.rstrip('/')}/api/v1/webhooks/microsoft"

    # ---------------- Création ----------------

    async def create_for_user(self, tenant_id: str | UUID, user_id: str | UUID) -> list[str]:
        """Crée les subscriptions mail + calendar pour un utilisateur.

        Idempotent : si une subscription du même type existe déjà, elle est
        supprimée côté Graph avant d'en créer une nouvelle.
        """
        token = self._integration.get_valid_access_token(tenant_id, user_id)
        created: list[str] = []

        async with httpx.AsyncClient(
            base_url=GRAPH_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        ) as client:
            for resource_type, path in RESOURCE_PATHS.items():
                await self._delete_existing(tenant_id, user_id, resource_type, client)
                sub_id = await self._create_single(
                    tenant_id, user_id, resource_type, path, client
                )
                created.append(sub_id)

        return created

    async def _create_single(
        self,
        tenant_id: str | UUID,
        user_id: str | UUID,
        resource_type: GraphResourceType,
        path: str,
        client: httpx.AsyncClient,
    ) -> str:
        client_state = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + SUBSCRIPTION_TTL

        payload = {
            "changeType": "created,updated",
            "notificationUrl": self.notification_url,
            "resource": path,
            "expirationDateTime": expires_at.isoformat().replace("+00:00", "Z"),
            "clientState": client_state,
        }
        r = await client.post("/subscriptions", json=payload)
        r.raise_for_status()
        data = r.json()

        with self._tenant_session(str(tenant_id)) as session:
            session.add(
                GraphSubscription(
                    tenant_id=tenant_id,  # type: ignore[arg-type]
                    user_id=user_id,  # type: ignore[arg-type]
                    subscription_id=data["id"],
                    resource_type=resource_type,
                    resource_path=path,
                    change_type="created,updated",
                    client_state=client_state,
                    expires_at=expires_at,
                )
            )

        logger.info(
            "graph.subscription.created",
            resource=resource_type.value,
            subscription_id=data["id"],
            tenant_id=str(tenant_id),
        )
        return data["id"]

    async def _delete_existing(
        self,
        tenant_id: str | UUID,
        user_id: str | UUID,
        resource_type: GraphResourceType,
        client: httpx.AsyncClient,
    ) -> None:
        with self._tenant_session(str(tenant_id)) as session:
            existing = session.scalar(
                select(GraphSubscription).where(
                    GraphSubscription.tenant_id == tenant_id,
                    GraphSubscription.user_id == user_id,
                    GraphSubscription.resource_type == resource_type,
                )
            )
            if not existing:
                return
            sub_id = existing.subscription_id
            session.delete(existing)

        try:
            r = await client.delete(f"/subscriptions/{sub_id}")
            if r.status_code not in (200, 204, 404):
                r.raise_for_status()
        except httpx.HTTPError as exc:
            logger.warning("graph.subscription.delete_failed", sub_id=sub_id, error=str(exc))

    # ---------------- Renouvellement ----------------

    async def renew_expiring(self) -> int:
        """Appelé par Celery beat — renouvelle toutes les subs expirant dans < 24h."""
        cutoff = datetime.now(timezone.utc) + RENEWAL_THRESHOLD
        renewed = 0

        with SessionLocal() as session:
            # Pas de RLS ici : on traite tous les tenants en lot.
            subs = session.scalars(
                select(GraphSubscription).where(GraphSubscription.expires_at < cutoff)
            ).all()
            subs_snapshot = [
                (s.id, s.tenant_id, s.user_id, s.subscription_id) for s in subs
            ]

        for sub_id, tenant_id, user_id, graph_sub_id in subs_snapshot:
            try:
                await self._renew_single(sub_id, str(tenant_id), str(user_id), graph_sub_id)
                renewed += 1
            except Exception as exc:
                logger.exception(
                    "graph.subscription.renew_failed",
                    subscription_id=graph_sub_id,
                    error=str(exc),
                )
        return renewed

    async def _renew_single(
        self, row_id: UUID, tenant_id: str, user_id: str, graph_sub_id: str
    ) -> None:
        token = self._integration.get_valid_access_token(tenant_id, user_id)
        new_expires = datetime.now(timezone.utc) + SUBSCRIPTION_TTL

        async with httpx.AsyncClient(
            base_url=GRAPH_BASE,
            headers={"Authorization": f"Bearer {token}"},
            timeout=30,
        ) as client:
            r = await client.patch(
                f"/subscriptions/{graph_sub_id}",
                json={
                    "expirationDateTime": new_expires.isoformat().replace("+00:00", "Z"),
                },
            )
            r.raise_for_status()

        with self._tenant_session(tenant_id) as session:
            row = session.get(GraphSubscription, row_id)
            if row:
                row.expires_at = new_expires
        logger.info("graph.subscription.renewed", subscription_id=graph_sub_id)

    # ---------------- Validation webhook ----------------

    def verify_client_state(self, subscription_id: str, client_state: str) -> bool:
        """Vérifie que le clientState reçu matche celui qu'on a stocké.

        Pas de RLS ici — l'endpoint webhook est public et ne connaît pas le tenant.
        """
        with SessionLocal() as session:
            sub = session.scalar(
                select(GraphSubscription).where(
                    GraphSubscription.subscription_id == subscription_id
                )
            )
        if not sub:
            return False
        return secrets.compare_digest(sub.client_state, client_state)

    def tenant_for_subscription(self, subscription_id: str) -> tuple[str, str] | None:
        """Renvoie (tenant_id, user_id) pour router le traitement."""
        with SessionLocal() as session:
            sub = session.scalar(
                select(GraphSubscription).where(
                    GraphSubscription.subscription_id == subscription_id
                )
            )
        if not sub:
            return None
        return str(sub.tenant_id), str(sub.user_id)

    # ---------------- Helpers ----------------

    @staticmethod
    def _tenant_session(tenant_id: str):
        class _Ctx:
            def __enter__(self) -> Session:
                self.session = SessionLocal()
                self.session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
                return self.session

            def __exit__(self, exc_type, exc, tb) -> None:
                try:
                    if exc_type is None:
                        self.session.commit()
                    else:
                        self.session.rollback()
                finally:
                    self.session.close()

        return _Ctx()
