"""Garde-fou mensuel pour le coût LLM par tenant.

Si le coût cumulé du mois en cours dépasse `llm.cost_limit_usd_monthly`, on :
  1. force le modèle Haiku (le moins cher) sur toutes les tâches
  2. envoie une notification one-shot (Slack/Teams + email à l'owner)

La vérif est mise en cache 5 min pour éviter d'agréger usage_events à chaque
call LLM. Invalidation automatique par TTL.
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.usage import LlmUsageEvent
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)

# Cache (tenant_id) -> (is_capped, expires_at)
_CACHE_TTL = 300.0
_cache: dict[str, tuple[bool, float]] = {}


def is_over_monthly_budget(tenant_id: str) -> bool:
    """True si le tenant a dépassé son plafond mensuel ce mois-ci."""
    entry = _cache.get(tenant_id)
    now = time.time()
    if entry and entry[1] > now:
        return entry[0]

    try:
        limit_usd = float(
            SettingsService().get_tenant(tenant_id, "llm.cost_limit_usd_monthly") or "0"
        )
    except (TypeError, ValueError):
        limit_usd = 0.0

    if limit_usd <= 0:
        _cache[tenant_id] = (False, now + _CACHE_TTL)
        return False

    start_of_month = datetime.now(timezone.utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )

    with SessionLocal() as db:
        total_micro = db.scalar(
            select(func.coalesce(func.sum(LlmUsageEvent.cost_micro_usd), 0))
            .where(
                LlmUsageEvent.tenant_id == UUID(tenant_id),
                LlmUsageEvent.created_at >= start_of_month,
            )
        ) or 0
    total_usd = total_micro / 1_000_000

    capped = total_usd >= limit_usd
    if capped:
        _notify_once_per_month(tenant_id, total_usd, limit_usd)

    _cache[tenant_id] = (capped, now + _CACHE_TTL)
    return capped


def _notify_once_per_month(tenant_id: str, total_usd: float, limit_usd: float) -> None:
    """Envoie l'alerte au plus une fois par mois (tracking via tenant_settings)."""
    import asyncio

    from meoxa_secretary.models.setting import TenantSetting
    from meoxa_secretary.services.notifications import NotificationService

    month_key = datetime.now(timezone.utc).strftime("%Y%m")
    key = "llm.cost_alert_last_month"

    with SessionLocal() as db:
        from sqlalchemy import text

        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        setting = db.scalar(
            select(TenantSetting).where(
                TenantSetting.tenant_id == UUID(tenant_id),
                TenantSetting.key == key,
            )
        )
        if setting and setting.value == month_key:
            return  # déjà notifié ce mois-ci

        if setting:
            setting.value = month_key
        else:
            db.add(
                TenantSetting(
                    tenant_id=UUID(tenant_id),  # type: ignore[arg-type]
                    key=key,
                    value=month_key,
                    is_secret=False,
                )
            )
        db.commit()

    logger.warning(
        "cost_guardrail.capped",
        tenant_id=tenant_id,
        cost_usd=round(total_usd, 2),
        limit_usd=round(limit_usd, 2),
    )

    try:
        asyncio.run(
            NotificationService(tenant_id).notify(
                title="🔒 Plafond mensuel LLM atteint",
                text=(
                    f"Le coût Claude de ce mois a atteint ${total_usd:.2f} "
                    f"(plafond ${limit_usd:.2f}). Secretary bascule automatiquement "
                    f"sur le modèle le moins cher (Haiku) jusqu'au début du mois "
                    f"prochain. Pour lever le plafond, modifie "
                    f"`llm.cost_limit_usd_monthly` dans les préférences tenant."
                ),
            )
        )
    except Exception as exc:
        logger.debug("cost_guardrail.notify_failed", error=str(exc))


def invalidate(tenant_id: str) -> None:
    _cache.pop(tenant_id, None)
