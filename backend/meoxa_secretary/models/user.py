"""Utilisateurs et appartenance à un tenant.

Un utilisateur peut appartenir à plusieurs tenants via `memberships` — le JWT
porte le `tenant_id` actif, ce qui permet de switcher côté UI.
"""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meoxa_secretary.models.base import Base, TimestampMixin, UUIDMixin


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class User(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "users"

    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Super-admin plateforme (toi, MDO) — accès aux platform_settings.
    is_superadmin: Mapped[bool] = mapped_column(default=False, nullable=False)

    # MFA TOTP (RFC 6238). Secret chiffré Fernet, codes de secours en JSON chiffré.
    totp_enabled: Mapped[bool] = mapped_column(default=False, nullable=False)
    totp_secret: Mapped[str | None] = mapped_column(String(512), nullable=True)
    backup_codes: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    memberships: Mapped[list["Membership"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Membership(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "memberships"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_membership_user_tenant"),)

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    tenant_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[Role] = mapped_column(String(32), default=Role.MEMBER, nullable=False)

    user: Mapped[User] = relationship(back_populates="memberships")
