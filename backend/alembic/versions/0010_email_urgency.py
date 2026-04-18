"""email urgency column + index

Revision ID: 0010_email_urgency
Revises: 0009_email_pipeline_ms_health
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_email_urgency"
down_revision: str | None = "0009_email_pipeline_ms_health"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "email_threads",
        sa.Column(
            "urgency",
            sa.String(32),
            nullable=False,
            server_default="unknown",
        ),
    )
    op.create_index("ix_email_threads_urgency", "email_threads", ["urgency"])


def downgrade() -> None:
    op.drop_index("ix_email_threads_urgency", table_name="email_threads")
    op.drop_column("email_threads", "urgency")
