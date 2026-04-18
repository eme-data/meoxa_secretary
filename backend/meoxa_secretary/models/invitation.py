"""Invitations d'utilisateurs à rejoindre un tenant."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class InvitationStatus(StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REVOKED = "revoked"
    EXPIRED = "expired"


class Invitation(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "invitations"
    __table_args__ = (UniqueConstraint("token", name="uq_invitations_token"),)

    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="member")
    # Token opaque (url-safe) — utilisé dans le lien d'invitation.
    token: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[InvitationStatus] = mapped_column(
        String(32), default=InvitationStatus.PENDING, nullable=False, index=True
    )
    invited_by_user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
