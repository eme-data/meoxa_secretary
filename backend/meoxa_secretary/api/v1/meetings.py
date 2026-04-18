"""Routes — réunions, bot Teams, transcripts."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from meoxa_secretary.core.deps import CurrentAuth, TenantDB
from meoxa_secretary.models.meeting import Meeting, MeetingStatus
from meoxa_secretary.workers.tasks.meetings import schedule_meeting_bot

router = APIRouter()


class MeetingScheduleIn(BaseModel):
    title: str
    join_url: str
    starts_at: datetime
    ends_at: datetime | None = None
    organizer_email: str


class MeetingOut(BaseModel):
    id: UUID
    title: str
    starts_at: datetime
    status: MeetingStatus

    model_config = {"from_attributes": True}


@router.get("", response_model=list[MeetingOut])
def list_meetings(db: TenantDB, _: CurrentAuth) -> list[MeetingOut]:
    meetings = db.scalars(select(Meeting).order_by(Meeting.starts_at.desc())).all()
    return [MeetingOut.model_validate(m) for m in meetings]


@router.post("/schedule", response_model=MeetingOut, status_code=status.HTTP_201_CREATED)
def schedule_bot(body: MeetingScheduleIn, db: TenantDB, auth: CurrentAuth) -> MeetingOut:
    """Planifie l'envoi du bot Teams sur une réunion donnée."""
    meeting = Meeting(
        tenant_id=auth.tenant_id,  # type: ignore[arg-type]
        title=body.title,
        join_url=body.join_url,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        organizer_email=body.organizer_email,
        status=MeetingStatus.SCHEDULED,
    )
    db.add(meeting)
    db.flush()
    schedule_meeting_bot.delay(str(meeting.id), auth.tenant_id)
    return MeetingOut.model_validate(meeting)


@router.get("/{meeting_id}", response_model=MeetingOut)
def get_meeting(meeting_id: UUID, db: TenantDB, _: CurrentAuth) -> MeetingOut:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Réunion introuvable")
    return MeetingOut.model_validate(meeting)


# ---------------- Détail enrichi ----------------


class MeetingDetail(BaseModel):
    id: UUID
    title: str
    starts_at: datetime
    ends_at: datetime | None
    status: MeetingStatus
    organizer_email: str
    join_url: str | None
    summary_markdown: str | None
    action_items: list[dict] | None
    planner_task_ids: list[str] | None
    raw_text_length: int


@router.get("/{meeting_id}/detail", response_model=MeetingDetail)
def get_meeting_detail(
    meeting_id: UUID, db: TenantDB, _: CurrentAuth
) -> MeetingDetail:
    import json
    from sqlalchemy import select as _select

    from meoxa_secretary.models.meeting import MeetingTranscript

    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Réunion introuvable")
    transcript = db.scalar(
        _select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.id)
    )
    actions = None
    task_ids = None
    raw_len = 0
    summary_md = None
    if transcript:
        summary_md = transcript.summary_markdown
        raw_len = len(transcript.raw_text or "")
        if transcript.action_items_json:
            try:
                actions = json.loads(transcript.action_items_json)
            except ValueError:
                actions = None
        if transcript.planner_task_ids_json:
            try:
                task_ids = json.loads(transcript.planner_task_ids_json)
            except ValueError:
                task_ids = None

    return MeetingDetail(
        id=meeting.id,
        title=meeting.title,
        starts_at=meeting.starts_at,
        ends_at=meeting.ends_at,
        status=meeting.status,
        organizer_email=meeting.organizer_email,
        join_url=meeting.join_url or None,
        summary_markdown=summary_md,
        action_items=actions,
        planner_task_ids=task_ids,
        raw_text_length=raw_len,
    )


@router.post("/{meeting_id}/resend-email", status_code=status.HTTP_202_ACCEPTED)
async def resend_cr_email(
    meeting_id: UUID, db: TenantDB, auth: CurrentAuth
) -> dict[str, str]:
    """Renvoie le CR à l'organisateur (ou à l'adresse custom stockée)."""
    from sqlalchemy import select as _select

    from meoxa_secretary.models.meeting import MeetingTranscript
    from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
    from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationError

    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Réunion introuvable")
    transcript = db.scalar(
        _select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.id)
    )
    if not transcript or not transcript.summary_markdown:
        raise HTTPException(status.HTTP_409_CONFLICT, "Aucun CR disponible")

    try:
        graph = await MicrosoftGraphService.for_user(
            tenant_id=str(auth.tenant_id), user_id=str(auth.user.id)
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    html_body = (
        "<pre style='font-family:system-ui;white-space:pre-wrap'>"
        + (
            transcript.summary_markdown.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        + "</pre>"
    )

    try:
        await graph.send_mail(
            to=meeting.organizer_email,
            subject=f"CR — {meeting.title}",
            html_body=html_body,
        )
    finally:
        await graph.aclose()

    return {"status": "sent", "to": meeting.organizer_email}
