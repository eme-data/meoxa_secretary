"""Tâches Celery d'indexation du contexte tenant (RAG)."""

import asyncio

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.models.memory import MemorySourceType
from meoxa_secretary.services.context import ContextService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.memory.index_text")
def index_text(
    tenant_id: str,
    source_type: str,
    source_id: str,
    content: str,
    meta: dict | None = None,
) -> int:
    """Indexe un texte arbitraire (email, CR) dans la mémoire du tenant."""
    try:
        st = MemorySourceType(source_type)
    except ValueError:
        logger.warning("memory.index.unknown_source_type", source_type=source_type)
        return 0

    return asyncio.run(
        ContextService().index(
            tenant_id=tenant_id,
            source_type=st,
            source_id=source_id,
            content=content,
            meta=meta or {},
        )
    )
