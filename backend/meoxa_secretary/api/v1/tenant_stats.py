"""Endpoint stats pour le dashboard tenant (`/app`)."""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from meoxa_secretary.core.deps import CurrentAuth, TenantDB
from meoxa_secretary.models.email import EmailStatus, EmailThread
from meoxa_secretary.models.meeting import Meeting, MeetingStatus, MeetingTranscript
from meoxa_secretary.models.usage import LlmUsageEvent

router = APIRouter()


class DashboardStats(BaseModel):
    emails_to_review: int
    meetings_upcoming: int
    crs_ready: int
    llm_cost_usd_mtd: float


class RecentEmail(BaseModel):
    id: str
    subject: str
    from_address: str
    received_at: datetime | None
    status: str


class RecentMeeting(BaseModel):
    id: str
    title: str
    starts_at: datetime
    status: str
    has_summary: bool


class DashboardPayload(BaseModel):
    stats: DashboardStats
    recent_emails: list[RecentEmail]
    recent_meetings: list[RecentMeeting]


@router.get("", response_model=DashboardPayload)
def dashboard(auth: CurrentAuth, db: TenantDB) -> DashboardPayload:
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    emails_to_review = (
        db.scalar(
            select(func.count(EmailThread.id)).where(
                EmailThread.status == EmailStatus.DRAFTED
            )
        )
        or 0
    )
    meetings_upcoming = (
        db.scalar(
            select(func.count(Meeting.id)).where(
                Meeting.starts_at >= now, Meeting.starts_at < now + timedelta(days=14)
            )
        )
        or 0
    )
    crs_ready = (
        db.scalar(
            select(func.count(MeetingTranscript.id)).where(
                MeetingTranscript.summary_markdown.is_not(None)
            )
        )
        or 0
    )
    cost_micro = (
        db.scalar(
            select(func.coalesce(func.sum(LlmUsageEvent.cost_micro_usd), 0)).where(
                LlmUsageEvent.created_at >= month_start
            )
        )
        or 0
    )

    recent_emails_rows = db.scalars(
        select(EmailThread).order_by(EmailThread.received_at.desc()).limit(5)
    ).all()

    recent_meetings_rows = db.scalars(
        select(Meeting).order_by(Meeting.starts_at.desc()).limit(5)
    ).all()
    meeting_ids = [m.id for m in recent_meetings_rows]
    has_summary = {
        t.meeting_id
        for t in db.scalars(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id.in_(meeting_ids))
        ).all()
        if t.summary_markdown
    }

    return DashboardPayload(
        stats=DashboardStats(
            emails_to_review=int(emails_to_review),
            meetings_upcoming=int(meetings_upcoming),
            crs_ready=int(crs_ready),
            llm_cost_usd_mtd=int(cost_micro) / 1_000_000,
        ),
        recent_emails=[
            RecentEmail(
                id=str(t.id),
                subject=t.subject,
                from_address=t.from_address,
                received_at=t.received_at,
                status=t.status,
            )
            for t in recent_emails_rows
        ],
        recent_meetings=[
            RecentMeeting(
                id=str(m.id),
                title=m.title,
                starts_at=m.starts_at,
                status=m.status,
                has_summary=m.id in has_summary,
            )
            for m in recent_meetings_rows
        ],
    )
