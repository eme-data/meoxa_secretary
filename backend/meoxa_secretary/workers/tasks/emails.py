"""Pipeline de traitement des emails entrants.

Flux :
1. `ingest_message(tenant_id, user_id, resource)` — appelée par le webhook Graph
   quand un nouveau message arrive : fetch via Graph, upsert EmailThread,
   indexation RAG, puis enqueue `draft_reply` si auto-draft activé.
2. `draft_reply(thread_id, tenant_id)` — appelle Claude, crée un brouillon
   Outlook avec la réponse suggérée, notifie le user.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime, timezone

from sqlalchemy import select, text

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.email import EmailStatus, EmailThread, EmailUrgency
from meoxa_secretary.models.memory import MemorySourceType
from meoxa_secretary.services.context import ContextService
from meoxa_secretary.services.email_filters import should_skip
from meoxa_secretary.services.llm import LLMService
from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationError
from meoxa_secretary.services.notifications import NotificationService
from meoxa_secretary.services.settings import SettingsService
from meoxa_secretary.workers.celery_app import celery_app

logger = get_logger(__name__)


# ---------------- Scheduler (anciennement stub) ----------------


@celery_app.task(name="meoxa_secretary.workers.tasks.emails.sync_all_tenants")
def sync_all_tenants() -> None:
    """Fallback : si les webhooks Graph sont down, on pourrait poller ici.

    Maintenant que les subscriptions push fonctionnent, ce task est un no-op
    utilisé uniquement pour détecter un décrochage. Si tu veux remettre du
    polling de secours, itère sur les tenants actifs et appelle ingest_recent.
    """
    logger.debug("emails.sync_all_tenants.noop")


# ---------------- Ingestion ----------------


@celery_app.task(name="meoxa_secretary.workers.tasks.emails.ingest_message")
def ingest_message(tenant_id: str, user_id: str, message_id: str) -> str | None:
    """Fetch un message via Graph, upsert EmailThread, index RAG, enqueue draft."""
    try:
        message = asyncio.run(_fetch_message(tenant_id, user_id, message_id))
    except MicrosoftIntegrationError as exc:
        logger.warning("emails.ingest.ms_error", error=str(exc))
        return None

    # Règles de filtrage tenant — skip avant toute LLM call.
    from_addr = message.get("from", {}).get("emailAddress", {}).get("address", "")
    subject = message.get("subject", "") or ""
    skip, reason = should_skip(tenant_id, from_addr, subject)

    thread_id = _upsert_thread(tenant_id, message, force_ignore=skip)

    if skip:
        logger.info("emails.skip.matched_filter", reason=reason, thread_id=thread_id)
        return thread_id

    # Indexation RAG asynchrone — n'interrompt pas le flow draft.
    body_text = _html_to_text(message.get("body", {}).get("content", ""))
    if body_text:
        try:
            from meoxa_secretary.workers.tasks.memory import index_text

            index_text.delay(
                tenant_id=tenant_id,
                source_type=MemorySourceType.EMAIL.value,
                source_id=message.get("id", ""),
                content=body_text,
                meta={
                    "subject": subject,
                    "from": from_addr,
                    "received_at": message.get("receivedDateTime"),
                },
            )
        except Exception as exc:
            logger.warning("emails.rag.enqueue_failed", error=str(exc))

    # Classification d'urgence via Claude Haiku (économe)
    urgency = _classify_and_store(tenant_id, thread_id, subject, body_text)

    # Newsletter / spam → pas de draft
    if urgency in ("newsletter", "spam"):
        logger.info("emails.skip.urgency", urgency=urgency, thread_id=thread_id)
        return thread_id

    # Urgent → notif immédiate si activé
    if urgency == "urgent":
        notify_urgent = (
            SettingsService().get_tenant(tenant_id, "emails.notify_urgent") or "true"
        ).lower() == "true"
        if notify_urgent:
            try:
                asyncio.run(
                    NotificationService(tenant_id).notify(
                        title=f"Email urgent — {subject[:80]}",
                        text=f"De : {from_addr}\n\n{body_text[:400]}",
                    )
                )
            except Exception as exc:
                logger.debug("emails.urgent.notify_failed", error=str(exc))

    # Auto-draft si activé pour le tenant
    auto_draft = (
        SettingsService().get_tenant(tenant_id, "emails.auto_draft") or "true"
    ).lower() == "true"
    if auto_draft and thread_id:
        draft_reply.delay(thread_id=thread_id, tenant_id=tenant_id, user_id=user_id)
    return thread_id


def _classify_and_store(
    tenant_id: str, thread_id: str | None, subject: str, body: str
) -> str:
    """Classe l'email + persiste l'urgence. Retourne le tag."""
    if not thread_id:
        return "unknown"
    try:
        urgency = LLMService(tenant_id=tenant_id).classify_email_urgency(subject, body)
    except Exception as exc:
        logger.warning("emails.classify.failed", error=str(exc))
        urgency = "normal"

    with SessionLocal() as db:
        db.execute(
            text("SELECT set_config('app.tenant_id', :tid, true)"),
            {"tid": tenant_id},
        )
        thread = db.scalar(select(EmailThread).where(EmailThread.id == thread_id))
        if thread:
            thread.urgency = EmailUrgency(urgency)  # type: ignore[arg-type]
            db.commit()
    return urgency


async def _fetch_message(tenant_id: str, user_id: str, message_id: str) -> dict:
    graph = await MicrosoftGraphService.for_user(tenant_id, user_id)
    try:
        return await graph.get_message(message_id)
    finally:
        await graph.aclose()


def _upsert_thread(
    tenant_id: str, message: dict, force_ignore: bool = False
) -> str | None:
    ms_msg_id = message.get("id")
    conversation_id = message.get("conversationId", "")
    subject = (message.get("subject") or "(sans objet)")[:500]
    from_addr = (
        message.get("from", {}).get("emailAddress", {}).get("address", "")[:320]
    )
    snippet = (message.get("bodyPreview") or "")[:2000]
    body_html = message.get("body", {}).get("content", "") or ""
    body_text = _html_to_text(body_html)[:20000]
    received_iso = message.get("receivedDateTime")
    received_at = None
    if received_iso:
        try:
            received_at = datetime.fromisoformat(received_iso.replace("Z", "+00:00"))
        except ValueError:
            received_at = None

    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        thread = db.scalar(
            select(EmailThread).where(
                EmailThread.ms_conversation_id == conversation_id
            )
        )
        if thread is None:
            thread = EmailThread(
                tenant_id=tenant_id,  # type: ignore[arg-type]
                ms_conversation_id=conversation_id,
                ms_message_id=ms_msg_id,
                received_at=received_at,
                subject=subject,
                from_address=from_addr,
                snippet=snippet,
                body_text=body_text,
                status=EmailStatus.IGNORED if force_ignore else EmailStatus.PENDING,
            )
            db.add(thread)
        else:
            thread.ms_message_id = ms_msg_id or thread.ms_message_id
            thread.received_at = received_at or thread.received_at
            thread.subject = subject
            thread.from_address = from_addr
            thread.snippet = snippet
            thread.body_text = body_text
            # Nouveau message → on remet en pending pour re-drafter
            if thread.status in (EmailStatus.DRAFTED, EmailStatus.IGNORED):
                thread.status = EmailStatus.PENDING
                thread.suggested_reply = None
                thread.outlook_draft_id = None
        db.flush()
        thread_id = str(thread.id)
        db.commit()
    return thread_id


# ---------------- Draft reply ----------------


@celery_app.task(
    name="meoxa_secretary.workers.tasks.emails.draft_reply",
    bind=True,
    max_retries=3,
    default_retry_delay=60,
)
def draft_reply(self, thread_id: str, tenant_id: str, user_id: str) -> bool:
    """Génère un brouillon via Claude + crée un draft Outlook via Graph."""
    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        thread = db.scalar(select(EmailThread).where(EmailThread.id == thread_id))
        if not thread:
            return False
        body_text = thread.body_text or thread.snippet
        subject = thread.subject
        ms_message_id = thread.ms_message_id

    if not body_text or not ms_message_id:
        logger.info("emails.draft.skipped_empty", thread_id=thread_id)
        return False

    try:
        suggestion = LLMService(tenant_id=tenant_id).draft_email_reply(
            email_body=body_text,
            thread_context=f"Sujet : {subject}",
        )
    except Exception as exc:
        logger.exception("emails.draft.llm_failed", error=str(exc))
        raise self.retry(exc=exc)

    if not suggestion.strip():
        return False

    # Crée un brouillon Outlook pré-rempli
    draft_id = None
    try:
        draft_id = asyncio.run(
            _create_outlook_draft(tenant_id, user_id, ms_message_id, suggestion)
        )
    except MicrosoftIntegrationError as exc:
        logger.warning("emails.draft.outlook_skipped", error=str(exc))
    except Exception as exc:
        logger.warning("emails.draft.outlook_failed", error=str(exc))

    # Persiste suggestion + status + draft_id
    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        thread = db.scalar(select(EmailThread).where(EmailThread.id == thread_id))
        if thread:
            thread.suggested_reply = suggestion
            thread.outlook_draft_id = draft_id
            thread.status = EmailStatus.DRAFTED
            db.commit()

    # Notification Slack/Teams
    try:
        asyncio.run(
            NotificationService(tenant_id).notify(
                title=f"Brouillon prêt — {subject[:80]}",
                text=suggestion[:500],
            )
        )
    except Exception as exc:
        logger.debug("emails.draft.notify_failed", error=str(exc))

    return True


async def _create_outlook_draft(
    tenant_id: str, user_id: str, message_id: str, suggestion_text: str
) -> str | None:
    html = _markdown_to_simple_html(suggestion_text)
    graph = await MicrosoftGraphService.for_user(tenant_id, user_id)
    try:
        draft = await graph.create_reply_draft(message_id)
        draft_id = draft.get("id")
        if draft_id:
            await graph.update_message_body(draft_id, html)
        return draft_id
    finally:
        await graph.aclose()


# ---------------- Helpers ----------------


def _html_to_text(html: str) -> str:
    """Extraction minimaliste de texte à partir de HTML (sans BeautifulSoup)."""
    if not html:
        return ""
    # Retire les blocs <style>/<script>
    html = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    # <br>, </p>, </div> → saut de ligne
    html = re.sub(r"<(br|/p|/div|/tr)[^>]*>", "\n", html, flags=re.IGNORECASE)
    # Toutes les autres balises
    html = re.sub(r"<[^>]+>", " ", html)
    # Entités HTML courantes
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def _markdown_to_simple_html(text: str) -> str:
    """Convertit du texte avec sauts de ligne en HTML minimal (paragraphes)."""
    escaped = (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    paragraphs = [p.strip() for p in escaped.split("\n\n") if p.strip()]
    return "".join(f"<p>{p.replace(chr(10), '<br>')}</p>" for p in paragraphs)
