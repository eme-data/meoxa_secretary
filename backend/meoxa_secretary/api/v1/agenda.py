"""Routes — agenda (lecture calendrier, smart scheduling, création Teams meeting)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from meoxa_secretary.core.deps import CurrentAuth, require_active_subscription
from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationError
from meoxa_secretary.services.scheduling import SchedulingService

router = APIRouter(dependencies=[Depends(require_active_subscription)])


class CalendarEvent(BaseModel):
    id: str
    subject: str
    start: datetime
    end: datetime
    organizer: str | None = None
    online_meeting_url: str | None = None


@router.get("/events", response_model=list[CalendarEvent])
async def list_events(auth: CurrentAuth) -> list[CalendarEvent]:
    """Liste les prochains événements du calendrier Outlook de l'utilisateur."""
    now = datetime.now(UTC)
    try:
        graph = await MicrosoftGraphService.for_user(
            tenant_id=str(auth.tenant_id), user_id=str(auth.user.id)
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    try:
        raw_events = await graph.list_upcoming_events(
            start=now.isoformat(), end=(now + timedelta(days=30)).isoformat()
        )
    finally:
        await graph.aclose()

    return [
        CalendarEvent(
            id=e["id"],
            subject=e.get("subject", "(sans titre)"),
            start=datetime.fromisoformat(e["start"]["dateTime"]),
            end=datetime.fromisoformat(e["end"]["dateTime"]),
            organizer=e.get("organizer", {}).get("emailAddress", {}).get("address"),
            online_meeting_url=e.get("onlineMeeting", {}).get("joinUrl")
            if e.get("onlineMeeting")
            else None,
        )
        for e in raw_events
    ]


# ---------------- Smart scheduling ----------------


class SuggestSlotsRequest(BaseModel):
    duration_min: int = Field(30, ge=15, le=480)
    from_date: datetime | None = None
    to_date: datetime | None = None
    max_slots: int = Field(5, ge=1, le=20)


class SlotOut(BaseModel):
    start: datetime
    end: datetime


@router.post("/suggest-slots", response_model=list[SlotOut])
async def suggest_slots(body: SuggestSlotsRequest, auth: CurrentAuth) -> list[SlotOut]:
    now = datetime.now(UTC)
    start = body.from_date or (now + timedelta(hours=1))
    end = body.to_date or (start + timedelta(days=7))
    if end <= start:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "to_date doit être après from_date")

    try:
        slots = await SchedulingService().find_free_slots(
            tenant_id=str(auth.tenant_id),
            user_id=str(auth.user.id),
            duration_min=body.duration_min,
            from_date=start,
            to_date=end,
            max_slots=body.max_slots,
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return [SlotOut(start=s.start, end=s.end) for s in slots]


class CreateMeetingRequest(BaseModel):
    subject: str
    start: datetime
    end: datetime


class CreatedMeeting(BaseModel):
    id: str
    join_url: str
    subject: str


@router.post("/meetings", response_model=CreatedMeeting)
async def create_online_meeting(
    body: CreateMeetingRequest, auth: CurrentAuth
) -> CreatedMeeting:
    try:
        graph = await MicrosoftGraphService.for_user(
            tenant_id=str(auth.tenant_id), user_id=str(auth.user.id)
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    try:
        data = await graph.create_online_meeting(
            subject=body.subject,
            start_iso=body.start.astimezone(UTC).isoformat().replace("+00:00", "Z"),
            end_iso=body.end.astimezone(UTC).isoformat().replace("+00:00", "Z"),
        )
    finally:
        await graph.aclose()

    return CreatedMeeting(
        id=data.get("id", ""),
        join_url=data.get("joinUrl", ""),
        subject=body.subject,
    )
