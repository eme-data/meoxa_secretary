"""Service Stripe — checkout, portal, webhook.

Credentials lus depuis platform_settings :
- stripe.api_key
- stripe.webhook_secret
- stripe.price_id (Price Stripe pour le Pack Secrétariat à 1490€ HT)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

import stripe
from sqlalchemy import select, text

from meoxa_secretary.config import get_settings
from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.billing import SubscriptionStatus, TenantSubscription
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)


class BillingService:
    def __init__(self) -> None:
        s = SettingsService()
        self._api_key = s.get_platform("stripe.api_key")
        self._price_id = s.get_platform("stripe.price_id")
        self._webhook_secret = s.get_platform("stripe.webhook_secret")
        self._backend_url = get_settings().backend_url.rstrip("/")
        self._frontend_url = (
            get_settings().cors_origin_list[0].rstrip("/")
            if get_settings().cors_origin_list
            else self._backend_url
        )
        if self._api_key:
            stripe.api_key = self._api_key

    # ---------------- Checkout ----------------

    def create_checkout_session(
        self, tenant_id: str | UUID, tenant_name: str, customer_email: str
    ) -> str:
        self._assert_configured()
        customer_id = self._get_or_create_customer_id(tenant_id, tenant_name, customer_email)

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": self._price_id, "quantity": 1}],
            success_url=f"{self._frontend_url}/app/billing?status=success",
            cancel_url=f"{self._frontend_url}/app/billing?status=cancelled",
            client_reference_id=str(tenant_id),
            metadata={"tenant_id": str(tenant_id)},
            allow_promotion_codes=True,
        )
        return session.url or ""

    def create_portal_session(self, tenant_id: str | UUID) -> str:
        self._assert_configured()
        with self._tenant_session(str(tenant_id)) as db:
            sub = db.scalar(
                select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
            )
            if not sub or not sub.stripe_customer_id:
                raise ValueError("Aucun client Stripe pour ce tenant")
            customer_id = sub.stripe_customer_id

        portal = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=f"{self._frontend_url}/app/billing",
        )
        return portal.url

    # ---------------- Webhook ----------------

    def parse_webhook(self, payload: bytes, signature: str) -> dict[str, Any]:
        self._assert_configured()
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=self._webhook_secret,
        )

    def handle_event(self, event: dict[str, Any]) -> None:
        event_type = event.get("type", "")
        obj = event.get("data", {}).get("object", {})

        if event_type == "checkout.session.completed":
            self._upsert_from_checkout(obj)
        elif event_type in {
            "customer.subscription.created",
            "customer.subscription.updated",
            "customer.subscription.deleted",
        }:
            self._upsert_from_subscription(obj)
        else:
            logger.debug("stripe.event.ignored", type=event_type)

    # ---------------- Upserts ----------------

    def _upsert_from_checkout(self, session_obj: dict[str, Any]) -> None:
        tenant_id = session_obj.get("client_reference_id") or session_obj.get(
            "metadata", {}
        ).get("tenant_id")
        subscription_id = session_obj.get("subscription")
        customer_id = session_obj.get("customer")
        if not tenant_id or not subscription_id:
            return

        sub_obj = stripe.Subscription.retrieve(subscription_id)
        self._persist(
            tenant_id=tenant_id,
            customer_id=customer_id,
            subscription_obj=sub_obj,
        )

    def _upsert_from_subscription(self, sub_obj: dict[str, Any]) -> None:
        customer_id = sub_obj.get("customer")
        if not customer_id:
            return
        tenant_id = self._tenant_id_from_customer(customer_id)
        if not tenant_id:
            return
        self._persist(
            tenant_id=tenant_id, customer_id=customer_id, subscription_obj=sub_obj
        )

    def _persist(
        self, tenant_id: str, customer_id: str | None, subscription_obj: Any
    ) -> None:
        status_str = getattr(subscription_obj, "status", None) or subscription_obj.get("status")
        period_end_ts = getattr(subscription_obj, "current_period_end", None) or subscription_obj.get(
            "current_period_end"
        )
        cancel_at_period_end = getattr(
            subscription_obj, "cancel_at_period_end", False
        ) or subscription_obj.get("cancel_at_period_end", False)

        items = getattr(subscription_obj, "items", None) or subscription_obj.get("items", {})
        plan = None
        item_data = items.get("data") if isinstance(items, dict) else getattr(items, "data", None)
        if item_data:
            price = item_data[0].get("price") if isinstance(item_data[0], dict) else item_data[0].price
            plan = price.get("id") if isinstance(price, dict) else price.id

        try:
            status_enum = SubscriptionStatus(status_str)
        except ValueError:
            status_enum = SubscriptionStatus.NONE

        with self._tenant_session(str(tenant_id)) as db:
            sub = db.scalar(
                select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
            )
            if not sub:
                sub = TenantSubscription(tenant_id=tenant_id)  # type: ignore[arg-type]
                db.add(sub)
            sub.stripe_customer_id = customer_id
            sub.stripe_subscription_id = (
                getattr(subscription_obj, "id", None) or subscription_obj.get("id")
            )
            sub.status = status_enum
            sub.plan = plan
            sub.current_period_end = (
                datetime.fromtimestamp(period_end_ts, tz=timezone.utc)
                if period_end_ts
                else None
            )
            sub.cancel_at_period_end = bool(cancel_at_period_end)

    # ---------------- Helpers ----------------

    def _get_or_create_customer_id(
        self, tenant_id: str | UUID, tenant_name: str, email: str
    ) -> str:
        with self._tenant_session(str(tenant_id)) as db:
            sub = db.scalar(
                select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
            )
            if sub and sub.stripe_customer_id:
                return sub.stripe_customer_id

        customer = stripe.Customer.create(
            email=email,
            name=tenant_name,
            metadata={"tenant_id": str(tenant_id)},
        )
        with self._tenant_session(str(tenant_id)) as db:
            sub = db.scalar(
                select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id)
            )
            if not sub:
                sub = TenantSubscription(
                    tenant_id=tenant_id,  # type: ignore[arg-type]
                    stripe_customer_id=customer.id,
                    status=SubscriptionStatus.NONE,
                )
                db.add(sub)
            else:
                sub.stripe_customer_id = customer.id
        return customer.id

    def _tenant_id_from_customer(self, customer_id: str) -> str | None:
        # Lookup via métadonnées Stripe (on a mis `tenant_id` dessus à la création).
        try:
            customer = stripe.Customer.retrieve(customer_id)
            return customer.metadata.get("tenant_id") if customer.metadata else None
        except stripe.StripeError as exc:
            logger.warning("stripe.customer.lookup_failed", error=str(exc))
            return None

    def _assert_configured(self) -> None:
        if not self._api_key or not self._price_id:
            raise RuntimeError(
                "Stripe non configuré — renseigner stripe.api_key et stripe.price_id "
                "dans l'admin plateforme."
            )

    @staticmethod
    def _tenant_session(tenant_id: str):
        class _Ctx:
            def __enter__(self):
                self.session = SessionLocal()
                self.session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
                return self.session

            def __exit__(self, exc_type, exc, tb):
                try:
                    if exc_type is None:
                        self.session.commit()
                    else:
                        self.session.rollback()
                finally:
                    self.session.close()

        return _Ctx()
