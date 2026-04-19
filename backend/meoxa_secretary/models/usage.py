"""Événements d'utilisation LLM — tracés pour facturation interne / alerting.

Un event par appel `messages.create`. Permet d'agréger :
- coût mensuel par tenant
- modèles utilisés
- tenants trop consommateurs (à alerter avant qu'ils ne mangent la marge).
"""

from enum import StrEnum
from uuid import UUID

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class LlmTaskKind(StrEnum):
    EMAIL_DRAFT = "email_draft"
    MEETING_SUMMARY = "meeting_summary"
    ACTION_EXTRACTION = "action_extraction"
    OTHER = "other"


class LlmUsageEvent(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "llm_usage_events"

    user_id: Mapped[UUID | None] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    model: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    task_kind: Mapped[LlmTaskKind] = mapped_column(String(32), nullable=False, index=True)
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_read_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cache_write_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # Coût estimé en micro-dollars (entier) — évite les flottants en somme.
    cost_micro_usd: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
