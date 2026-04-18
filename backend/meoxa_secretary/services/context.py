"""Service RAG : indexation + recherche vectorielle sur `memory_entries`."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.memory import MemoryEntry, MemorySourceType
from meoxa_secretary.services.embeddings import EmbeddingsService

logger = get_logger(__name__)

CHUNK_SIZE = 800            # caractères approx (~200 tokens)
CHUNK_OVERLAP = 100


class ContextService:
    """Indexation et récupération du contexte tenant pour Claude."""

    def __init__(self) -> None:
        self._embeddings = EmbeddingsService()

    # ---------------- Indexation ----------------

    async def index(
        self,
        *,
        tenant_id: str | UUID,
        source_type: MemorySourceType,
        source_id: str,
        content: str,
        meta: dict | None = None,
    ) -> int:
        if not self._embeddings.is_configured():
            logger.info("context.index.skipped_no_voyage")
            return 0

        chunks = _split(content)
        if not chunks:
            return 0

        vectors = await self._embeddings.embed(chunks, input_type="document")

        with self._tenant_session(str(tenant_id)) as db:
            # Remplace les anciens chunks de la même source.
            db.execute(
                text(
                    "DELETE FROM memory_entries "
                    "WHERE tenant_id = :tid AND source_type = :st AND source_id = :sid"
                ),
                {"tid": str(tenant_id), "st": source_type.value, "sid": source_id},
            )
            for idx, (chunk, vector) in enumerate(zip(chunks, vectors, strict=False)):
                db.add(
                    MemoryEntry(
                        tenant_id=tenant_id,  # type: ignore[arg-type]
                        source_type=source_type,
                        source_id=source_id,
                        chunk_index=idx,
                        content=chunk,
                        embedding=vector,
                        meta=meta or {},
                    )
                )
        return len(chunks)

    # ---------------- Recherche ----------------

    async def retrieve(
        self,
        *,
        tenant_id: str | UUID,
        query: str,
        top_k: int = 6,
        source_types: list[MemorySourceType] | None = None,
    ) -> list[MemoryEntry]:
        if not self._embeddings.is_configured():
            return []
        if not query.strip():
            return []
        [q_vector] = await self._embeddings.embed([query], input_type="query")

        with self._tenant_session(str(tenant_id)) as db:
            stmt = select(MemoryEntry)
            if source_types:
                stmt = stmt.where(MemoryEntry.source_type.in_([s.value for s in source_types]))
            stmt = stmt.order_by(MemoryEntry.embedding.cosine_distance(q_vector)).limit(top_k)
            rows = db.scalars(stmt).all()
            for r in rows:
                db.expunge(r)
        return list(rows)

    def format_for_prompt(self, entries: list[MemoryEntry], max_chars: int = 4000) -> str:
        """Met en forme le contexte récupéré pour injection dans un prompt Claude."""
        if not entries:
            return ""
        lines: list[str] = [
            "### Contexte passé du tenant (à utiliser si pertinent, sans citer verbatim) :",
        ]
        used = 0
        for e in entries:
            snippet = f"- [{e.source_type}] {e.content.strip()}"
            if used + len(snippet) > max_chars:
                break
            lines.append(snippet)
            used += len(snippet)
        return "\n".join(lines)

    # ---------------- Helpers ----------------

    @staticmethod
    def _tenant_session(tenant_id: str):
        class _Ctx:
            def __enter__(self) -> Session:
                self.session = SessionLocal()
                self.session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
                return self.session

            def __exit__(self, exc_type, exc, tb) -> None:
                try:
                    if exc_type is None:
                        self.session.commit()
                    else:
                        self.session.rollback()
                finally:
                    self.session.close()

        return _Ctx()


def _split(content: str) -> list[str]:
    content = content.strip()
    if not content:
        return []
    if len(content) <= CHUNK_SIZE:
        return [content]
    chunks: list[str] = []
    start = 0
    while start < len(content):
        end = min(start + CHUNK_SIZE, len(content))
        chunks.append(content[start:end])
        if end == len(content):
            break
        start = end - CHUNK_OVERLAP
    return chunks
