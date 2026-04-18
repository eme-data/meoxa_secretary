"""Stockage des tokens OAuth Microsoft 365 par utilisateur/tenant."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class MicrosoftIntegration(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "microsoft_integrations"

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    ms_user_id: Mapped[str] = mapped_column(String(128), nullable=False)
    ms_upn: Mapped[str] = mapped_column(String(320), nullable=False)
    # Tokens chiffrés côté app avant insertion (à implémenter dans le service).
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scopes: Mapped[str] = mapped_column(Text, nullable=False)
    # Dernière erreur rencontrée (refresh token révoqué, scopes manquants…).
    # Le frontend affiche une bannière tant que ces champs sont remplis.
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    last_error_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
