"""Feedback loop — récupère les éditions passées pour les injecter en few-shot.

Quand l'user pousse un brouillon dans Outlook après édition, on capture le diff
entre `suggested_reply` et `sent_reply`. Lors de la prochaine génération,
on injecte les 3 derniers exemples comme few-shot au prompt Claude.

Effet : Secretary apprend le ton du user au fil des corrections.
"""

from __future__ import annotations

from sqlalchemy import desc, select

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.models.email import EmailThread

logger = get_logger(__name__)

MAX_EXAMPLES = 3
MIN_EDIT_CHARS = 30  # pas la peine d'apprendre d'une édition mineure


def get_recent_corrections(db, tenant_id: str) -> list[tuple[str, str]]:
    """Retourne les (draft, sent) récents où l'user a vraiment édité le brouillon.

    `db` doit être une session scope tenant (RLS).
    """
    rows = db.scalars(
        select(EmailThread)
        .where(
            EmailThread.suggested_reply.is_not(None),
            EmailThread.sent_reply.is_not(None),
        )
        .order_by(desc(EmailThread.sent_at))
        .limit(20)
    ).all()

    examples: list[tuple[str, str]] = []
    for thread in rows:
        draft = thread.suggested_reply or ""
        sent = thread.sent_reply or ""
        if abs(len(draft) - len(sent)) >= MIN_EDIT_CHARS or _text_distance(draft, sent) > 0.15:
            examples.append((draft, sent))
        if len(examples) >= MAX_EXAMPLES:
            break
    return examples


def _text_distance(a: str, b: str) -> float:
    """Approximation grossière — ratio de chars différents."""
    if not a or not b:
        return 1.0
    if a == b:
        return 0.0
    n = max(len(a), len(b))
    same = sum(1 for x, y in zip(a, b, strict=False) if x == y)
    return 1.0 - (same / n)
