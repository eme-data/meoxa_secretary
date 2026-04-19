"""Routes d'authentification : signup, login (+ MFA), refresh, me."""

from datetime import datetime
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from slugify import slugify
from sqlalchemy import select
from sqlalchemy.orm import Session

from meoxa_secretary.core.deps import CurrentAuth
from meoxa_secretary.core.rate_limit import limiter
from meoxa_secretary.core.security import (
    create_token,
    decode_token,
    hash_password,
    verify_password,
)
from meoxa_secretary.database import get_db
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.user import Membership, Role, User
from meoxa_secretary.schemas.auth import (
    LoginRequest,
    MfaChallenge,
    MfaEnrollConfirm,
    MfaEnrollConfirmResponse,
    MfaEnrollStart,
    MfaLoginRequest,
    RefreshRequest,
    SignupRequest,
    TokenPair,
    UserMe,
)
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.invitations import InvitationError, InvitationService
from meoxa_secretary.services.mfa import MfaService

router = APIRouter()

DBDep = Annotated[Session, Depends(get_db)]


@router.post("/signup", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/hour")
def signup(request: Request, body: SignupRequest, db: DBDep) -> TokenPair:
    if db.scalar(select(User).where(User.email == body.email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "Email déjà utilisé")

    tenant = Tenant(
        name=body.organization_name,
        slug=_unique_tenant_slug(db, body.organization_name),
    )
    db.add(tenant)
    db.flush()

    user = User(
        email=body.email,
        full_name=body.full_name,
        password_hash=hash_password(body.password),
    )
    db.add(user)
    db.flush()

    db.add(Membership(user_id=user.id, tenant_id=tenant.id, role=Role.OWNER))
    db.commit()

    AuditService.log(
        action="auth.signup",
        resource=f"user:{user.id}",
        user_id=user.id,
        tenant_id=tenant.id,
        ip_address=_client_ip(request),
    )
    return _issue_tokens(user_id=str(user.id), tenant_id=str(tenant.id))


@router.post("/login", response_model=TokenPair | MfaChallenge)
@limiter.limit("10/minute")
def login(request: Request, body: LoginRequest, db: DBDep):
    user = db.scalar(select(User).where(User.email == body.email))
    if not user or not verify_password(body.password, user.password_hash) or not user.is_active:
        AuditService.log(
            action="auth.login.failed",
            resource=f"email:{body.email}",
            user_id=user.id if user else None,
            ip_address=_client_ip(request),
        )
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Identifiants invalides")

    membership = db.scalar(select(Membership).where(Membership.user_id == user.id))
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Aucune organisation associée")

    if user.totp_enabled:
        # On ne livre pas encore l'access_token — retour d'un challenge signé,
        # l'utilisateur doit ensuite poster /auth/mfa/login avec son code TOTP.
        challenge = create_token(
            subject=str(user.id),
            tenant_id=str(membership.tenant_id),
            token_type="mfa_challenge",
        )
        return MfaChallenge(challenge_token=challenge)

    AuditService.log(
        action="auth.login",
        resource=f"user:{user.id}",
        user_id=user.id,
        tenant_id=membership.tenant_id,
        ip_address=_client_ip(request),
    )
    return _issue_tokens(user_id=str(user.id), tenant_id=str(membership.tenant_id))


@router.post("/mfa/login", response_model=TokenPair)
@limiter.limit("10/minute")
def mfa_login(request: Request, body: MfaLoginRequest, db: DBDep) -> TokenPair:
    try:
        payload = decode_token(body.challenge_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Challenge invalide") from exc
    if payload.get("typ") != "mfa_challenge":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de token invalide")

    user = db.get(User, payload["sub"])
    if not user or not user.totp_enabled or not user.totp_secret:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "MFA indisponible")

    service = MfaService()
    ok = service.verify_totp(user.totp_secret, body.code)
    if not ok:
        # Essayer comme backup code
        new_codes = service.verify_and_consume_backup(user.backup_codes, body.code)
        if new_codes is None:
            AuditService.log(
                action="auth.mfa.failed",
                resource=f"user:{user.id}",
                user_id=user.id,
                tenant_id=payload["tid"],
                ip_address=_client_ip(request),
            )
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Code MFA invalide")
        user.backup_codes = new_codes
        db.commit()

    AuditService.log(
        action="auth.mfa.success",
        resource=f"user:{user.id}",
        user_id=user.id,
        tenant_id=payload["tid"],
        ip_address=_client_ip(request),
    )
    return _issue_tokens(user_id=str(user.id), tenant_id=payload["tid"])


@router.post("/mfa/enroll/start", response_model=MfaEnrollStart)
def mfa_enroll_start(auth: CurrentAuth) -> MfaEnrollStart:
    if auth.user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "MFA déjà active")
    enroll = MfaService().start_enrollment(auth.user.email)
    return MfaEnrollStart(**enroll.__dict__)


@router.post("/mfa/enroll/confirm", response_model=MfaEnrollConfirmResponse)
def mfa_enroll_confirm(
    body: MfaEnrollConfirm, auth: CurrentAuth, db: DBDep, request: Request
) -> MfaEnrollConfirmResponse:
    if auth.user.totp_enabled:
        raise HTTPException(status.HTTP_409_CONFLICT, "MFA déjà active")
    try:
        encrypted_secret, backup_codes = MfaService().confirm_enrollment(body.secret, body.code)
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    user = db.get(User, auth.user.id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Utilisateur introuvable")
    user.totp_secret = encrypted_secret
    user.totp_enabled = True
    user.backup_codes = MfaService.encrypt_backup_codes(backup_codes)
    db.commit()

    AuditService.log(
        action="auth.mfa.enabled",
        resource=f"user:{user.id}",
        user_id=user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )
    return MfaEnrollConfirmResponse(backup_codes=backup_codes)


@router.post("/mfa/disable", status_code=status.HTTP_204_NO_CONTENT)
def mfa_disable(auth: CurrentAuth, db: DBDep, request: Request) -> None:
    user = db.get(User, auth.user.id)
    if not user or not user.totp_enabled:
        return
    user.totp_enabled = False
    user.totp_secret = None
    user.backup_codes = None
    db.commit()
    AuditService.log(
        action="auth.mfa.disabled",
        resource=f"user:{user.id}",
        user_id=user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )


@router.post("/refresh", response_model=TokenPair)
def refresh(body: RefreshRequest) -> TokenPair:
    try:
        payload = decode_token(body.refresh_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Refresh token invalide") from exc

    if payload.get("typ") != "refresh":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de token invalide")

    return _issue_tokens(user_id=payload["sub"], tenant_id=payload["tid"])


@router.get("/me", response_model=UserMe)
def me(auth: CurrentAuth, db: DBDep) -> UserMe:
    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == auth.user.id, Membership.tenant_id == auth.tenant_id
        )
    )
    return UserMe(
        id=auth.user.id,
        email=auth.user.email,
        full_name=auth.user.full_name,
        tenant_id=auth.tenant_id,  # type: ignore[arg-type]
        role=(membership.role if membership else Role.MEMBER),
        is_superadmin=auth.user.is_superadmin,
        totp_enabled=auth.user.totp_enabled,
    )


def _issue_tokens(user_id: str, tenant_id: str) -> TokenPair:
    return TokenPair(
        access_token=create_token(user_id, tenant_id, "access"),
        refresh_token=create_token(user_id, tenant_id, "refresh"),
    )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


def _unique_tenant_slug(db: Session, organization_name: str) -> str:
    """Génère un slug unique, en suffixant -2/-3/... si collision.

    Évite l'IntegrityError quand deux tenants s'appellent pareil (fréquent
    pour les noms génériques comme « Cabinet Durand »).
    """
    base = slugify(organization_name)[:76] or "tenant"
    candidate = base
    n = 2
    while db.scalar(select(Tenant).where(Tenant.slug == candidate)):
        suffix = f"-{n}"
        candidate = f"{base[: 80 - len(suffix)]}{suffix}"
        n += 1
    return candidate


# ---------------- Acceptation d'invitation ----------------


class InvitationAcceptRequest(BaseModel):
    token: str
    password: str
    full_name: str


class InvitationPreview(BaseModel):
    email: EmailStr
    organization_name: str
    role: str
    expires_at: datetime


@router.get("/invitations/{token}", response_model=InvitationPreview)
def preview_invitation(token: str, db: DBDep) -> InvitationPreview:
    from datetime import datetime as _dt
    from datetime import UTC as _UTC

    from meoxa_secretary.models.invitation import Invitation, InvitationStatus
    from meoxa_secretary.models.tenant import Tenant

    inv = db.scalar(select(Invitation).where(Invitation.token == token))
    if not inv or inv.status != InvitationStatus.PENDING:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invitation invalide")
    if inv.expires_at < _dt.now(_UTC):
        raise HTTPException(status.HTTP_410_GONE, "Invitation expirée")
    tenant = db.scalar(select(Tenant).where(Tenant.id == inv.tenant_id))
    return InvitationPreview(
        email=inv.email,
        organization_name=tenant.name if tenant else "",
        role=inv.role,
        expires_at=inv.expires_at,
    )


@router.post("/invitations/accept", response_model=TokenPair)
@limiter.limit("10/hour")
def accept_invitation(
    request: Request, body: InvitationAcceptRequest
) -> TokenPair:
    if len(body.password) < 10:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "Mot de passe trop court (≥ 10 caractères)"
        )
    try:
        user, tenant_id = InvitationService.accept(
            token=body.token, password=body.password, full_name=body.full_name
        )
    except InvitationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    AuditService.log(
        action="team.invitation_accepted",
        resource=f"user:{user.id}",
        user_id=user.id,
        tenant_id=tenant_id,
        ip_address=_client_ip(request),
    )
    return _issue_tokens(user_id=str(user.id), tenant_id=tenant_id)
