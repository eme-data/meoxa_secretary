"""Dashboard super-admin — liste des tenants avec métriques clés."""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from meoxa_secretary.core.deps import SuperAdmin
from meoxa_secretary.database import get_db
from meoxa_secretary.models.audit import AuditLog
from meoxa_secretary.models.billing import SubscriptionStatus, TenantSubscription
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.user import Membership
from meoxa_secretary.services.usage import UsageService

router = APIRouter()


class TenantSummary(BaseModel):
    id: str
    name: str
    slug: str
    is_active: bool
    created_at: datetime
    onboarded_at: datetime | None
    deletion_scheduled_at: datetime | None
    members_count: int
    subscription_status: str
    last_activity_at: datetime | None
    llm_cost_usd_mtd: float
    llm_calls_mtd: int


class DashboardResponse(BaseModel):
    generated_at: datetime
    totals: dict[str, float]
    tenants: list[TenantSummary]


@router.get("/tenants", response_model=DashboardResponse)
def list_tenants(_: SuperAdmin, db: Session = Depends(get_db)) -> DashboardResponse:
    tenants = db.scalars(select(Tenant).order_by(Tenant.created_at.desc())).all()

    # Usage LLM mois courant (agrégat cross-tenant).
    usage_by_tenant = {
        u["tenant_id"]: u for u in UsageService.aggregate_by_tenant(db)
    }

    subs_by_tenant = {
        str(s.tenant_id): s
        for s in db.scalars(select(TenantSubscription)).all()
    }

    members_count = {}
    for row in db.execute(
        select(Membership.tenant_id, Membership.id).order_by(Membership.tenant_id)
    ).all():
        members_count[str(row.tenant_id)] = members_count.get(str(row.tenant_id), 0) + 1

    # Dernière activité = dernier audit log par tenant (approximation).
    last_activity = {
        str(row.tenant_id): row.created_at
        for row in db.execute(
            select(AuditLog.tenant_id, AuditLog.created_at).order_by(
                AuditLog.tenant_id, AuditLog.created_at.desc()
            )
        ).all()
    }

    summaries: list[TenantSummary] = []
    total_cost_usd = 0.0
    total_active_subs = 0
    for t in tenants:
        u = usage_by_tenant.get(str(t.id), {})
        cost_usd = float(u.get("cost_usd", 0.0))
        total_cost_usd += cost_usd

        sub = subs_by_tenant.get(str(t.id))
        status = sub.status if sub else SubscriptionStatus.NONE
        if status in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING):
            total_active_subs += 1

        summaries.append(
            TenantSummary(
                id=str(t.id),
                name=t.name,
                slug=t.slug,
                is_active=t.is_active,
                created_at=t.created_at,
                onboarded_at=t.onboarded_at,
                deletion_scheduled_at=t.deletion_scheduled_at,
                members_count=members_count.get(str(t.id), 0),
                subscription_status=str(status),
                last_activity_at=last_activity.get(str(t.id)),
                llm_cost_usd_mtd=cost_usd,
                llm_calls_mtd=int(u.get("calls", 0)),
            )
        )

    return DashboardResponse(
        generated_at=datetime.now(timezone.utc),
        totals={
            "tenants": float(len(tenants)),
            "active_subscriptions": float(total_active_subs),
            "llm_cost_usd_mtd": total_cost_usd,
        },
        tenants=summaries,
    )
