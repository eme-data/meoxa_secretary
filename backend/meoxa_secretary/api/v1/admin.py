"""Routes d'administration — platform (super-admin) + tenant (admin tenant)."""

from fastapi import APIRouter, HTTPException, Request, status

from meoxa_secretary.core.deps import SuperAdmin, TenantAdmin, TenantDB
from meoxa_secretary.schemas.settings import SettingOut, SettingUpdate
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.settings import SettingsService

router = APIRouter()

# ---------------- Platform (super-admin) ---------------- #

platform_router = APIRouter(prefix="/platform-settings", tags=["admin:platform"])


@platform_router.get("", response_model=list[SettingOut])
def list_platform_settings(_: SuperAdmin) -> list[SettingOut]:
    return [SettingOut(**row) for row in SettingsService().list_platform()]


@platform_router.put("/{key}", response_model=SettingOut)
def update_platform_setting(
    key: str, body: SettingUpdate, auth: SuperAdmin, request: Request
) -> SettingOut:
    service = SettingsService()
    try:
        service.set_platform(key, body.value)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    AuditService.log(
        action="admin.platform_setting.updated",
        resource=f"platform_setting:{key}",
        user_id=auth.user.id,
        ip_address=_client_ip(request),
        meta={"key": key},
    )

    for row in service.list_platform():
        if row["key"] == key:
            return SettingOut(**row)
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Setting introuvable après MAJ")


# ---------------- Tenant (admin/owner du tenant) ---------------- #

tenant_router = APIRouter(prefix="/tenant-settings", tags=["admin:tenant"])


@tenant_router.get("", response_model=list[SettingOut])
def list_tenant_settings(auth: TenantAdmin, db: TenantDB) -> list[SettingOut]:
    return [SettingOut(**row) for row in SettingsService().list_tenant(auth.tenant_id, db)]


@tenant_router.put("/{key}", response_model=SettingOut)
def update_tenant_setting(
    key: str, body: SettingUpdate, auth: TenantAdmin, db: TenantDB, request: Request
) -> SettingOut:
    service = SettingsService()
    try:
        service.set_tenant(auth.tenant_id, key, body.value, db)
    except KeyError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc

    AuditService.log(
        action="admin.tenant_setting.updated",
        resource=f"tenant_setting:{key}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
        meta={"key": key},
    )

    for row in service.list_tenant(auth.tenant_id, db):
        if row["key"] == key:
            return SettingOut(**row)
    raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Setting introuvable après MAJ")


router.include_router(platform_router)
router.include_router(tenant_router)


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
