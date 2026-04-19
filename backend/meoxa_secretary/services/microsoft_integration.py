"""Persistance et refresh des tokens OAuth Microsoft 365.

- Les access/refresh tokens sont chiffrés au repos via Fernet.
- Le refresh est automatique si l'access token expire dans moins de 5 minutes.
- Utilisé par les routes (via `auth.user.id` + `auth.tenant_id`) et par les workers
  (qui fournissent explicitement tenant_id).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

import msal
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from meoxa_secretary.core.crypto import decrypt, encrypt
from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.integration import MicrosoftIntegration
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)

REFRESH_THRESHOLD = timedelta(minutes=5)


class MicrosoftIntegrationError(RuntimeError):
    """Levée quand aucune intégration n'existe ou qu'elle est non rafraîchissable."""


class MicrosoftIntegrationService:
    """CRUD des intégrations Microsoft + gestion du cycle de vie des tokens."""

    def __init__(self) -> None:
        self._settings = SettingsService()

    # ---------------- Persistance ----------------

    def save_from_msal_result(
        self,
        *,
        tenant_id: str | UUID,
        user_id: str | UUID,
        result: dict[str, Any],
    ) -> MicrosoftIntegration:
        """Crée/met à jour une intégration à partir du dict MSAL."""
        if "access_token" not in result:
            raise MicrosoftIntegrationError(result.get("error_description", "Échec OAuth"))

        ms_upn = result.get("id_token_claims", {}).get("preferred_username", "")
        ms_user_id = result.get("id_token_claims", {}).get("oid", "")
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(result.get("expires_in", 3600))
        )
        scopes = result.get("scope", " ".join(self._scopes()))

        with self._tenant_session(str(tenant_id)) as session:
            existing = session.scalar(
                select(MicrosoftIntegration).where(
                    MicrosoftIntegration.tenant_id == tenant_id,
                    MicrosoftIntegration.user_id == user_id,
                )
            )
            if existing:
                existing.access_token = encrypt(result["access_token"])
                existing.refresh_token = encrypt(
                    result.get("refresh_token", decrypt(existing.refresh_token))
                )
                existing.expires_at = expires_at
                existing.scopes = scopes
                existing.ms_upn = ms_upn or existing.ms_upn
                existing.ms_user_id = ms_user_id or existing.ms_user_id
                integration = existing
            else:
                integration = MicrosoftIntegration(
                    tenant_id=tenant_id,  # type: ignore[arg-type]
                    user_id=user_id,  # type: ignore[arg-type]
                    ms_user_id=ms_user_id,
                    ms_upn=ms_upn,
                    access_token=encrypt(result["access_token"]),
                    refresh_token=encrypt(result.get("refresh_token", "")),
                    expires_at=expires_at,
                    scopes=scopes,
                )
                session.add(integration)
            session.flush()
            session.refresh(integration)
            # Expire — sinon le refresh plus bas lit des attributs détachés
            session.expunge(integration)
        return integration

    # ---------------- Lecture + refresh ----------------

    def get_valid_access_token(self, tenant_id: str | UUID, user_id: str | UUID) -> str:
        """Retourne un access token valide, en rafraîchissant si nécessaire."""
        integration = self._load(tenant_id, user_id)
        if integration.expires_at - datetime.now(timezone.utc) > REFRESH_THRESHOLD:
            return decrypt(integration.access_token)

        return self._refresh(integration)

    def _load(self, tenant_id: str | UUID, user_id: str | UUID) -> MicrosoftIntegration:
        with self._tenant_session(str(tenant_id)) as session:
            integration = session.scalar(
                select(MicrosoftIntegration).where(
                    MicrosoftIntegration.tenant_id == tenant_id,
                    MicrosoftIntegration.user_id == user_id,
                )
            )
            if not integration:
                raise MicrosoftIntegrationError(
                    "Aucune intégration Microsoft pour cet utilisateur — l'OAuth n'a pas été fait."
                )
            session.expunge(integration)
            return integration

    def _refresh(self, integration: MicrosoftIntegration) -> str:
        refresh_token = decrypt(integration.refresh_token)
        if not refresh_token:
            self._mark_error(integration, "refresh_token_absent")
            raise MicrosoftIntegrationError(
                "Refresh token absent — l'utilisateur doit relancer l'OAuth."
            )

        app = self._msal_app()
        result = app.acquire_token_by_refresh_token(
            refresh_token=refresh_token, scopes=self._scopes()
        )
        if "error" in result:
            msg = result.get("error_description", "Échec du refresh MSAL")
            logger.error("ms.refresh.error", error=msg)
            self._mark_error(integration, msg[:500])
            raise MicrosoftIntegrationError(msg)

        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=int(result.get("expires_in", 3600))
        )
        new_access = result["access_token"]
        new_refresh = result.get("refresh_token", refresh_token)

        with self._tenant_session(str(integration.tenant_id)) as session:
            row = session.get(MicrosoftIntegration, integration.id)
            if row:
                row.access_token = encrypt(new_access)
                row.refresh_token = encrypt(new_refresh)
                row.expires_at = expires_at
                row.last_error = None
                row.last_error_at = None
        return new_access

    def _mark_error(self, integration: MicrosoftIntegration, message: str) -> None:
        """Trace l'erreur sur l'intégration pour affichage UI (bannière)."""
        try:
            with self._tenant_session(str(integration.tenant_id)) as session:
                row = session.get(MicrosoftIntegration, integration.id)
                if row:
                    row.last_error = message
                    row.last_error_at = datetime.now(timezone.utc)
        except Exception as exc:
            logger.warning("ms.mark_error_failed", error=str(exc))

    # ---------------- Helpers ----------------

    def _msal_app(self) -> msal.ConfidentialClientApplication:
        client_id = self._settings.get_platform("microsoft.client_id")
        client_secret = self._settings.get_platform("microsoft.client_secret")
        tenant = self._settings.get_platform("microsoft.tenant_id") or "common"
        if not client_id or not client_secret:
            raise MicrosoftIntegrationError(
                "Microsoft 365 non configuré — renseigner microsoft.client_id et "
                "microsoft.client_secret dans l'admin plateforme."
            )
        return msal.ConfidentialClientApplication(
            client_id=client_id,
            client_credential=client_secret,
            authority=f"https://login.microsoftonline.com/{tenant}",
        )

    def _scopes(self) -> list[str]:
        from meoxa_secretary.services.microsoft_graph import _sanitize_scopes

        return _sanitize_scopes(self._settings.get_platform("microsoft.graph_scopes"))

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
