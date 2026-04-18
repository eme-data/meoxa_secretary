"""email pipeline fields + ms integration health

Revision ID: 0009_email_pipeline_and_ms_health
Revises: 0008_usage_invitations_planner
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_email_pipeline_and_ms_health"
down_revision: str | None = "0008_usage_invitations_planner"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "microsoft_integrations", sa.Column("last_error", sa.Text(), nullable=True)
    )
    op.add_column(
        "microsoft_integrations",
        sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.add_column(
        "email_threads", sa.Column("ms_message_id", sa.String(256), nullable=True)
    )
    op.add_column(
        "email_threads",
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("email_threads", sa.Column("body_text", sa.Text(), nullable=True))
    op.add_column(
        "email_threads", sa.Column("outlook_draft_id", sa.String(256), nullable=True)
    )
    op.create_index("ix_email_threads_received_at", "email_threads", ["received_at"])


def downgrade() -> None:
    op.drop_index("ix_email_threads_received_at", table_name="email_threads")
    op.drop_column("email_threads", "outlook_draft_id")
    op.drop_column("email_threads", "body_text")
    op.drop_column("email_threads", "received_at")
    op.drop_column("email_threads", "ms_message_id")
    op.drop_column("microsoft_integrations", "last_error_at")
    op.drop_column("microsoft_integrations", "last_error")
