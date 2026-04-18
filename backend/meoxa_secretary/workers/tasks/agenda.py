"""Tâches de synchronisation du calendrier Outlook."""

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.agenda.sync_all_tenants")
def sync_all_tenants() -> None:
    logger.info("agenda.sync_all_tenants.start")
    # TODO: itérer sur les tenants actifs


@celery_app.task(name="meoxa_secretary.workers.tasks.agenda.sync_tenant")
def sync_tenant(tenant_id: str) -> None:
    """Fetch les évènements à venir et planifie le bot Teams sur les Teams meetings."""
    logger.info("agenda.sync_tenant", tenant_id=tenant_id)
    # TODO: MicrosoftGraphService.list_upcoming_events + auto-schedule bots
