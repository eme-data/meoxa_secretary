"""Tâche Celery : pousse un CR de réunion vers Notion si l'intégration est configurée."""

import asyncio
import json

from sqlalchemy import select, text

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.meeting import Meeting, MeetingTranscript
from meoxa_secretary.services.notion import NotionService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.notion_push.push_cr_to_notion")
def push_cr_to_notion(tenant_id: str, meeting_id: str) -> str | None:
    service = NotionService(tenant_id)
    if not service.is_configured():
        logger.debug("notion.skip.not_configured", tenant_id=tenant_id)
        return None

    with SessionLocal() as db:
        db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        meeting = db.scalar(select(Meeting).where(Meeting.id == meeting_id))
        transcript = db.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
        )
        if not meeting or not transcript or not transcript.summary_markdown:
            return None
        snapshot = {
            "title": meeting.title,
            "starts_at": meeting.starts_at.isoformat(),
            "organizer_email": meeting.organizer_email,
            "summary_markdown": transcript.summary_markdown,
        }

    try:
        page_id = asyncio.run(
            service.push_meeting_cr(
                title=snapshot["title"],
                starts_at=snapshot["starts_at"],
                organizer_email=snapshot["organizer_email"],
                meeting_id=meeting_id,
                summary_markdown=snapshot["summary_markdown"],
            )
        )
    except Exception as exc:
        logger.exception("notion.push_failed", error=str(exc))
        return None

    if not page_id:
        return None

    # Persiste le page_id pour éviter les doublons (ou debug).
    with SessionLocal() as db:
        db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        transcript = db.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
        )
        if transcript:
            existing = []
            if transcript.notion_page_ids_json:
                try:
                    existing = json.loads(transcript.notion_page_ids_json)
                except ValueError:
                    existing = []
            existing.append(page_id)
            transcript.notion_page_ids_json = json.dumps(existing)
            db.commit()
    return page_id
