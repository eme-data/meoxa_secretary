"""onboarded_at + teams_recording_confirmed sur tenants

Revision ID: 0007_onboarding
Revises: 0006_meeting_recordings
Create Date: 2026-04-18
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_onboarding"
down_revision: str | None = "0006_meeting_recordings"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "tenants", sa.Column("onboarded_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "tenants",
        sa.Column(
            "teams_recording_confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_column("tenants", "teams_recording_confirmed")
    op.drop_column("tenants", "onboarded_at")
