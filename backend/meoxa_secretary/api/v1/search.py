"""Recherche full-text sur emails + CR de réunions (tenant scope + RLS)."""

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select, text

from meoxa_secretary.core.deps import (
    CurrentAuth,
    TenantDB,
    require_active_subscription,
)
from meoxa_secretary.models.email import EmailThread
from meoxa_secretary.models.meeting import Meeting, MeetingTranscript

router = APIRouter(dependencies=[Depends(require_active_subscription)])


class EmailHit(BaseModel):
    id: UUID
    subject: str
    from_address: str
    snippet: str
    rank: float


class MeetingHit(BaseModel):
    id: UUID                # meeting_id
    title: str
    excerpt: str
    rank: float


class SearchResponse(BaseModel):
    query: str
    emails: list[EmailHit]
    meetings: list[MeetingHit]


@router.get("", response_model=SearchResponse)
def search(
    auth: CurrentAuth,
    db: TenantDB,
    q: str = Query(..., min_length=2, max_length=200),
    limit: int = Query(10, ge=1, le=50),
) -> SearchResponse:
    """Recherche combinée sur emails et CR de réunions."""
    # plainto_tsquery gère les mots simples, websearch_to_tsquery les opérateurs
    # avancés (AND/OR/NOT/quotes). websearch est plus user-friendly.
    tsquery_sql = text(
        "websearch_to_tsquery('french', :q)"
    ).bindparams(q=q)

    # --- Emails ---
    email_rank = func.ts_rank(EmailThread.__table__.c.search_tsv, tsquery_sql).label("rank")
    email_stmt = (
        select(EmailThread, email_rank)
        .where(EmailThread.__table__.c.search_tsv.op("@@")(tsquery_sql))
        .order_by(email_rank.desc())
        .limit(limit)
    )
    email_rows = db.execute(email_stmt).all()
    emails = [
        EmailHit(
            id=row[0].id,
            subject=row[0].subject,
            from_address=row[0].from_address,
            snippet=row[0].snippet[:200],
            rank=float(row[1] or 0),
        )
        for row in email_rows
    ]

    # --- Meetings ---
    meeting_rank = func.ts_rank(
        MeetingTranscript.__table__.c.search_tsv, tsquery_sql
    ).label("rank")
    meeting_stmt = (
        select(MeetingTranscript, meeting_rank)
        .where(MeetingTranscript.__table__.c.search_tsv.op("@@")(tsquery_sql))
        .order_by(meeting_rank.desc())
        .limit(limit)
    )
    meeting_rows = db.execute(meeting_stmt).all()
    meetings: list[MeetingHit] = []
    for t, rank in meeting_rows:
        meeting = db.get(Meeting, t.meeting_id)
        if not meeting:
            continue
        excerpt = (t.summary_markdown or t.raw_text or "")[:300]
        meetings.append(
            MeetingHit(
                id=meeting.id,
                title=meeting.title,
                excerpt=excerpt,
                rank=float(rank or 0),
            )
        )

    return SearchResponse(query=q, emails=emails, meetings=meetings)
