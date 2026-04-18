"""mfa, branding, rgpd, billing, memory (pgvector)

Revision ID: 0005_mfa_branding_billing_memory
Revises: 0004_graph_subscriptions
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "0005_mfa_branding_billing_memory"
down_revision: str | None = "0004_graph_subscriptions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    # 1. MFA
    op.add_column(
        "users",
        sa.Column("totp_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("users", sa.Column("totp_secret", sa.String(512), nullable=True))
    op.add_column("users", sa.Column("backup_codes", sa.String(2048), nullable=True))

    # 2. Branding + RGPD
    op.add_column("tenants", sa.Column("logo_url", sa.String(1024), nullable=True))
    op.add_column("tenants", sa.Column("primary_color", sa.String(32), nullable=True))
    op.add_column("tenants", sa.Column("accent_color", sa.String(32), nullable=True))
    op.add_column(
        "tenants", sa.Column("deletion_scheduled_at", sa.DateTime(timezone=True), nullable=True)
    )

    # 3. Billing
    op.create_table(
        "tenant_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stripe_customer_id", sa.String(128), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(128), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="none"),
        sa.Column("plan", sa.String(64), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "cancel_at_period_end", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("tenant_id", name="uq_tenant_subscriptions_tenant"),
        sa.UniqueConstraint(
            "stripe_subscription_id", name="uq_tenant_subscriptions_stripe_sub"
        ),
    )
    op.create_index(
        "ix_tenant_subscriptions_tenant_id", "tenant_subscriptions", ["tenant_id"]
    )
    op.execute("ALTER TABLE tenant_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON tenant_subscriptions
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )

    # 4. pgvector + memory_entries
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        f"""
        CREATE TABLE memory_entries (
            id uuid PRIMARY KEY,
            tenant_id uuid NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            source_type varchar(32) NOT NULL,
            source_id varchar(128) NOT NULL,
            chunk_index integer NOT NULL DEFAULT 0,
            content text NOT NULL,
            embedding vector({EMBEDDING_DIM}) NOT NULL,
            meta jsonb NOT NULL DEFAULT '{{}}'::jsonb,
            created_at timestamptz NOT NULL DEFAULT now(),
            updated_at timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.create_index("ix_memory_entries_tenant_id", "memory_entries", ["tenant_id"])
    op.create_index("ix_memory_entries_source_type", "memory_entries", ["source_type"])
    op.create_index("ix_memory_entries_source_id", "memory_entries", ["source_id"])
    op.execute(
        "CREATE INDEX ix_memory_entries_embedding_hnsw ON memory_entries "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute("ALTER TABLE memory_entries ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON memory_entries
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON memory_entries")
    op.drop_index("ix_memory_entries_embedding_hnsw", table_name="memory_entries")
    op.drop_index("ix_memory_entries_source_id", table_name="memory_entries")
    op.drop_index("ix_memory_entries_source_type", table_name="memory_entries")
    op.drop_index("ix_memory_entries_tenant_id", table_name="memory_entries")
    op.drop_table("memory_entries")

    op.execute("DROP POLICY IF EXISTS tenant_isolation ON tenant_subscriptions")
    op.execute("ALTER TABLE tenant_subscriptions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_tenant_subscriptions_tenant_id", table_name="tenant_subscriptions")
    op.drop_table("tenant_subscriptions")

    op.drop_column("tenants", "deletion_scheduled_at")
    op.drop_column("tenants", "accent_color")
    op.drop_column("tenants", "primary_color")
    op.drop_column("tenants", "logo_url")

    op.drop_column("users", "backup_codes")
    op.drop_column("users", "totp_secret")
    op.drop_column("users", "totp_enabled")
