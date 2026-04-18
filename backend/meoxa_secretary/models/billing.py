"""Table `subscriptions` — liaison avec Stripe (un abonnement par tenant)."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class SubscriptionStatus(StrEnum):
    # Miroir des statuts Stripe que l'on utilise.
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    UNPAID = "unpaid"
    INCOMPLETE = "incomplete"
    INCOMPLETE_EXPIRED = "incomplete_expired"
    NONE = "none"                   # aucun abonnement connu


class TenantSubscription(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "tenant_subscriptions"
    __table_args__ = (
        UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant"),
        UniqueConstraint(
            "stripe_subscription_id", name="uq_tenant_subscriptions_stripe_sub"
        ),
    )

    stripe_customer_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        String(32), default=SubscriptionStatus.NONE, nullable=False
    )
    plan: Mapped[str | None] = mapped_column(String(64), nullable=True)
    current_period_end: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    cancel_at_period_end: Mapped[bool] = mapped_column(default=False, nullable=False)
