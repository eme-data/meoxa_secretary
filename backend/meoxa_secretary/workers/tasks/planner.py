"""Tâche Celery : pousse les actions extraites d'un CR vers Microsoft Planner."""

import asyncio
import json

from sqlalchemy import select

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.meeting import MeetingTranscript
from meoxa_secretary.services.llm import LLMService
from meoxa_secretary.services.planner import PlannerService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.planner.push_actions_for_meeting")
def push_actions_for_meeting(tenant_id: str, user_id: str, meeting_id: str) -> list[str]:
    """Extrait les actions via Claude puis les pousse dans Planner."""
    with SessionLocal() as db:
        transcript = db.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
        )
        if not transcript or not transcript.summary_markdown:
            return []
        summary = transcript.summary_markdown

    actions = LLMService(tenant_id=tenant_id).extract_actions(summary)
    if not actions:
        return []

    # Sauvegarde des actions extraites sur le transcript (même si Planner indispo).
    with SessionLocal() as db:
        transcript = db.scalar(
            select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting_id)
        )
        if transcript:
            transcript.action_items_json = json.dumps(actions)
            db.commit()

    try:
        task_ids = asyncio.run(
            PlannerService().push_actions_for_meeting(
                tenant_id=tenant_id,
                user_id=user_id,
                meeting_id=meeting_id,
                actions=actions,
            )
        )
        logger.info("planner.pushed", count=len(task_ids), meeting_id=meeting_id)
        return task_ids
    except Exception as exc:
        logger.exception("planner.push_failed", error=str(exc))
        return []
