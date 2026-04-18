"""Routes billing — checkout, portal, statut abonnement."""

from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from meoxa_secretary.core.deps import CurrentAuth, TenantAdmin, TenantDB
from meoxa_secretary.models.billing import SubscriptionStatus, TenantSubscription
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.services.billing import BillingService

router = APIRouter()


class SubscriptionOut(BaseModel):
    status: SubscriptionStatus
    plan: str | None
    current_period_end: datetime | None
    cancel_at_period_end: bool


class CheckoutResponse(BaseModel):
    url: str


class PortalResponse(BaseModel):
    url: str


@router.get("/subscription", response_model=SubscriptionOut)
def get_subscription(auth: CurrentAuth, db: TenantDB) -> SubscriptionOut:
    sub = db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == auth.tenant_id)
    )
    if not sub:
        return SubscriptionOut(
            status=SubscriptionStatus.NONE,
            plan=None,
            current_period_end=None,
            cancel_at_period_end=False,
        )
    return SubscriptionOut(
        status=sub.status,
        plan=sub.plan,
        current_period_end=sub.current_period_end,
        cancel_at_period_end=sub.cancel_at_period_end,
    )


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(auth: TenantAdmin, db: TenantDB) -> CheckoutResponse:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")
    try:
        url = BillingService().create_checkout_session(
            tenant_id=str(tenant.id),
            tenant_name=tenant.name,
            customer_email=auth.user.email,
        )
    except RuntimeError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return CheckoutResponse(url=url)


@router.post("/portal", response_model=PortalResponse)
def create_portal(auth: TenantAdmin) -> PortalResponse:
    try:
        url = BillingService().create_portal_session(tenant_id=str(auth.tenant_id))
    except (RuntimeError, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return PortalResponse(url=url)
