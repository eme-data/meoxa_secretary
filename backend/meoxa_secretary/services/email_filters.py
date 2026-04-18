"""Pré-filtrage des emails entrants avant passage au LLM.

Chaque tenant peut définir :
- `emails.skip_senders` : patterns d'expéditeurs à ignorer
  (ex: "noreply@, *.newsletter.com")
- `emails.skip_subject_patterns` : motifs de sujets à ignorer
  (ex: "Re: [SPAM], Désinscription")

Si l'email matche au moins une règle, il est upsert avec status `IGNORED`
et aucun brouillon n'est généré (gain de coût LLM).
"""

from __future__ import annotations

import fnmatch

from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.services.settings import SettingsService

logger = get_logger(__name__)


def should_skip(tenant_id: str, from_address: str, subject: str) -> tuple[bool, str]:
    """Retourne (skip, reason). reason vide si pas de skip."""
    settings = SettingsService()

    sender_patterns = [
        p.strip().lower()
        for p in (settings.get_tenant(tenant_id, "emails.skip_senders") or "").split(",")
        if p.strip()
    ]
    subject_patterns = [
        p.strip().lower()
        for p in (
            settings.get_tenant(tenant_id, "emails.skip_subject_patterns") or ""
        ).split(",")
        if p.strip()
    ]

    from_lower = (from_address or "").lower()
    subject_lower = (subject or "").lower()

    for pattern in sender_patterns:
        if _matches(pattern, from_lower):
            return True, f"sender '{pattern}'"

    for pattern in subject_patterns:
        if pattern in subject_lower or _matches(pattern, subject_lower):
            return True, f"subject '{pattern}'"

    return False, ""


def _matches(pattern: str, value: str) -> bool:
    """Support glob (*) + match simple 'contient'."""
    if "*" in pattern:
        return fnmatch.fnmatch(value, pattern)
    return pattern in value
