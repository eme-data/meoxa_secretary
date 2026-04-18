"""Tâche Celery : applique les politiques de rétention des transcriptions."""

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.retention import RetentionService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.retention.apply_retention_all")
def apply_retention_all() -> dict[str, int]:
    result = RetentionService().apply_all()
    if result:
        logger.info("retention.beat.done", tenants_affected=len(result), detail=result)
    return result
