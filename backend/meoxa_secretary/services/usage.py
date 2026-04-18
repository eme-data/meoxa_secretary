"""Enregistrement et agrégation de l'usage LLM (Claude).

Les tarifs ($/MTok) sont les prix publics Anthropic à janvier 2026. À ajuster
si les prix changent — aucun impact sur les events déjà persistés (on stocke
le coût calculé au moment du call).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import Integer, func, select, text
from sqlalchemy.orm import Session

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.usage import LlmTaskKind, LlmUsageEvent

logger = get_logger(__name__)


@dataclass(frozen=True)
class ModelPricing:
    """Prix en dollars par MTok (million de tokens)."""

    input: float
    output: float
    cache_read: float
    cache_write: float  # Écriture cache 5min (TTL court)


# Ordre : du moins cher au plus cher.
PRICING: dict[str, ModelPricing] = {
    "claude-haiku-4-5-20251001": ModelPricing(1.0, 5.0, 0.10, 1.25),
    "claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.30, 3.75),
    "claude-opus-4-7": ModelPricing(15.0, 75.0, 1.50, 18.75),
}

# Fallback si un modèle inconnu est utilisé — pas d'imputation pour ne pas
# gonfler artificiellement les coûts.
DEFAULT_PRICING = ModelPricing(0.0, 0.0, 0.0, 0.0)


class UsageService:
    """API d'enregistrement + agrégation."""

    @staticmethod
    def compute_cost_micro_usd(
        *,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cache_read_tokens: int,
        cache_write_tokens: int,
    ) -> int:
        p = PRICING.get(model, DEFAULT_PRICING)
        total_usd = (
            input_tokens * p.input / 1_000_000
            + output_tokens * p.output / 1_000_000
            + cache_read_tokens * p.cache_read / 1_000_000
            + cache_write_tokens * p.cache_write / 1_000_000
        )
        return int(round(total_usd * 1_000_000))

    @staticmethod
    def record(
        *,
        tenant_id: str | UUID,
        user_id: str | UUID | None,
        model: str,
        task_kind: LlmTaskKind,
        usage: Any,
    ) -> None:
        """Persiste un event à partir du `response.usage` de l'Anthropic SDK.

        Jamais bloquant : si l'enregistrement échoue, on loggue et on passe.
        """
        try:
            input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
            output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
            cache_read = int(getattr(usage, "cache_read_input_tokens", 0) or 0)
            cache_write = int(getattr(usage, "cache_creation_input_tokens", 0) or 0)

            cost_micro = UsageService.compute_cost_micro_usd(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read,
                cache_write_tokens=cache_write,
            )

            with SessionLocal() as db:
                db.execute(
                    text("SET LOCAL app.tenant_id = :tid"), {"tid": str(tenant_id)}
                )
                db.add(
                    LlmUsageEvent(
                        tenant_id=tenant_id,  # type: ignore[arg-type]
                        user_id=user_id,  # type: ignore[arg-type]
                        model=model,
                        task_kind=task_kind,
                        input_tokens=input_tokens,
                        output_tokens=output_tokens,
                        cache_read_tokens=cache_read,
                        cache_write_tokens=cache_write,
                        cost_micro_usd=cost_micro,
                    )
                )
                db.commit()
        except Exception as exc:
            logger.warning("usage.record.failed", error=str(exc))

    # ---------------- Agrégations (super-admin) ----------------

    @staticmethod
    def aggregate_by_tenant(
        db: Session, since: datetime | None = None
    ) -> list[dict[str, Any]]:
        """Agrège les coûts par tenant depuis `since` (défaut : début du mois courant).

        N.B. appelé par le super-admin sans RLS (session globale) — on lit cross-tenant.
        """
        if since is None:
            now = datetime.now(timezone.utc)
            since = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        rows = db.execute(
            select(
                LlmUsageEvent.tenant_id,
                func.count().label("calls"),
                func.coalesce(func.sum(LlmUsageEvent.input_tokens), 0).label("input_tokens"),
                func.coalesce(func.sum(LlmUsageEvent.output_tokens), 0).label("output_tokens"),
                func.coalesce(
                    func.sum(LlmUsageEvent.cache_read_tokens), 0
                ).label("cache_read_tokens"),
                func.coalesce(
                    func.sum(LlmUsageEvent.cost_micro_usd), 0
                ).label("cost_micro_usd"),
            )
            .where(LlmUsageEvent.created_at >= since)
            .group_by(LlmUsageEvent.tenant_id)
        ).all()

        return [
            {
                "tenant_id": str(r.tenant_id),
                "calls": int(r.calls or 0),
                "input_tokens": int(r.input_tokens or 0),
                "output_tokens": int(r.output_tokens or 0),
                "cache_read_tokens": int(r.cache_read_tokens or 0),
                "cost_micro_usd": int(r.cost_micro_usd or 0),
                "cost_usd": (r.cost_micro_usd or 0) / 1_000_000,
            }
            for r in rows
        ]
