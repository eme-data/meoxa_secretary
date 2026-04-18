"""Souscriptions Microsoft Graph (notifications push sur mail + calendrier + drive).

Durée de vie max côté Microsoft :
- Mail / calendrier / driveItem : 3 jours (~4230 minutes)
→ Un worker Celery renouvelle les subscriptions qui expirent dans < 24 h.

Pour RECORDINGS, `delta_url` mémorise le dernier token delta de OneDrive,
permettant de ne récupérer que les changements depuis la dernière scan.
"""

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class GraphResourceType(StrEnum):
    MAIL = "mail"                 # /me/mailFolders('inbox')/messages
    CALENDAR = "calendar"         # /me/events
    RECORDINGS = "recordings"     # /me/drive/root (filtré sur dossier Recordings)


class GraphSubscription(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "graph_subscriptions"
    __table_args__ = (
        UniqueConstraint("subscription_id", name="uq_graph_subscriptions_subscription_id"),
    )

    user_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # ID renvoyé par Microsoft Graph lors du POST /subscriptions
    subscription_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    resource_type: Mapped[GraphResourceType] = mapped_column(String(32), nullable=False)
    resource_path: Mapped[str] = mapped_column(String(512), nullable=False)
    change_type: Mapped[str] = mapped_column(String(64), nullable=False, default="created,updated")
    # Secret partagé pour valider l'authenticité des notifications entrantes.
    client_state: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    # Token delta OneDrive (uniquement pour RECORDINGS) — URL à rappeler pour obtenir
    # uniquement les changements depuis le dernier scan.
    delta_url: Mapped[str | None] = mapped_column(Text, nullable=True)
