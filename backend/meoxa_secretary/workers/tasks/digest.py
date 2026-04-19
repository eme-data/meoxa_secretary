"""Envoi du digest matinal — scheduled par Celery beat.

`send_all_digests` itère sur tous les tenants actifs dont l'heure locale est
entre 6h55 et 7h05 (match approximatif — le beat tick toutes les 5 min).

Stratégie : on déclenche le job une fois par heure (:00) et on laisse chaque
tenant décider s'il veut être envoyé maintenant en comparant sa timezone + son
`digest.hour` avec l'heure UTC actuelle.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from sqlalchemy import select
from zoneinfo import ZoneInfo

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.services.digest import send_digest_for_tenant
from meoxa_secretary.services.settings import SettingsService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.digest.send_all_digests")
def send_all_digests() -> int:
    """Envoie le digest à tous les tenants dont l'heure locale == `digest.hour`.

    Exécuté une fois par heure par Celery beat.
    """
    now_utc = datetime.now(timezone.utc)

    with SessionLocal() as db:
        tenants = db.scalars(
            select(Tenant).where(
                Tenant.is_active.is_(True),
                Tenant.deletion_scheduled_at.is_(None),
            )
        ).all()
        tenant_ids = [str(t.id) for t in tenants]

    settings = SettingsService()
    sent = 0
    for tid in tenant_ids:
        tz_name = settings.get_tenant(tid, "general.timezone") or "Europe/Paris"
        hour_str = settings.get_tenant(tid, "digest.hour") or "7"
        try:
            tz = ZoneInfo(tz_name)
            target_hour = int(hour_str)
        except Exception:
            continue
        local_hour = now_utc.astimezone(tz).hour
        if local_hour != target_hour:
            continue
        try:
            ok = asyncio.run(send_digest_for_tenant(tid))
            if ok:
                sent += 1
        except Exception as exc:
            logger.warning("digest.tenant.failed", tenant_id=tid, error=str(exc))
    logger.info("digest.run.done", sent=sent, total=len(tenant_ids))
    return sent


@celery_app.task(name="meoxa_secretary.workers.tasks.digest.send_tenant_digest")
def send_tenant_digest(tenant_id: str) -> bool:
    """Trigger manuel : envoie immédiatement le digest du tenant (pour le test)."""
    try:
        return asyncio.run(send_digest_for_tenant(tenant_id))
    except Exception as exc:
        logger.warning("digest.manual.failed", tenant_id=tenant_id, error=str(exc))
        return False
