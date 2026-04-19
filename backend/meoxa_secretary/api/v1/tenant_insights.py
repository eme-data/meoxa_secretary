"""Endpoint Insights — métriques de valeur pour le tenant (ROI réel)."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import func, select

from meoxa_secretary.core.deps import CurrentAuth, TenantDB
from meoxa_secretary.models.email import EmailStatus, EmailThread
from meoxa_secretary.models.meeting import MeetingTranscript
from meoxa_secretary.models.usage import LlmUsageEvent

router = APIRouter()

# Hypothèses alignées sur le ROI calculator de la landing.
MIN_SAVED_PER_DRAFT = 2     # 2 min / brouillon d'email généré
MIN_SAVED_PER_CR = 40        # 40 min / compte-rendu de réunion


class DailyPoint(BaseModel):
    date: str               # YYYY-MM-DD
    drafts: int
    crs: int
    llm_cost_usd: float


class InsightsResponse(BaseModel):
    period_days: int
    drafts_generated: int
    crs_generated: int
    hours_saved: float
    time_saved_label: str           # ex: "12 h 30"
    llm_cost_usd: float
    llm_calls: int
    last_7_days: list[DailyPoint]


@router.get("", response_model=InsightsResponse)
def get_insights(auth: CurrentAuth, db: TenantDB) -> InsightsResponse:
    now = datetime.now(UTC)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    week_ago = now - timedelta(days=7)

    # --- Agrégats mensuels ---
    drafts = (
        db.scalar(
            select(func.count(EmailThread.id)).where(
                EmailThread.status.in_(
                    [EmailStatus.DRAFTED, EmailStatus.SENT]
                ),
                EmailThread.updated_at >= month_start,
            )
        )
        or 0
    )
    crs = (
        db.scalar(
            select(func.count(MeetingTranscript.id)).where(
                MeetingTranscript.summary_markdown.is_not(None),
                MeetingTranscript.updated_at >= month_start,
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
    calls = (
        db.scalar(
            select(func.count(LlmUsageEvent.id)).where(
                LlmUsageEvent.created_at >= month_start
            )
        )
        or 0
    )

    minutes_saved = drafts * MIN_SAVED_PER_DRAFT + crs * MIN_SAVED_PER_CR
    hours_saved = minutes_saved / 60

    # --- Série 7 jours ---
    daily: dict[str, dict[str, float]] = {}
    for i in range(7):
        d = (now - timedelta(days=i)).date().isoformat()
        daily[d] = {"drafts": 0, "crs": 0, "llm_cost_usd": 0.0}

    drafts_by_day = db.execute(
        select(
            func.date(EmailThread.updated_at).label("d"),
            func.count().label("n"),
        )
        .where(
            EmailThread.status.in_([EmailStatus.DRAFTED, EmailStatus.SENT]),
            EmailThread.updated_at >= week_ago,
        )
        .group_by(func.date(EmailThread.updated_at))
    ).all()
    for row in drafts_by_day:
        key = row.d.isoformat() if hasattr(row.d, "isoformat") else str(row.d)
        if key in daily:
            daily[key]["drafts"] = int(row.n)

    crs_by_day = db.execute(
        select(
            func.date(MeetingTranscript.updated_at).label("d"),
            func.count().label("n"),
        )
        .where(
            MeetingTranscript.summary_markdown.is_not(None),
            MeetingTranscript.updated_at >= week_ago,
        )
        .group_by(func.date(MeetingTranscript.updated_at))
    ).all()
    for row in crs_by_day:
        key = row.d.isoformat() if hasattr(row.d, "isoformat") else str(row.d)
        if key in daily:
            daily[key]["crs"] = int(row.n)

    cost_by_day = db.execute(
        select(
            func.date(LlmUsageEvent.created_at).label("d"),
            func.coalesce(func.sum(LlmUsageEvent.cost_micro_usd), 0).label("c"),
        )
        .where(LlmUsageEvent.created_at >= week_ago)
        .group_by(func.date(LlmUsageEvent.created_at))
    ).all()
    for row in cost_by_day:
        key = row.d.isoformat() if hasattr(row.d, "isoformat") else str(row.d)
        if key in daily:
            daily[key]["llm_cost_usd"] = int(row.c) / 1_000_000

    last_7 = sorted(
        [
            DailyPoint(
                date=d,
                drafts=int(v["drafts"]),
                crs=int(v["crs"]),
                llm_cost_usd=float(v["llm_cost_usd"]),
            )
            for d, v in daily.items()
        ],
        key=lambda p: p.date,
    )

    return InsightsResponse(
        period_days=(now - month_start).days + 1,
        drafts_generated=int(drafts),
        crs_generated=int(crs),
        hours_saved=round(hours_saved, 1),
        time_saved_label=_format_hm(minutes_saved),
        llm_cost_usd=round(int(cost_micro) / 1_000_000, 2),
        llm_calls=int(calls),
        last_7_days=last_7,
    )


def _format_hm(minutes: int) -> str:
    if minutes < 60:
        return f"{minutes} min"
    h, m = divmod(minutes, 60)
    if m == 0:
        return f"{h} h"
    return f"{h} h {m:02d}"
