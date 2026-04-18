"""Templates d'emails réutilisables par tenant.

Exemples typiques : accusé de réception, rappel de paiement, demande de devis,
réponse à un candidat… L'user choisit un template, Secretary génère un brouillon
à partir du prompt du template + contexte du thread.
"""

from sqlalchemy import String, Text
from sqlalchemy.orm import Mapped, mapped_column

from meoxa_secretary.models.base import Base, TenantScopedMixin, TimestampMixin, UUIDMixin


class EmailTemplate(Base, UUIDMixin, TimestampMixin, TenantScopedMixin):
    __tablename__ = "email_templates"

    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # Prompt système qui guide Claude pour la génération
    # (ex: "Écris une réponse d'accusé de réception, polie et concise…")
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
