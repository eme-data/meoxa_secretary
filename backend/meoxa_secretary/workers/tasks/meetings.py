"""Tâches réunions — pipeline OneDrive recordings (pas de bot Teams).

Flow :
    scan_recordings (notif OneDrive) → process_recording (par item)
        → transcription (VTT direct ou Whisper MP4) → summarize via Claude
        → save MeetingTranscript + index RAG + send_mail Graph à l'organisateur
"""

import asyncio

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.meeting_recording import MeetingRecordingService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


@celery_app.task(name="meoxa_secretary.workers.tasks.meetings.scan_recordings")
def scan_recordings(tenant_id: str, user_id: str) -> list[str]:
    """Scan delta OneDrive pour un user. Enqueue `process_recording` par item."""
    item_ids = asyncio.run(MeetingRecordingService().scan_for_user(tenant_id, user_id))
    for item_id in item_ids:
        process_recording.delay(tenant_id=tenant_id, user_id=user_id, drive_item_id=item_id)
    return item_ids


@celery_app.task(
    name="meoxa_secretary.workers.tasks.meetings.process_recording",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def process_recording(self, tenant_id: str, user_id: str, drive_item_id: str) -> None:
    """Télécharge + transcrit + résume un enregistrement, puis envoie le CR par mail."""
    try:
        asyncio.run(
            MeetingRecordingService().process_item(
                tenant_id=tenant_id, user_id=user_id, drive_item_id=drive_item_id
            )
        )
    except Exception as exc:
        logger.exception("meetings.process.failed", error=str(exc))
        raise self.retry(exc=exc) from exc
