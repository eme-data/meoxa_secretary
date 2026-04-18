"""Tâches RGPD : export asynchrone + purge différée."""

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.tenant_data import TenantDataService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.tenant.export_tenant")
def export_tenant(tenant_id: str, requested_by_user_id: str) -> str:
    archive = TenantDataService().export(tenant_id)
    AuditService.log(
        action="tenant.export.completed",
        resource=f"tenant:{tenant_id}",
        user_id=requested_by_user_id,
        tenant_id=tenant_id,
        meta={"archive": str(archive)},
    )
    return str(archive)


@celery_app.task(name="meoxa_secretary.workers.tasks.tenant.purge_due_tenants")
def purge_due_tenants() -> int:
    purged = TenantDataService().purge_due()
    if purged:
        logger.info("tenant.purge.beat", purged=purged)
    return purged
