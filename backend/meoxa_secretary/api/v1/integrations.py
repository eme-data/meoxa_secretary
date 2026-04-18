"""Routes d'intégration Microsoft 365 (OAuth authorization code)."""

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from meoxa_secretary.config import get_settings
from meoxa_secretary.core.deps import CurrentAuth
from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.microsoft_graph import MicrosoftOAuthService
from meoxa_secretary.services.microsoft_integration import (
    MicrosoftIntegrationError,
    MicrosoftIntegrationService,
)
from meoxa_secretary.services.microsoft_subscription import MicrosoftSubscriptionService

logger = get_logger(__name__)
router = APIRouter()


@router.get("/microsoft/authorize")
def microsoft_authorize(auth: CurrentAuth) -> dict[str, str]:
    """Retourne l'URL de consentement Microsoft — le frontend y redirige l'utilisateur."""
    try:
        url = MicrosoftOAuthService().build_authorize_url(
            state=f"{auth.user.id}:{auth.tenant_id}",
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc
    return {"authorize_url": url}


@router.get("/microsoft/status")
def microsoft_status(auth: CurrentAuth) -> dict[str, object]:
    """Renvoie l'état de l'intégration MS de l'utilisateur courant."""
    from datetime import datetime, timezone

    from sqlalchemy import select, text

    from meoxa_secretary.database import SessionLocal
    from meoxa_secretary.models.integration import MicrosoftIntegration

    with SessionLocal() as db:
        db.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": str(auth.tenant_id)})
        integration = db.scalar(
            select(MicrosoftIntegration).where(
                MicrosoftIntegration.user_id == auth.user.id
            )
        )
        if not integration:
            return {"connected": False, "healthy": False, "last_error": None}

        healthy = integration.last_error is None
        expired = integration.expires_at < datetime.now(timezone.utc)
        return {
            "connected": True,
            "healthy": healthy and not expired,
            "expired": expired,
            "ms_upn": integration.ms_upn,
            "last_error": integration.last_error,
            "last_error_at": integration.last_error_at.isoformat()
            if integration.last_error_at
            else None,
            "expires_at": integration.expires_at.isoformat(),
        }


@router.get("/microsoft/callback")
async def microsoft_callback(
    background: BackgroundTasks,
    code: str = Query(...),
    state: str = Query(...),
) -> RedirectResponse:
    """Callback OAuth Microsoft — échange le code contre des tokens et les persiste."""
    try:
        user_id, tenant_id = state.split(":", 1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "State invalide") from exc

    try:
        result = MicrosoftOAuthService().exchange_code(code=code)
        integration = MicrosoftIntegrationService().save_from_msal_result(
            tenant_id=tenant_id, user_id=user_id, result=result
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    AuditService.log(
        action="integration.microsoft.connected",
        resource=f"microsoft_integration:{integration.id}",
        user_id=user_id,
        tenant_id=tenant_id,
        meta={"ms_upn": integration.ms_upn},
    )

    # Créer les subscriptions Graph (mail + calendrier) en tâche de fond —
    # le redirect vers le frontend part sans attendre.
    background.add_task(_create_subscriptions_safe, tenant_id, user_id)

    frontend_url = get_settings().cors_origin_list[0] if get_settings().cors_origin_list else "/"
    return RedirectResponse(
        url=f"{frontend_url}/app/integrations?provider=microsoft&status=connected"
    )


async def _create_subscriptions_safe(tenant_id: str, user_id: str) -> None:
    try:
        await MicrosoftSubscriptionService().create_for_user(tenant_id, user_id)
    except Exception as exc:
        logger.exception(
            "graph.subscriptions.initial_create_failed",
            tenant_id=tenant_id,
            user_id=user_id,
            error=str(exc),
        )
