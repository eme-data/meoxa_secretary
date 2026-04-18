"""Table `tenants` — une organisation cliente = un tenant."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TimestampMixin, UUIDMixin


class Tenant(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "tenants"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    slug: Mapped[str] = mapped_column(String(80), nullable=False, unique=True)
    # Domaine email primaire (ex: "meoxa.app") — utilisé pour auto-routing des invitations.
    primary_domain: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Branding — exposés au frontend via /auth/me puis appliqués en CSS vars.
    logo_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    primary_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    accent_color: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Suppression différée RGPD — rempli par le droit à l'oubli, purgé après TTL.
    deletion_scheduled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # Timestamp de fin de l'onboarding wizard. Null = wizard à présenter.
    onboarded_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # L'owner a confirmé avoir activé l'auto-record + live captions côté Teams.
    teams_recording_confirmed: Mapped[bool] = mapped_column(default=False, nullable=False)
