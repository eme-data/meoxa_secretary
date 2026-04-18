"""Routes tenant : branding, export RGPD, droit à l'oubli, onboarding."""

from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select

from meoxa_secretary.core.deps import CurrentAuth, TenantAdmin, TenantDB
from meoxa_secretary.models.billing import SubscriptionStatus, TenantSubscription
from meoxa_secretary.models.integration import MicrosoftIntegration
from meoxa_secretary.models.setting import TenantSetting
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.tenant_data import EXPORT_DIR, TenantDataService
from meoxa_secretary.workers.tasks.tenant import export_tenant as export_tenant_task

router = APIRouter()

UPLOADS_DIR = Path("/var/lib/meoxa/uploads")


# ---------------- Branding ----------------

class BrandingOut(BaseModel):
    logo_url: str | None
    primary_color: str | None
    accent_color: str | None


class BrandingUpdate(BaseModel):
    logo_url: str | None = None
    primary_color: str | None = None
    accent_color: str | None = None


@router.get("/branding", response_model=BrandingOut)
def get_branding(auth: CurrentAuth, db: TenantDB) -> BrandingOut:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")
    return BrandingOut(
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        accent_color=tenant.accent_color,
    )


@router.put("/branding", response_model=BrandingOut)
def update_branding(
    body: BrandingUpdate, auth: TenantAdmin, db: TenantDB, request: Request
) -> BrandingOut:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")

    for field in ("logo_url", "primary_color", "accent_color"):
        value = getattr(body, field)
        if value is not None:
            setattr(tenant, field, value or None)
    db.commit()

    AuditService.log(
        action="tenant.branding.updated",
        resource=f"tenant:{tenant.id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return BrandingOut(
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        accent_color=tenant.accent_color,
    )


@router.post("/branding/logo", response_model=BrandingOut)
async def upload_logo(
    file: UploadFile, auth: TenantAdmin, db: TenantDB, request: Request
) -> BrandingOut:
    if file.content_type not in ("image/png", "image/jpeg", "image/svg+xml", "image/webp"):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Type de fichier non supporté")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    ext = (file.filename or "logo").rsplit(".", 1)[-1].lower()[:5]
    dest = UPLOADS_DIR / f"logo-{auth.tenant_id}.{ext}"
    content = await file.read()
    if len(content) > 2 * 1024 * 1024:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Logo > 2 Mo")
    dest.write_bytes(content)

    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")
    tenant.logo_url = f"/api/v1/tenant/branding/logo/{auth.tenant_id}.{ext}"
    db.commit()

    AuditService.log(
        action="tenant.branding.logo_uploaded",
        resource=f"tenant:{tenant.id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return BrandingOut(
        logo_url=tenant.logo_url,
        primary_color=tenant.primary_color,
        accent_color=tenant.accent_color,
    )


@router.get("/branding/logo/{filename}")
def serve_logo(filename: str) -> FileResponse:
    # Publique (logo est déjà affiché au user non loggué sur sa page login).
    path = UPLOADS_DIR / filename
    if not path.is_file() or not path.resolve().is_relative_to(UPLOADS_DIR.resolve()):
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return FileResponse(path)


# ---------------- RGPD : export ----------------

class ExportRequestOut(BaseModel):
    status: str
    task_id: str | None = None
    download_url: str | None = None


@router.post("/export", response_model=ExportRequestOut, status_code=status.HTTP_202_ACCEPTED)
def request_export(auth: TenantAdmin, request: Request) -> ExportRequestOut:
    task = export_tenant_task.delay(str(auth.tenant_id), str(auth.user.id))
    AuditService.log(
        action="tenant.export.requested",
        resource=f"tenant:{auth.tenant_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return ExportRequestOut(status="pending", task_id=task.id)


@router.get("/export/latest")
def download_latest_export(auth: TenantAdmin) -> FileResponse:
    pattern = f"tenant-{auth.tenant_id}-*.zip"
    candidates = sorted(EXPORT_DIR.glob(pattern))
    if not candidates:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Aucun export disponible")
    return FileResponse(
        candidates[-1], media_type="application/zip", filename=candidates[-1].name
    )


# ---------------- RGPD : droit à l'oubli ----------------

class DeletionStatus(BaseModel):
    scheduled_at: datetime | None
    grace_period_days: int = 30


@router.get("/deletion", response_model=DeletionStatus)
def deletion_status(auth: CurrentAuth, db: TenantDB) -> DeletionStatus:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    return DeletionStatus(scheduled_at=tenant.deletion_scheduled_at if tenant else None)


@router.post("/deletion", response_model=DeletionStatus, status_code=status.HTTP_202_ACCEPTED)
def request_deletion(auth: TenantAdmin, request: Request) -> DeletionStatus:
    scheduled = TenantDataService().schedule_deletion(str(auth.tenant_id))
    AuditService.log(
        action="tenant.deletion.requested",
        resource=f"tenant:{auth.tenant_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
        meta={"scheduled_for": scheduled.isoformat()},
    )
    return DeletionStatus(scheduled_at=scheduled)


@router.delete("/deletion", response_model=DeletionStatus)
def cancel_deletion(auth: TenantAdmin, request: Request) -> DeletionStatus:
    TenantDataService().cancel_deletion(str(auth.tenant_id))
    AuditService.log(
        action="tenant.deletion.cancelled",
        resource=f"tenant:{auth.tenant_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return DeletionStatus(scheduled_at=None)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------------- Onboarding ----------------

class OnboardingStatus(BaseModel):
    completed: bool
    completed_at: datetime | None
    steps: dict[str, bool]


@router.get("/onboarding", response_model=OnboardingStatus)
def onboarding_status(auth: CurrentAuth, db: TenantDB) -> OnboardingStatus:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")

    ms_connected = db.scalar(
        select(MicrosoftIntegration).where(MicrosoftIntegration.user_id == auth.user.id)
    ) is not None

    reply_tone_set = db.scalar(
        select(TenantSetting).where(TenantSetting.key == "emails.reply_tone")
    ) is not None
    signature_set = db.scalar(
        select(TenantSetting).where(TenantSetting.key == "general.email_signature")
    ) is not None

    sub = db.scalar(
        select(TenantSubscription).where(TenantSubscription.tenant_id == auth.tenant_id)
    )
    billing_active = bool(
        sub
        and sub.status
        in (SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIALING)
    )

    return OnboardingStatus(
        completed=tenant.onboarded_at is not None,
        completed_at=tenant.onboarded_at,
        steps={
            "logo_uploaded": bool(tenant.logo_url),
            "microsoft_connected": ms_connected,
            "teams_recording_confirmed": tenant.teams_recording_confirmed,
            "reply_tone_configured": reply_tone_set,
            "signature_configured": signature_set,
            "mfa_enabled": auth.user.totp_enabled,
            "billing_active": billing_active,
        },
    )


@router.post("/onboarding/teams-confirmed", response_model=OnboardingStatus)
def confirm_teams_recording(
    auth: TenantAdmin, db: TenantDB, request: Request
) -> OnboardingStatus:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")
    tenant.teams_recording_confirmed = True
    db.commit()
    AuditService.log(
        action="onboarding.teams_confirmed",
        resource=f"tenant:{tenant.id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return onboarding_status(auth, db)  # type: ignore[arg-type]


@router.post("/onboarding/import-history", status_code=status.HTTP_202_ACCEPTED)
def start_history_import(auth: CurrentAuth, request: Request) -> dict[str, str]:
    """Lance l'indexation RAG des 30 derniers jours d'emails. Async."""
    from meoxa_secretary.workers.tasks.onboarding import import_history

    task = import_history.delay(str(auth.tenant_id), str(auth.user.id), 30)
    AuditService.log(
        action="onboarding.import.started",
        resource=f"tenant:{auth.tenant_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return {"status": "pending", "task_id": task.id}


@router.post("/onboarding/complete", response_model=OnboardingStatus)
def complete_onboarding(
    auth: TenantAdmin, db: TenantDB, request: Request
) -> OnboardingStatus:
    tenant = db.scalar(select(Tenant).where(Tenant.id == auth.tenant_id))
    if not tenant:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Tenant introuvable")
    tenant.onboarded_at = datetime.now(timezone.utc)
    db.commit()
    AuditService.log(
        action="onboarding.completed",
        resource=f"tenant:{tenant.id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return onboarding_status(auth, db)  # type: ignore[arg-type]
