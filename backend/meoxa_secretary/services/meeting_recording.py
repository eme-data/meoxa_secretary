"""Détection et traitement des enregistrements Teams dans OneDrive.

Principe (compatible Office 365 Basic / Standard — pas besoin de Teams Premium) :

1. L'utilisateur active dans Teams : enregistrement auto + sous-titres live.
2. Teams dépose le MP4 + VTT dans `/OneDrive/Recordings/`.
3. Notre souscription Graph sur `/me/drive/root` nous notifie.
4. On appelle l'endpoint delta pour récupérer les éléments changés depuis la dernière scan.
5. Pour chaque nouveau MP4 :
     - Si un VTT (sous-titres) est présent dans le même dossier → on l'utilise directement.
     - Sinon → on télécharge l'audio et on le transcrit via faster-whisper.
6. Claude génère le compte-rendu via `LLMService.summarize_meeting`.
7. Le CR est sauvegardé, indexé dans la mémoire RAG, et envoyé par mail à l'organisateur
   via Microsoft Graph (`/me/sendMail`) — donc pas de SMTP à configurer.
"""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

import httpx

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.meeting import Meeting, MeetingStatus, MeetingTranscript
from meoxa_secretary.models.memory import MemorySourceType
from meoxa_secretary.models.subscription import GraphResourceType, GraphSubscription
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationService
from sqlalchemy import select, text

logger = get_logger(__name__)

GRAPH_BASE = "https://graph.microsoft.com/v1.0"
INITIAL_DELTA_URL = f"{GRAPH_BASE}/me/drive/root/delta"

# Les enregistrements Teams vont dans un dossier "Recordings" au root du OneDrive
# de l'organisateur. On filtre par nom de parent + extension.
RECORDING_PARENT_NAMES = {"Recordings", "Enregistrements"}
AUDIO_VIDEO_EXT = re.compile(r"\.(mp4|mp3|m4a|wav)$", re.IGNORECASE)
CAPTION_EXT = re.compile(r"\.vtt$", re.IGNORECASE)


class MeetingRecordingService:
    """Orchestration du pipeline enregistrement → CR pour un utilisateur."""

    def __init__(self) -> None:
        self._integration = MicrosoftIntegrationService()

    # ---------------- Scan delta OneDrive ----------------

    async def scan_for_user(self, tenant_id: str | UUID, user_id: str | UUID) -> list[str]:
        """Récupère les changements depuis le dernier delta ; retourne les IDs des items à traiter."""
        sub = self._get_recordings_subscription(tenant_id, user_id)
        delta_url = sub.delta_url or INITIAL_DELTA_URL
        token = self._integration.get_valid_access_token(tenant_id, user_id)

        items: list[dict[str, Any]] = []
        new_delta_url: str | None = None

        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=30
        ) as client:
            url: str | None = delta_url
            while url:
                r = await client.get(url)
                r.raise_for_status()
                data = r.json()
                items.extend(data.get("value", []))
                url = data.get("@odata.nextLink")
                if "@odata.deltaLink" in data:
                    new_delta_url = data["@odata.deltaLink"]
                    break

        self._persist_delta(sub.id, new_delta_url)

        relevant = [i for i in items if self._is_new_recording(i)]
        logger.info(
            "recording.scan.done",
            total=len(items),
            recordings=len(relevant),
            tenant_id=str(tenant_id),
            user_id=str(user_id),
        )
        return [i["id"] for i in relevant]

    def _is_new_recording(self, item: dict[str, Any]) -> bool:
        if item.get("deleted"):
            return False
        name = item.get("name", "")
        parent = item.get("parentReference", {}).get("name", "")
        if parent not in RECORDING_PARENT_NAMES:
            return False
        return bool(AUDIO_VIDEO_EXT.search(name))

    # ---------------- Traitement d'un item ----------------

    async def process_item(
        self, tenant_id: str | UUID, user_id: str | UUID, drive_item_id: str
    ) -> None:
        token = self._integration.get_valid_access_token(tenant_id, user_id)

        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=60
        ) as client:
            item = (await client.get(f"{GRAPH_BASE}/me/drive/items/{drive_item_id}")).json()
            title = _clean_title(item.get("name", "Réunion"))
            parent_id = item.get("parentReference", {}).get("id")

            vtt_content = await self._find_and_download_caption(
                client, parent_id=parent_id, base_name=item.get("name", "")
            )
            transcript_text = (
                _vtt_to_text(vtt_content) if vtt_content else await self._transcribe_audio(
                    client, drive_item_id
                )
            )

        if not transcript_text.strip():
            logger.warning("recording.process.empty_transcript", drive_item_id=drive_item_id)
            return

        self._save_and_notify(
            tenant_id=tenant_id,
            user_id=user_id,
            drive_item_id=drive_item_id,
            title=title,
            transcript_text=transcript_text,
            organizer_email=_extract_user_email(item),
        )

    async def _find_and_download_caption(
        self, client: httpx.AsyncClient, parent_id: str, base_name: str
    ) -> str | None:
        """Cherche un fichier VTT du même nom de base dans le dossier parent."""
        if not parent_id:
            return None
        stem = re.sub(AUDIO_VIDEO_EXT, "", base_name)
        siblings = (
            await client.get(f"{GRAPH_BASE}/me/drive/items/{parent_id}/children")
        ).json()
        for sibling in siblings.get("value", []):
            name = sibling.get("name", "")
            if stem in name and CAPTION_EXT.search(name):
                vtt_url = sibling.get("@microsoft.graph.downloadUrl")
                if vtt_url:
                    r = await client.get(vtt_url)
                    r.raise_for_status()
                    return r.text
        return None

    async def _transcribe_audio(
        self, client: httpx.AsyncClient, drive_item_id: str
    ) -> str:
        """Télécharge le MP4/audio et le transcrit via faster-whisper."""
        import os
        import tempfile

        meta = (await client.get(f"{GRAPH_BASE}/me/drive/items/{drive_item_id}")).json()
        download_url = meta.get("@microsoft.graph.downloadUrl")
        if not download_url:
            logger.warning("recording.audio.no_download_url", drive_item_id=drive_item_id)
            return ""

        suffix = ".mp4" if ".mp4" in meta.get("name", "").lower() else ".bin"
        with tempfile.NamedTemporaryFile(
            suffix=suffix, dir="/var/lib/meoxa/tmp", delete=False
        ) as tmp:
            tmp_path = tmp.name

        try:
            os.makedirs("/var/lib/meoxa/tmp", exist_ok=True)
            async with client.stream("GET", download_url) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    async for chunk in r.aiter_bytes(chunk_size=1024 * 256):
                        f.write(chunk)
            logger.info(
                "recording.audio.downloaded",
                drive_item_id=drive_item_id,
                size=os.path.getsize(tmp_path),
            )
            from meoxa_secretary.services.whisper import WhisperService

            return WhisperService().transcribe(tmp_path)
        finally:
            try:
                os.unlink(tmp_path)
            except FileNotFoundError:
                pass

    # ---------------- Persistance + envoi du CR ----------------

    def _save_and_notify(
        self,
        *,
        tenant_id: str | UUID,
        user_id: str | UUID,
        drive_item_id: str,
        title: str,
        transcript_text: str,
        organizer_email: str | None,
    ) -> None:
        # Import tardif pour éviter un import cycle LLM ↔ context ↔ models.
        from meoxa_secretary.services.context import ContextService
        from meoxa_secretary.services.llm import LLMService

        summary_md = ""
        try:
            summary_md = LLMService(tenant_id=str(tenant_id)).summarize_meeting(
                transcript=transcript_text,
                context=f"Réunion Teams — {title}",
            )
        except Exception as exc:
            logger.exception("recording.summary.failed", error=str(exc))

        with self._tenant_session(str(tenant_id)) as db:
            meeting = db.scalar(select(Meeting).where(Meeting.ms_meeting_id == drive_item_id))
            if not meeting:
                meeting = Meeting(
                    tenant_id=tenant_id,  # type: ignore[arg-type]
                    ms_meeting_id=drive_item_id,
                    title=title,
                    join_url="",
                    starts_at=_fallback_now(),
                    organizer_email=organizer_email or "",
                    status=MeetingStatus.READY,
                )
                db.add(meeting)
                db.flush()
            else:
                meeting.status = MeetingStatus.READY
                meeting.title = title

            transcript = db.scalar(
                select(MeetingTranscript).where(MeetingTranscript.meeting_id == meeting.id)
            )
            if not transcript:
                transcript = MeetingTranscript(
                    tenant_id=tenant_id,  # type: ignore[arg-type]
                    meeting_id=meeting.id,
                    raw_text=transcript_text,
                    summary_markdown=summary_md,
                )
                db.add(transcript)
            else:
                transcript.raw_text = transcript_text
                transcript.summary_markdown = summary_md
            meeting_id = str(meeting.id)

        # Indexation RAG (non bloquante).
        try:
            import asyncio

            asyncio.run(
                ContextService().index(
                    tenant_id=tenant_id,
                    source_type=MemorySourceType.MEETING_SUMMARY,
                    source_id=meeting_id,
                    content=summary_md or transcript_text[:5000],
                    meta={"title": title},
                )
            )
        except Exception as exc:
            logger.warning("recording.rag.index_failed", error=str(exc))

        # Envoi du CR à l'organisateur via Graph.
        if organizer_email and summary_md:
            try:
                import asyncio

                asyncio.run(
                    self._send_cr_email(
                        tenant_id=tenant_id,
                        user_id=user_id,
                        to=organizer_email,
                        title=title,
                        summary_md=summary_md,
                    )
                )
            except Exception as exc:
                logger.warning("recording.email.failed", error=str(exc))

        # Poussée des actions dans Planner (async, non bloquant).
        if summary_md:
            try:
                from meoxa_secretary.workers.tasks.planner import push_actions_for_meeting

                push_actions_for_meeting.delay(
                    tenant_id=str(tenant_id),
                    user_id=str(user_id),
                    meeting_id=meeting_id,
                )
            except Exception as exc:
                logger.warning("recording.planner.enqueue_failed", error=str(exc))

        # Push Notion si configuré (async).
        if summary_md:
            try:
                from meoxa_secretary.workers.tasks.notion_push import push_cr_to_notion

                push_cr_to_notion.delay(
                    tenant_id=str(tenant_id),
                    meeting_id=meeting_id,
                )
            except Exception as exc:
                logger.warning("recording.notion.enqueue_failed", error=str(exc))

        # Notification Slack / Teams (best-effort).
        if summary_md:
            try:
                import asyncio

                from meoxa_secretary.services.notifications import NotificationService

                asyncio.run(
                    NotificationService(str(tenant_id)).notify(
                        title=f"CR prêt — {title}",
                        text=summary_md.split("\n\n")[0][:500],
                    )
                )
            except Exception as exc:
                logger.warning("recording.notify.failed", error=str(exc))

    async def _send_cr_email(
        self,
        *,
        tenant_id: str | UUID,
        user_id: str | UUID,
        to: str,
        title: str,
        summary_md: str,
    ) -> None:
        """Envoie le CR depuis la BAL de l'utilisateur via /me/sendMail."""
        token = self._integration.get_valid_access_token(tenant_id, user_id)
        body_html = "<pre style='font-family:system-ui;white-space:pre-wrap'>" + _escape(
            summary_md
        ) + "</pre>"
        payload = {
            "message": {
                "subject": f"CR — {title}",
                "body": {"contentType": "HTML", "content": body_html},
                "toRecipients": [{"emailAddress": {"address": to}}],
            },
            "saveToSentItems": True,
        }
        async with httpx.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=30
        ) as client:
            r = await client.post(f"{GRAPH_BASE}/me/sendMail", json=payload)
            r.raise_for_status()
        logger.info("recording.email.sent", to=to)

    # ---------------- Helpers DB ----------------

    def _get_recordings_subscription(
        self, tenant_id: str | UUID, user_id: str | UUID
    ) -> GraphSubscription:
        with self._tenant_session(str(tenant_id)) as db:
            sub = db.scalar(
                select(GraphSubscription).where(
                    GraphSubscription.tenant_id == tenant_id,
                    GraphSubscription.user_id == user_id,
                    GraphSubscription.resource_type == GraphResourceType.RECORDINGS,
                )
            )
            if not sub:
                raise RuntimeError(
                    "Pas de souscription OneDrive pour ce user — relancer l'OAuth MS."
                )
            db.expunge(sub)
            return sub

    def _persist_delta(self, subscription_row_id: UUID, new_delta_url: str | None) -> None:
        if not new_delta_url:
            return
        with SessionLocal() as db:
            sub = db.get(GraphSubscription, subscription_row_id)
            if sub:
                sub.delta_url = new_delta_url
                db.commit()

    @staticmethod
    def _tenant_session(tenant_id: str):
        class _Ctx:
            def __enter__(self):
                self.session = SessionLocal()
                self.session.execute(
                    text("SELECT set_config('app.tenant_id', :tid, true)"),
                    {"tid": tenant_id},
                )
                return self.session

            def __exit__(self, exc_type, exc, tb):
                try:
                    if exc_type is None:
                        self.session.commit()
                    else:
                        self.session.rollback()
                finally:
                    self.session.close()

        return _Ctx()


# ------------------- Helpers purs -------------------

def _clean_title(name: str) -> str:
    name = AUDIO_VIDEO_EXT.sub("", name)
    # Teams préfixe souvent par la date — on garde tel quel, lisible.
    return name.strip(" -_") or "Réunion"


def _extract_user_email(item: dict[str, Any]) -> str | None:
    created_by = item.get("createdBy", {}).get("user", {})
    return created_by.get("email") or created_by.get("displayName")


def _vtt_to_text(vtt: str) -> str:
    """Extrait le texte brut d'un VTT (timestamps/metadata supprimés)."""
    lines: list[str] = []
    for raw in vtt.splitlines():
        line = raw.strip()
        if not line or line == "WEBVTT":
            continue
        if "-->" in line or line.isdigit():
            continue
        if line.startswith("NOTE") or line.startswith("STYLE"):
            continue
        lines.append(line)
    return " ".join(lines)


def _escape(text_in: str) -> str:
    return (
        text_in.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _fallback_now():
    from datetime import datetime, timezone

    return datetime.now(timezone.utc)
