"""Threads d'emails suivis par l'automatisation."""

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class EmailStatus(StrEnum):
    PENDING = "pending"
    DRAFTED = "drafted"
    SENT = "sent"
    IGNORED = "ignored"


class EmailUrgency(StrEnum):
    URGENT = "urgent"
    NORMAL = "normal"
    NEWSLETTER = "newsletter"
    SPAM = "spam"
    UNKNOWN = "unknown"


class EmailThread(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "email_threads"

    ms_conversation_id: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    # Dernier message reçu du thread (utilisé pour createReply).
    ms_message_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, index=True
    )
    subject: Mapped[str] = mapped_column(String(500), nullable=False)
    from_address: Mapped[str] = mapped_column(String(320), nullable=False)
    snippet: Mapped[str] = mapped_column(Text, nullable=False, default="")
    body_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[EmailStatus] = mapped_column(
        String(32), default=EmailStatus.PENDING, nullable=False
    )
    # Classification d'urgence par Claude — décide si on drafte et si on notifie.
    urgency: Mapped[EmailUrgency] = mapped_column(
        String(32), default=EmailUrgency.UNKNOWN, nullable=False, index=True
    )
    suggested_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    # ID du brouillon créé dans Outlook via createReply (si on l'a poussé).
    outlook_draft_id: Mapped[str | None] = mapped_column(String(256), nullable=True)
    # Version effectivement envoyée par l'user (après édition du brouillon) — feedback loop.
    sent_reply: Mapped[str | None] = mapped_column(Text, nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
