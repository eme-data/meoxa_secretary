"""delta_url sur graph_subscriptions pour les recordings OneDrive

Revision ID: 0006_meeting_recordings
Revises: 0005_mfa_branding_billing_memory
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_meeting_recordings"
down_revision: str | None = "0005_mfa_branding_billing_memory"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "graph_subscriptions", sa.Column("delta_url", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("graph_subscriptions", "delta_url")
