"""Endpoints publics — webhooks Microsoft Graph + Stripe.

Sécurité :
- Microsoft : validation via `clientState` stocké côté DB.
- Stripe : validation via signature `Stripe-Signature` + webhook secret.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import PlainTextResponse

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.billing import BillingService
from meoxa_secretary.services.microsoft_subscription import MicrosoftSubscriptionService

logger = get_logger(__name__)
router = APIRouter()


@router.post("/microsoft")
async def microsoft_webhook(request: Request) -> Response:
    # --- Étape 1 : handshake de validation ---
    validation_token = request.query_params.get("validationToken")
    if validation_token:
        logger.info("graph.webhook.validation")
        return PlainTextResponse(content=validation_token, status_code=200)

    # --- Étape 2 : traitement des notifications ---
    try:
        body: dict[str, Any] = await request.json()
    except ValueError:
        return Response(status_code=400)

    notifications = body.get("value", [])
    service = MicrosoftSubscriptionService()
    accepted = 0

    # Import local pour éviter un import circulaire au chargement du module.
    from meoxa_secretary.workers.tasks.graph_notifications import process_notification

    for n in notifications:
        sub_id = n.get("subscriptionId", "")
        client_state = n.get("clientState", "")
        if not service.verify_client_state(sub_id, client_state):
            logger.warning("graph.webhook.bad_state", subscription_id=sub_id)
            continue

        route = service.tenant_for_subscription(sub_id)
        if not route:
            continue
        tenant_id, user_id = route

        process_notification.delay(tenant_id=tenant_id, user_id=user_id, notification=n)
        accepted += 1

    if accepted:
        AuditService.log(
            action="graph.webhook.received",
            resource=f"graph_subscription:{notifications[0].get('subscriptionId', '')}",
            meta={"count": accepted, "total": len(notifications)},
        )

    # 202 Accepted — le traitement réel est async
    return Response(status_code=202)


@router.post("/stripe")
async def stripe_webhook(request: Request) -> Response:
    signature = request.headers.get("stripe-signature")
    if not signature:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signature manquante")

    payload = await request.body()
    service = BillingService()
    try:
        event = service.parse_webhook(payload=payload, signature=signature)
    except Exception as exc:
        logger.warning("stripe.webhook.invalid_signature", error=str(exc))
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Signature invalide") from exc

    # Import local pour éviter un cycle worker <-> webhook.
    from meoxa_secretary.workers.tasks.billing import handle_stripe_event

    handle_stripe_event.delay(event)
    AuditService.log(
        action="stripe.webhook.received",
        resource=f"stripe_event:{event.get('id', '')}",
        meta={"type": event.get("type", "")},
    )
    return Response(status_code=200)
