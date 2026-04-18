"""Tables de configuration — éditables depuis l'UI d'administration.

- `platform_settings` : clés globales plateforme (Anthropic, Microsoft, bot Teams, S3…).
  Lues par le super-admin (toi). Pas de tenant_id.
- `tenant_settings` : clés propres à chaque tenant (préférences LLM, signature, fuseau…).
  Lues par les admins du tenant.

Les valeurs sensibles (`is_secret=True`) sont chiffrées via Fernet avant persistance.
"""

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class PlatformSetting(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "platform_settings"
    __table_args__ = (UniqueConstraint("key", name="uq_platform_settings_key"),)

    key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_secret: Mapped[bool] = mapped_column(nullable=False, default=False)


class TenantSetting(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "tenant_settings"
    __table_args__ = (
        UniqueConstraint("tenant_id", "key", name="uq_tenant_settings_tenant_key"),
    )

    key: Mapped[str] = mapped_column(String(128), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False, default="")
    is_secret: Mapped[bool] = mapped_column(nullable=False, default=False)
