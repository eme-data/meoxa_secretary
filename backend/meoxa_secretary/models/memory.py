"""Mémoire contextuelle par tenant — chunks indexés avec embeddings pgvector.

Sert à alimenter les prompts Claude avec le passé pertinent du tenant (emails
précédents, CR de réunions, décisions) pour améliorer la qualité des réponses.
"""

from enum import StrEnum

from pgvector.sqlalchemy import Vector
from sqlalchemy import Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin

# Dimension des embeddings Voyage AI (voyage-3-large : 1024, voyage-3 : 1024).
EMBEDDING_DIM = 1024


class MemorySourceType(StrEnum):
    EMAIL = "email"
    MEETING_TRANSCRIPT = "meeting_transcript"
    MEETING_SUMMARY = "meeting_summary"
    NOTE = "note"


class MemoryEntry(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "memory_entries"
    __table_args__ = (
        Index(
            "ix_memory_entries_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    source_type: Mapped[MemorySourceType] = mapped_column(String(32), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(nullable=False, default=0)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # type: ignore[arg-type]
    embedding: Mapped[list[float]] = mapped_column(Vector(EMBEDDING_DIM), nullable=False)
    meta: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
