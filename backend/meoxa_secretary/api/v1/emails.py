"""Routes emails — liste, détail, approve (pousse le brouillon dans Outlook)."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from meoxa_secretary.core.deps import CurrentAuth, TenantDB, require_active_subscription
from meoxa_secretary.models.email import EmailStatus, EmailThread, EmailUrgency

# Toutes les routes emails exigent un abonnement actif.
router = APIRouter(dependencies=[Depends(require_active_subscription)])


class EmailThreadOut(BaseModel):
    id: UUID
    subject: str
    from_address: str
    snippet: str
    body_text: str | None = None
    received_at: datetime | None
    status: EmailStatus
    urgency: EmailUrgency
    suggested_reply: str | None
    outlook_draft_id: str | None

    model_config = {"from_attributes": True}


class EmailThreadListItem(BaseModel):
    id: UUID
    subject: str
    from_address: str
    snippet: str
    received_at: datetime | None
    status: EmailStatus
    urgency: EmailUrgency

    model_config = {"from_attributes": True}


class SuggestionUpdate(BaseModel):
    suggested_reply: str


@router.get("", response_model=list[EmailThreadListItem])
def list_threads(
    db: TenantDB,
    _: CurrentAuth,
    urgency: EmailUrgency | None = None,
    status_filter: EmailStatus | None = None,
) -> list[EmailThreadListItem]:
    stmt = (
        select(EmailThread)
        .order_by(EmailThread.received_at.desc().nullslast())
        .limit(100)
    )
    if urgency is not None:
        stmt = stmt.where(EmailThread.urgency == urgency)
    if status_filter is not None:
        stmt = stmt.where(EmailThread.status == status_filter)
    threads = db.scalars(stmt).all()
    return [EmailThreadListItem.model_validate(t) for t in threads]


@router.get("/{thread_id}", response_model=EmailThreadOut)
def get_thread(thread_id: UUID, db: TenantDB, _: CurrentAuth) -> EmailThreadOut:
    thread = db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")
    return EmailThreadOut.model_validate(thread)


@router.put("/{thread_id}/suggestion", response_model=EmailThreadOut)
def update_suggestion(
    thread_id: UUID, body: SuggestionUpdate, db: TenantDB, _: CurrentAuth
) -> EmailThreadOut:
    thread = db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")
    thread.suggested_reply = body.suggested_reply
    db.commit()
    db.refresh(thread)
    return EmailThreadOut.model_validate(thread)


@router.post("/{thread_id}/regenerate", response_model=EmailThreadOut)
def regenerate_suggestion(
    thread_id: UUID, db: TenantDB, auth: CurrentAuth
) -> EmailThreadOut:
    thread = db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")
    thread.status = EmailStatus.PENDING
    thread.suggested_reply = None
    db.commit()

    from meoxa_secretary.workers.tasks.emails import draft_reply

    draft_reply.delay(
        thread_id=str(thread.id),
        tenant_id=str(auth.tenant_id),
        user_id=str(auth.user.id),
    )
    db.refresh(thread)
    return EmailThreadOut.model_validate(thread)


@router.post("/{thread_id}/push-to-outlook", response_model=EmailThreadOut)
async def push_to_outlook(
    thread_id: UUID, db: TenantDB, auth: CurrentAuth
) -> EmailThreadOut:
    """Recrée un brouillon Outlook avec la suggestion actuelle (après édition user)."""
    thread = db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")
    if not thread.suggested_reply or not thread.ms_message_id:
        raise HTTPException(status.HTTP_409_CONFLICT, "Pas de suggestion ou de message lié")

    from meoxa_secretary.services.microsoft_graph import MicrosoftGraphService
    from meoxa_secretary.services.microsoft_integration import MicrosoftIntegrationError
    from meoxa_secretary.workers.tasks.emails import _markdown_to_simple_html

    try:
        graph = await MicrosoftGraphService.for_user(
            tenant_id=str(auth.tenant_id), user_id=str(auth.user.id)
        )
    except MicrosoftIntegrationError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc

    try:
        draft = await graph.create_reply_draft(thread.ms_message_id)
        draft_id = draft.get("id")
        if draft_id:
            await graph.update_message_body(
                draft_id, _markdown_to_simple_html(thread.suggested_reply)
            )
    finally:
        await graph.aclose()

    thread.outlook_draft_id = draft_id
    thread.status = EmailStatus.DRAFTED
    db.commit()
    db.refresh(thread)
    return EmailThreadOut.model_validate(thread)


@router.post("/{thread_id}/mark-sent", response_model=EmailThreadOut)
def mark_thread_sent(
    thread_id: UUID,
    body: SuggestionUpdate,
    db: TenantDB,
    _: CurrentAuth,
) -> EmailThreadOut:
    """Capture la version finale envoyée par l'user (pour le feedback loop)."""
    from datetime import datetime as _dt
    from datetime import UTC as _UTC

    thread = db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")
    thread.sent_reply = body.suggested_reply
    thread.sent_at = _dt.now(_UTC)
    thread.status = EmailStatus.SENT
    db.commit()
    db.refresh(thread)
    return EmailThreadOut.model_validate(thread)


@router.post("/{thread_id}/ignore", response_model=EmailThreadOut)
def ignore_thread(thread_id: UUID, db: TenantDB, _: CurrentAuth) -> EmailThreadOut:
    thread = db.get(EmailThread, thread_id)
    if not thread:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Thread introuvable")
    thread.status = EmailStatus.IGNORED
    db.commit()
    db.refresh(thread)
    return EmailThreadOut.model_validate(thread)
