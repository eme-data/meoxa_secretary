"""Tâches Celery déclenchées par les webhooks Microsoft Graph."""

import asyncio
from typing import Any

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.microsoft_subscription import MicrosoftSubscriptionService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.graph_notifications.process_notification")
def process_notification(tenant_id: str, user_id: str, notification: dict[str, Any]) -> None:
    """Traite une notification de changement (mail reçu, évènement modifié, etc.).

    `notification` contient notamment :
    - changeType : "created" | "updated" | "deleted"
    - resource   : chemin de la ressource (ex: "me/messages/AAMk...")
    - subscriptionId
    """
    resource = notification.get("resource", "")
    change_type = notification.get("changeType", "")
    logger.info(
        "graph.notification.received",
        tenant_id=tenant_id,
        user_id=user_id,
        change_type=change_type,
        resource=resource,
    )

    # Routing minimaliste — on délègue aux services métier.
    if "drive" in resource or "driveItem" in resource:
        # Notification OneDrive : peut être un nouvel enregistrement Teams.
        from meoxa_secretary.workers.tasks.meetings import scan_recordings

        scan_recordings.delay(tenant_id=tenant_id, user_id=user_id)
    elif "messages" in resource:
        # `resource` ex: "Users/{userId}/Messages/AAMk..."
        message_id = resource.rsplit("/", 1)[-1]
        if message_id:
            from meoxa_secretary.workers.tasks.emails import ingest_message

            ingest_message.delay(
                tenant_id=tenant_id, user_id=user_id, message_id=message_id
            )
    elif "events" in resource:
        # TODO: fetch l'event + logique de rappel / indexation calendrier
        pass


@celery_app.task(name="meoxa_secretary.workers.tasks.graph_notifications.renew_subscriptions")
def renew_subscriptions() -> int:
    """Beat quotidien — renouvelle toutes les subs expirant dans < 24h."""
    return asyncio.run(MicrosoftSubscriptionService().renew_expiring())
