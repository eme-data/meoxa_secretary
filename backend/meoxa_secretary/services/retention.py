"""Application des politiques de rétention par tenant.

Setting tenant `retention.transcripts_days` (int) :
- 0 (défaut) = rétention illimitée (aucune suppression auto)
- N > 0      = supprime les `meeting_transcripts` créés il y a plus de N jours
               + les `memory_entries` dont le `source_type = meeting_*` et
               `source_id` correspond à ces meetings.

La rétention s'applique via un beat Celery quotidien (04:30 UTC).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, text

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.meeting import MeetingTranscript
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)

MIN_RETENTION_DAYS = 1
MAX_RETENTION_DAYS = 3650  # 10 ans


class RetentionService:
    """Applique la politique de rétention d'un tenant ou de tous."""

    def apply_for_tenant(self, tenant_id: str | UUID) -> int:
        """Retourne le nombre de transcripts purgés."""
        days = self._policy_days(str(tenant_id))
        if days <= 0:
            return 0

        cutoff = datetime.now(UTC) - timedelta(days=days)
        purged = 0

        with SessionLocal() as db:
            db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})
            old = db.scalars(
                select(MeetingTranscript).where(MeetingTranscript.created_at < cutoff)
            ).all()
            meeting_ids = [str(t.meeting_id) for t in old]
            for t in old:
                db.delete(t)
            db.commit()
            purged = len(old)

            # Supprime aussi les memory_entries associés (pour ne pas garder
            # en RAG des extraits dont le transcript n'existe plus).
            if meeting_ids:
                db.execute(
                    text(
                        "DELETE FROM memory_entries "
                        "WHERE tenant_id = :tid "
                        "AND source_type IN ('meeting_summary', 'meeting_transcript') "
                        "AND source_id = ANY(:ids)"
                    ),
                    {"tid": str(tenant_id), "ids": meeting_ids},
                )
                db.commit()

        if purged:
            logger.info(
                "retention.applied",
                tenant_id=str(tenant_id),
                days=days,
                purged=purged,
            )
        return purged

    def apply_all(self) -> dict[str, int]:
        with SessionLocal() as db:
            tenant_ids = [str(t.id) for t in db.scalars(select(Tenant.id)).all()]
        result: dict[str, int] = {}
        for tid in tenant_ids:
            try:
                count = self.apply_for_tenant(tid)
                if count:
                    result[tid] = count
            except Exception as exc:
                logger.exception("retention.tenant_failed", tenant_id=tid, error=str(exc))
        return result

    @staticmethod
    def _policy_days(tenant_id: str) -> int:
        raw = SettingsService().get_tenant(tenant_id, "retention.transcripts_days") or "0"
        try:
            days = int(raw)
        except ValueError:
            return 0
        if days <= 0:
            return 0
        return max(MIN_RETENTION_DAYS, min(days, MAX_RETENTION_DAYS))
