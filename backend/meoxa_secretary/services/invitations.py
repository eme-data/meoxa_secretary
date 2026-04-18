"""Gestion des invitations utilisateurs à rejoindre un tenant."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from slugify import slugify  # noqa: F401  (exporté pour cohérence)
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.core.security import hash_password
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.invitation import Invitation, InvitationStatus
from meoxa_secretary.models.tenant import Tenant
from meoxa_secretary.models.user import Membership, Role, User

logger = get_logger(__name__)

INVITATION_TTL = timedelta(days=7)


class InvitationError(Exception):
    pass


class InvitationService:
    # ---------------- Création ----------------

    @staticmethod
    def create(
        *,
        tenant_id: str | UUID,
        email: str,
        role: str,
        invited_by_user_id: str | UUID,
    ) -> Invitation:
        if role not in {Role.OWNER, Role.ADMIN, Role.MEMBER}:
            raise InvitationError("Rôle invalide")

        token = secrets.token_urlsafe(32)
        expires = datetime.now(timezone.utc) + INVITATION_TTL

        with SessionLocal() as db:
            db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})
            invitation = Invitation(
                tenant_id=tenant_id,  # type: ignore[arg-type]
                email=email.lower().strip(),
                role=role,
                token=token,
                invited_by_user_id=invited_by_user_id,  # type: ignore[arg-type]
                expires_at=expires,
                status=InvitationStatus.PENDING,
            )
            db.add(invitation)
            db.flush()
            db.refresh(invitation)
            db.expunge(invitation)
            db.commit()
        logger.info(
            "invitation.created",
            tenant_id=str(tenant_id),
            email=email,
            role=role,
        )
        return invitation

    # ---------------- Acceptation ----------------

    @staticmethod
    def accept(*, token: str, password: str, full_name: str) -> tuple[User, str]:
        """Accepte une invitation : crée/récupère l'user + membership, renvoie (user, tenant_id)."""
        with SessionLocal() as db:
            # Lecture sans RLS — on ne connaît pas encore le tenant.
            invitation = db.scalar(select(Invitation).where(Invitation.token == token))
            if not invitation:
                raise InvitationError("Invitation introuvable")

            if invitation.status != InvitationStatus.PENDING:
                raise InvitationError("Invitation déjà utilisée ou révoquée")
            if invitation.expires_at < datetime.now(timezone.utc):
                invitation.status = InvitationStatus.EXPIRED
                db.commit()
                raise InvitationError("Invitation expirée")

            tenant = db.scalar(
                select(Tenant).where(Tenant.id == invitation.tenant_id)
            )
            if not tenant or not tenant.is_active:
                raise InvitationError("Organisation introuvable ou inactive")

            user = db.scalar(select(User).where(User.email == invitation.email))
            if not user:
                user = User(
                    email=invitation.email,
                    full_name=full_name,
                    password_hash=hash_password(password),
                    is_active=True,
                )
                db.add(user)
                db.flush()

            # Membership (idempotent)
            existing = db.scalar(
                select(Membership).where(
                    Membership.user_id == user.id,
                    Membership.tenant_id == invitation.tenant_id,
                )
            )
            if not existing:
                db.add(
                    Membership(
                        user_id=user.id,
                        tenant_id=invitation.tenant_id,
                        role=invitation.role,
                    )
                )

            invitation.status = InvitationStatus.ACCEPTED
            invitation.accepted_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(user)
            db.expunge(user)
            return user, str(invitation.tenant_id)

    # ---------------- Révocation ----------------

    @staticmethod
    def revoke(tenant_id: str | UUID, invitation_id: UUID) -> None:
        with SessionLocal() as db:
            db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": str(tenant_id)})
            invitation = db.scalar(select(Invitation).where(Invitation.id == invitation_id))
            if not invitation:
                return
            invitation.status = InvitationStatus.REVOKED
            db.commit()

    # ---------------- Listings ----------------

    @staticmethod
    def list_pending(db: Session, tenant_id: str | UUID) -> list[Invitation]:
        return list(
            db.scalars(
                select(Invitation).where(
                    Invitation.tenant_id == tenant_id,
                    Invitation.status == InvitationStatus.PENDING,
                )
            ).all()
        )
