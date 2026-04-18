"""Tâches asynchrones pour le traitement des webhooks Stripe."""

from typing import Any

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.billing import BillingService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.billing.handle_stripe_event")
def handle_stripe_event(event: dict[str, Any]) -> None:
    try:
        BillingService().handle_event(event)
    except Exception as exc:
        logger.exception("stripe.event.handling_failed", error=str(exc))
        raise
