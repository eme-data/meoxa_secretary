"""Router v1 — regroupe toutes les routes de l'API."""

from fastapi import APIRouter

from meoxa_secretary.api.v1 import (
    admin,
    agenda,
    auth,
    billing,
    dashboard,
    emails,
    integrations,
    meetings,
    status,
    team,
    tenant,
    tenant_stats,
    webhooks,
)

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(integrations.router, prefix="/integrations", tags=["integrations"])
api_router.include_router(emails.router, prefix="/emails", tags=["emails"])
api_router.include_router(meetings.router, prefix="/meetings", tags=["meetings"])
api_router.include_router(agenda.router, prefix="/agenda", tags=["agenda"])
api_router.include_router(admin.router, prefix="/admin")
api_router.include_router(dashboard.router, prefix="/admin/dashboard", tags=["admin:dashboard"])
api_router.include_router(status.router, prefix="/status")
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(tenant.router, prefix="/tenant", tags=["tenant"])
api_router.include_router(team.router, prefix="/tenant/team", tags=["team"])
api_router.include_router(tenant_stats.router, prefix="/tenant/dashboard", tags=["dashboard"])
