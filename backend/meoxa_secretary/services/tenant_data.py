"""Service d'export et de suppression des données tenant (conformité RGPD).

- **Export** : produit un ZIP contenant un JSON par ressource + un manifest.
  Stocké temporairement sur disque (ou S3 si configuré) avec TTL court (7j).
- **Suppression** : marque le tenant `deletion_scheduled_at`, une tâche Celery
  effectue la suppression effective après 30 jours (annulable pendant ce délai).
"""

from __future__ import annotations

import io
import json
import zipfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import UUID

import httpx
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.audit import AuditLog
from meoxa_secretary.models.email import EmailThread
from meoxa_secretary.models.integration import MicrosoftIntegration
from meoxa_secretary.models.meeting import Meeting, MeetingTranscript
from meoxa_secretary.models.setting import TenantSetting
from meoxa_secretary.models.subscription import GraphSubscription
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.user import Membership, User
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationService

logger = get_logger(__name__)

DELETION_GRACE_PERIOD = timedelta(days=30)
EXPORT_DIR = Path("/var/lib/meoxa/exports")


class TenantDataService:
    # ---------------- Export ----------------

    def export(self, tenant_id: str | UUID) -> Path:
        """Crée un ZIP d'export et retourne son chemin local."""
        EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive_path = EXPORT_DIR / f"tenant-{tenant_id}-{timestamp}.zip"

        with SessionLocal() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            payload = self._collect_all(session, tenant_id)

        with zipfile.ZipFile(archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(
                "manifest.json",
                json.dumps(
                    {
                        "tenant_id": str(tenant_id),
                        "generated_at": datetime.now(timezone.utc).isoformat(),
                        "format_version": 1,
                        "files": sorted(payload.keys()),
                    },
                    indent=2,
                ),
            )
            for filename, data in payload.items():
                zf.writestr(filename, json.dumps(data, indent=2, default=str))

        logger.info("tenant.export.done", tenant_id=str(tenant_id), archive=str(archive_path))
        return archive_path

    def _collect_all(self, session: Session, tenant_id: str | UUID) -> dict[str, Any]:
        tenant = session.scalar(select(Tenant).where(Tenant.id == tenant_id))
        memberships = session.scalars(
            select(Membership).where(Membership.tenant_id == tenant_id)
        ).all()
        user_ids = [m.user_id for m in memberships]
        users = session.scalars(select(User).where(User.id.in_(user_ids))).all() if user_ids else []

        return {
            "tenant.json": _model_to_dict(tenant) if tenant else {},
            "users.json": [
                {k: v for k, v in _model_to_dict(u).items() if k not in ("password_hash", "totp_secret", "backup_codes")}
                for u in users
            ],
            "memberships.json": [_model_to_dict(m) for m in memberships],
            "email_threads.json": [
                _model_to_dict(t)
                for t in session.scalars(select(EmailThread)).all()
            ],
            "meetings.json": [
                _model_to_dict(m) for m in session.scalars(select(Meeting)).all()
            ],
            "meeting_transcripts.json": [
                _model_to_dict(t) for t in session.scalars(select(MeetingTranscript)).all()
            ],
            "microsoft_integrations.json": [
                {
                    k: v
                    for k, v in _model_to_dict(i).items()
                    if k not in ("access_token", "refresh_token")
                }
                for i in session.scalars(select(MicrosoftIntegration)).all()
            ],
            "graph_subscriptions.json": [
                _model_to_dict(s) for s in session.scalars(select(GraphSubscription)).all()
            ],
            "tenant_settings.json": [
                {k: v for k, v in _model_to_dict(s).items() if k != "value"}
                for s in session.scalars(select(TenantSetting)).all()
            ],
            "audit_logs.json": [
                _model_to_dict(a)
                for a in session.scalars(
                    select(AuditLog).where(AuditLog.tenant_id == tenant_id)
                ).all()
            ],
        }

    # ---------------- Suppression (RGPD) ----------------

    def schedule_deletion(self, tenant_id: str | UUID) -> datetime:
        """Marque la suppression ; effacement réel après `DELETION_GRACE_PERIOD`."""
        scheduled_for = datetime.now(timezone.utc) + DELETION_GRACE_PERIOD
        with SessionLocal() as session:
            tenant = session.get(Tenant, tenant_id)
            if not tenant:
                raise ValueError(f"Tenant introuvable: {tenant_id}")
            tenant.deletion_scheduled_at = scheduled_for
            tenant.is_active = False
            session.commit()
        logger.info(
            "tenant.deletion.scheduled", tenant_id=str(tenant_id), scheduled_for=scheduled_for
        )
        return scheduled_for

    def cancel_deletion(self, tenant_id: str | UUID) -> None:
        with SessionLocal() as session:
            tenant = session.get(Tenant, tenant_id)
            if not tenant:
                return
            tenant.deletion_scheduled_at = None
            tenant.is_active = True
            session.commit()
        logger.info("tenant.deletion.cancelled", tenant_id=str(tenant_id))

    def purge_due(self) -> int:
        """Supprime effectivement les tenants dont `deletion_scheduled_at` est passé."""
        purged = 0
        now = datetime.now(timezone.utc)
        with SessionLocal() as session:
            due = session.scalars(
                select(Tenant).where(
                    Tenant.deletion_scheduled_at.is_not(None),
                    Tenant.deletion_scheduled_at < now,
                )
            ).all()
            ids = [t.id for t in due]

        for tenant_id in ids:
            try:
                self._hard_delete(tenant_id)
                purged += 1
            except Exception as exc:
                logger.exception(
                    "tenant.purge.failed", tenant_id=str(tenant_id), error=str(exc)
                )
        return purged

    def _hard_delete(self, tenant_id: UUID) -> None:
        # 1. Révoquer les subscriptions Graph côté Microsoft (best-effort).
        with SessionLocal() as session:
            session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)})
            subs = session.scalars(select(GraphSubscription)).all()
            subs_snapshot = [(s.subscription_id, s.user_id) for s in subs]

        for sub_id, user_id in subs_snapshot:
            try:
                token = MicrosoftIntegrationService().get_valid_access_token(tenant_id, user_id)
                with httpx.Client(
                    base_url="https://graph.microsoft.com/v1.0",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=15,
                ) as client:
                    client.delete(f"/subscriptions/{sub_id}")
            except Exception as exc:
                logger.warning("graph.sub.delete_failed", sub_id=sub_id, error=str(exc))

        # 2. Supprimer le tenant — CASCADE fera le reste (memberships, emails,
        #    meetings, settings, subscriptions, integrations).
        with SessionLocal() as session:
            tenant = session.get(Tenant, tenant_id)
            if tenant:
                session.delete(tenant)
                session.commit()
        logger.info("tenant.purged", tenant_id=str(tenant_id))


def _model_to_dict(obj: Any) -> dict[str, Any]:
    if obj is None:
        return {}
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
