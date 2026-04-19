"""Import historique au onboarding — remplit la mémoire RAG avec 30j d'emails.

Pas de draft auto ici (on ne veut pas spammer Outlook avec 200 brouillons à J1).
Uniquement indexation dans `memory_entries` pour que les futurs brouillons
soient stylisés comme le user.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.memory import MemorySourceType
from meoxa_secretary.services.context import ContextService
from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationError
from meoxa_secretary.services.settings import SettingsService
from meoxa_secretary.services.signature_detector import detect_signature_from_messages
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)

DEFAULT_LOOKBACK_DAYS = 30
MAX_MESSAGES = 200


@celery_app.task(name="meoxa_secretary.workers.tasks.onboarding.import_history")
def import_history(tenant_id: str, user_id: str, lookback_days: int | None = None) -> int:
    days = lookback_days or DEFAULT_LOOKBACK_DAYS
    try:
        count = asyncio.run(_import(tenant_id, user_id, days))
    except MicrosoftIntegrationError as exc:
        logger.warning("onboarding.import.ms_error", error=str(exc))
        return 0
    logger.info("onboarding.import.done", count=count, tenant_id=tenant_id)
    return count


async def _import(tenant_id: str, user_id: str, days: int) -> int:
    since = datetime.now(UTC) - timedelta(days=days)
    since_iso = since.isoformat().replace("+00:00", "Z")

    graph = await MicrosoftGraphService.for_user(tenant_id, user_id)
    context = ContextService()
    indexed = 0

    try:
        messages = await graph.list_inbox_since(since_iso, top=MAX_MESSAGES)
    finally:
        await graph.aclose()

    for m in messages:
        body_preview = m.get("bodyPreview", "")
        if not body_preview.strip():
            continue
        try:
            await context.index(
                tenant_id=tenant_id,
                source_type=MemorySourceType.EMAIL,
                source_id=m.get("id", ""),
                content=body_preview,
                meta={
                    "subject": m.get("subject", ""),
                    "from": m.get("from", {}).get("emailAddress", {}).get("address", ""),
                    "received_at": m.get("receivedDateTime"),
                    "imported_at_onboarding": True,
                },
            )
            indexed += 1
        except Exception as exc:
            logger.warning("onboarding.import.item_failed", error=str(exc))

    return indexed


@celery_app.task(name="meoxa_secretary.workers.tasks.onboarding.detect_signature")
def detect_signature(tenant_id: str, user_id: str) -> bool:
    """Scanne sentItems et écrit la signature détectée si champ vide.

    Non destructif : si l'user a déjà une signature configurée, on n'écrase pas.
    Retourne True si une signature a été écrite.
    """
    settings = SettingsService()
    existing = settings.get_tenant(tenant_id, "general.email_signature")
    if existing and existing.strip():
        logger.debug("signature.skip.already_set", tenant_id=tenant_id)
        return False

    try:
        messages = asyncio.run(_fetch_sent(tenant_id, user_id))
    except MicrosoftIntegrationError as exc:
        logger.warning("signature.ms_error", error=str(exc))
        return False

    sig = detect_signature_from_messages(messages)
    if not sig:
        logger.info("signature.no_pattern", tenant_id=tenant_id)
        return False

    with SessionLocal() as db:
        from sqlalchemy import text

        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        settings.set_tenant(tenant_id, "general.email_signature", sig, db)
        db.commit()

    logger.info("signature.detected", tenant_id=tenant_id, lines=sig.count("\n") + 1)
    return True


async def _fetch_sent(tenant_id: str, user_id: str) -> list[dict]:
    graph = await MicrosoftGraphService.for_user(tenant_id, user_id)
    try:
        return await graph.list_sent_messages(top=20)
    finally:
        await graph.aclose()
