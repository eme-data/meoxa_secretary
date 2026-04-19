"""Auto-détection de la signature de l'utilisateur à partir de ses envois.

Algorithme simple : récupère les 20 derniers messages du dossier `sentItems`,
extrait les N dernières lignes de chaque message, et cherche le bloc de lignes
qui apparaît à l'identique dans au moins 50% des messages. Ce bloc est très
probablement la signature.

Limites volontaires :
- On ne remplace pas une signature déjà configurée par l'utilisateur.
- On s'arrête à 8 lignes (une signature typique).
- On ignore les réponses en chaîne (les lignes « From: », « Sent: »...) en coupant
  avant ces marqueurs.
"""

from __future__ import annotations

import re
from collections import Counter

from meoxa_secretary.core.logging import get_logger

logger = get_logger(__name__)

MIN_MESSAGES = 5
SIG_MAX_LINES = 8
SIG_MIN_LINES = 2
FREQUENCY_THRESHOLD = 0.5  # signature doit apparaître dans >= 50% des mails


_HTML_TAG = re.compile(r"<[^>]+>")
_REPLY_MARKERS = re.compile(
    r"^\s*(from|de|sent|envoy[ée]|subject|objet|to|à)\s*[:：]",  # noqa: RUF001 — inclut aussi le FULLWIDTH COLON (emails asiatiques)
    re.IGNORECASE | re.MULTILINE,
)


def _html_to_text(html: str) -> str:
    if not html:
        return ""
    html = re.sub(r"<(style|script)[^>]*>.*?</\1>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    html = re.sub(r"<(br|/p|/div|/tr|/li)[^>]*>", "\n", html, flags=re.IGNORECASE)
    html = _HTML_TAG.sub(" ", html)
    html = html.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    html = re.sub(r"[ \t]+", " ", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return html.strip()


def _extract_tail(text: str, max_lines: int = SIG_MAX_LINES) -> list[str]:
    """Renvoie les dernières lignes non vides, coupé avant un marqueur de reply."""
    # Coupe avant le premier marqueur de réponse enchaînée
    match = _REPLY_MARKERS.search(text)
    if match:
        text = text[: match.start()]
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-max_lines:]


def detect_signature_from_messages(messages: list[dict]) -> str | None:
    """Renvoie la signature commune ou None si pas de pattern évident."""
    if len(messages) < MIN_MESSAGES:
        return None

    tails: list[tuple[str, ...]] = []
    for m in messages:
        body_html = m.get("body", {}).get("content", "")
        text = _html_to_text(body_html)
        if not text:
            continue
        tail = _extract_tail(text)
        if len(tail) >= SIG_MIN_LINES:
            tails.append(tuple(tail))

    if len(tails) < MIN_MESSAGES:
        return None

    # Cherche le plus long suffixe commun qui apparaît dans >= 50% des tails.
    # On part de SIG_MAX_LINES et on décroît jusqu'à trouver.
    for length in range(SIG_MAX_LINES, SIG_MIN_LINES - 1, -1):
        suffixes = [tail[-length:] for tail in tails if len(tail) >= length]
        if not suffixes:
            continue
        counter = Counter(suffixes)
        most_common, count = counter.most_common(1)[0]
        if count / len(tails) >= FREQUENCY_THRESHOLD:
            return "\n".join(most_common)
    return None
