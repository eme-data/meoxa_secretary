"""Router v1 — regroupe toutes les routes de l'API."""

from fastapi import APIRouter

from meoxa_secretary.api.v1 import (
    admin,
    agenda,
    auth,
    billing,
    dashboard,
    email_templates,
    emails,
    integrations,
    meetings,
    search,
    status,
    team,
    tenant,
    tenant_insights,
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
api_router.include_router(tenant_insights.router, prefix="/tenant/insights", tags=["insights"])
api_router.include_router(search.router, prefix="/search", tags=["search"])
api_router.include_router(email_templates.router, prefix="/emails/templates", tags=["templates"])
