"""graph_subscriptions table

Revision ID: 0004_graph_subscriptions
Revises: 0003_audit_log
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "0004_graph_subscriptions"
down_revision: str | None = "0003_audit_log"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "graph_subscriptions",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "tenant_id",
            UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("subscription_id", sa.String(128), nullable=False),
        sa.Column("resource_type", sa.String(32), nullable=False),
        sa.Column("resource_path", sa.String(512), nullable=False),
        sa.Column("change_type", sa.String(64), nullable=False, server_default="created,updated"),
        sa.Column("client_state", sa.String(128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("subscription_id", name="uq_graph_subscriptions_subscription_id"),
    )
    op.create_index("ix_graph_subscriptions_tenant_id", "graph_subscriptions", ["tenant_id"])
    op.create_index(
        "ix_graph_subscriptions_subscription_id", "graph_subscriptions", ["subscription_id"]
    )
    op.create_index("ix_graph_subscriptions_expires_at", "graph_subscriptions", ["expires_at"])

    op.execute("ALTER TABLE graph_subscriptions ENABLE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON graph_subscriptions
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid)
            WITH CHECK (tenant_id = current_setting('app.tenant_id', true)::uuid)
        """
    )


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON graph_subscriptions")
    op.execute("ALTER TABLE graph_subscriptions DISABLE ROW LEVEL SECURITY")
    op.drop_index("ix_graph_subscriptions_expires_at", table_name="graph_subscriptions")
    op.drop_index("ix_graph_subscriptions_subscription_id", table_name="graph_subscriptions")
    op.drop_index("ix_graph_subscriptions_tenant_id", table_name="graph_subscriptions")
    op.drop_table("graph_subscriptions")
