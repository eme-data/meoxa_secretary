"""Service d'audit — écrit dans `audit_logs` sans casser la requête en cas d'erreur."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.audit import AuditLog

logger = get_logger(__name__)


class AuditService:
    """API statique (appelable partout) — n'expose jamais d'exception à l'appelant.

    Les logs d'audit sont importants mais ne doivent jamais planter une route
    métier. En cas d'échec DB (p.ex. DB indisponible), on fallback sur le
    logger structuré.
    """

    @staticmethod
    def log(
        *,
        action: str,
        resource: str = "",
        user_id: str | UUID | None = None,
        tenant_id: str | UUID | None = None,
        ip_address: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        payload = {
            "action": action,
            "resource": resource,
            "user_id": str(user_id) if user_id else None,
            "tenant_id": str(tenant_id) if tenant_id else None,
            "ip_address": ip_address,
            "meta": meta or {},
        }
        try:
            with SessionLocal() as db:
                db.add(
                    AuditLog(
                        tenant_id=tenant_id,  # type: ignore[arg-type]
                        user_id=user_id,  # type: ignore[arg-type]
                        action=action,
                        resource=resource,
                        ip_address=ip_address,
                        meta=meta or {},
                    )
                )
                db.commit()
        except Exception as exc:
            logger.warning("audit.log.db_failure", error=str(exc), **payload)
            return
        logger.info("audit", **payload)
