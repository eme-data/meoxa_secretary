"""Réunions suivies par le bot Teams + transcripts/CR."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class MeetingStatus(StrEnum):
    SCHEDULED = "scheduled"
    JOINING = "joining"
    RECORDING = "recording"
    TRANSCRIBING = "transcribing"
    SUMMARIZING = "summarizing"
    READY = "ready"
    FAILED = "failed"


class Meeting(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "meetings"

    ms_meeting_id: Mapped[str | None] = mapped_column(String(256), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    join_url: Mapped[str] = mapped_column(Text, nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[MeetingStatus] = mapped_column(
        String(32), default=MeetingStatus.SCHEDULED, nullable=False
    )
    organizer_email: Mapped[str] = mapped_column(String(320), nullable=False)

    transcript: Mapped["MeetingTranscript | None"] = relationship(
        back_populates="meeting", uselist=False, cascade="all, delete-orphan"
    )


class MeetingTranscript(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "meeting_transcripts"

    meeting_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    raw_text: Mapped[str] = mapped_column(Text, nullable=False, default="")
    summary_markdown: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_items_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    # IDs Planner créés à partir des actions extraites (JSON array).
    planner_task_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    meeting: Mapped[Meeting] = relationship(back_populates="transcript")
