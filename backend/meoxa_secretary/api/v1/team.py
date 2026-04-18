"""Routes team — invitations + gestion des membres au sein d'un tenant."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select

from meoxa_secretary.config import get_settings
from meoxa_secretary.core.deps import CurrentAuth, TenantAdmin, TenantDB
from meoxa_secretary.models.invitation import Invitation, InvitationStatus
from meoxa_secretary.models.user import Membership, Role, User
from meoxa_secretary.services.audit import AuditService
from meoxa_secretary.services.invitations import InvitationError, InvitationService

router = APIRouter()


# ---------------- Schemas ----------------


class MemberOut(BaseModel):
    user_id: UUID
    email: str
    full_name: str
    role: str
    is_active: bool
    totp_enabled: bool


class InvitationCreate(BaseModel):
    email: EmailStr
    role: str = "member"


class InvitationOut(BaseModel):
    id: UUID
    email: str
    role: str
    status: InvitationStatus
    expires_at: datetime
    accept_url: str


class RoleUpdate(BaseModel):
    role: str


# ---------------- Members ----------------


@router.get("/members", response_model=list[MemberOut])
def list_members(auth: CurrentAuth, db: TenantDB) -> list[MemberOut]:
    memberships = db.scalars(
        select(Membership).where(Membership.tenant_id == auth.tenant_id)
    ).all()
    user_ids = [m.user_id for m in memberships]
    users = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }
    return [
        MemberOut(
            user_id=m.user_id,
            email=users[m.user_id].email,
            full_name=users[m.user_id].full_name,
            role=m.role,
            is_active=users[m.user_id].is_active,
            totp_enabled=users[m.user_id].totp_enabled,
        )
        for m in memberships
        if m.user_id in users
    ]


@router.put("/members/{user_id}/role", response_model=MemberOut)
def change_role(
    user_id: UUID,
    body: RoleUpdate,
    auth: TenantAdmin,
    db: TenantDB,
    request: Request,
) -> MemberOut:
    if body.role not in {Role.OWNER, Role.ADMIN, Role.MEMBER}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Rôle invalide")

    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.tenant_id == auth.tenant_id
        )
    )
    if not membership:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membre introuvable")

    # Empêcher qu'il ne reste aucun owner.
    if membership.role == Role.OWNER and body.role != Role.OWNER:
        owners = db.execute(
            select(Membership).where(
                Membership.tenant_id == auth.tenant_id, Membership.role == Role.OWNER
            )
        ).all()
        if len(owners) <= 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Impossible — il doit rester au moins un owner"
            )

    membership.role = body.role
    db.commit()

    user = db.scalar(select(User).where(User.id == user_id))
    AuditService.log(
        action="team.role_changed",
        resource=f"user:{user_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
        meta={"new_role": body.role},
    )
    return MemberOut(
        user_id=user_id,
        email=user.email if user else "",
        full_name=user.full_name if user else "",
        role=body.role,
        is_active=user.is_active if user else False,
        totp_enabled=user.totp_enabled if user else False,
    )


@router.delete("/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: UUID, auth: TenantAdmin, db: TenantDB, request: Request
) -> None:
    if user_id == auth.user.id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Ne te retire pas toi-même")

    membership = db.scalar(
        select(Membership).where(
            Membership.user_id == user_id, Membership.tenant_id == auth.tenant_id
        )
    )
    if not membership:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Membre introuvable")

    if membership.role == Role.OWNER:
        owners = db.execute(
            select(Membership).where(
                Membership.tenant_id == auth.tenant_id, Membership.role == Role.OWNER
            )
        ).all()
        if len(owners) <= 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Impossible — il doit rester au moins un owner"
            )

    db.delete(membership)
    db.commit()
    AuditService.log(
        action="team.member_removed",
        resource=f"user:{user_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )


# ---------------- Invitations ----------------


@router.get("/invitations", response_model=list[InvitationOut])
def list_invitations(auth: TenantAdmin, db: TenantDB) -> list[InvitationOut]:
    invitations = InvitationService.list_pending(db, auth.tenant_id)
    return [_invitation_out(i) for i in invitations]


@router.post(
    "/invitations", response_model=InvitationOut, status_code=status.HTTP_201_CREATED
)
def create_invitation(
    body: InvitationCreate, auth: TenantAdmin, request: Request
) -> InvitationOut:
    try:
        invitation = InvitationService.create(
            tenant_id=auth.tenant_id,
            email=body.email,
            role=body.role,
            invited_by_user_id=auth.user.id,
        )
    except InvitationError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc

    AuditService.log(
        action="team.invitation_created",
        resource=f"invitation:{invitation.id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
        meta={"email": body.email, "role": body.role},
    )
    return _invitation_out(invitation)


@router.delete("/invitations/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
def revoke_invitation(
    invitation_id: UUID, auth: TenantAdmin, request: Request
) -> None:
    InvitationService.revoke(auth.tenant_id, invitation_id)
    AuditService.log(
        action="team.invitation_revoked",
        resource=f"invitation:{invitation_id}",
        user_id=auth.user.id,
        tenant_id=auth.tenant_id,
        ip_address=_client_ip(request),
    )


# ---------------- Helpers ----------------


def _invitation_out(inv: Invitation) -> InvitationOut:
    frontend = (
        get_settings().cors_origin_list[0] if get_settings().cors_origin_list else ""
    )
    return InvitationOut(
        id=inv.id,
        email=inv.email,
        role=inv.role,
        status=inv.status,
        expires_at=inv.expires_at,
        accept_url=f"{frontend}/signup/invitation/{inv.token}",
    )


def _client_ip(request: Request) -> str | None:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None
