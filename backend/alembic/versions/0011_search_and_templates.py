"""full-text search + email templates + feedback loop + notion integration

Revision ID: 0011_search_and_templates
Revises: 0010_email_urgency
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0011_search_and_templates"
down_revision: str | None = "0010_email_urgency"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Full-text search — colonnes tsvector auto-calculées + index GIN.
    op.execute(
        """
        ALTER TABLE email_threads
          ADD COLUMN search_tsv tsvector GENERATED ALWAYS AS (
            setweight(to_tsvector('french', coalesce(subject, '')), 'A') ||
            setweight(to_tsvector('french', coalesce(from_address, '')), 'B') ||
            setweight(to_tsvector('french', coalesce(body_text, snippet)), 'C')
          ) STORED
        """
    )
    op.create_index(
        "ix_email_threads_search_tsv",
        "email_threads",
        ["search_tsv"],
        postgresql_using="gin",
    )
    op.execute(
        """
        ALTER TABLE meeting_transcripts
          ADD COLUMN search_tsv tsvector GENERATED ALWAYS AS (
            setweight(to_tsvector('french', coalesce(summary_markdown, '')), 'A') ||
            setweight(to_tsvector('french', coalesce(raw_text, '')), 'C')
          ) STORED
        """
    )
    op.create_index(
        "ix_meeting_transcripts_search_tsv",
        "meeting_transcripts",
        ["search_tsv"],
        postgresql_using="gin",
    )

    # 2. Email templates — tenant-scoped.
    op.create_table(
        "email_templates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_email_templates_tenant_id", "email_templates", ["tenant_id"]
    )
    op.execute("ALTER TABLE email_templates ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON email_templates
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )

    # 3. Feedback loop — captures des éditions utilisateur sur les brouillons.
    op.add_column(
        "email_threads",
        sa.Column("sent_reply", sa.Text(), nullable=True),
    )
    op.add_column(
        "email_threads",
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Notion : champ pour persister l'ID de page créée par CR (pour déduplication).
    op.add_column(
        "meeting_transcripts",
        sa.Column("notion_page_ids_json", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_transcripts", "notion_page_ids_json")
    op.drop_column("email_threads", "sent_at")
    op.drop_column("email_threads", "sent_reply")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON email_templates")
    op.drop_index("ix_email_templates_tenant_id", table_name="email_templates")
    op.drop_table("email_templates")

    op.drop_index(
        "ix_meeting_transcripts_search_tsv", table_name="meeting_transcripts"
    )
    op.execute("ALTER TABLE meeting_transcripts DROP COLUMN search_tsv")
    op.drop_index("ix_email_threads_search_tsv", table_name="email_threads")
    op.execute("ALTER TABLE email_threads DROP COLUMN search_tsv")
