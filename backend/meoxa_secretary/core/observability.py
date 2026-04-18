"""Intégration sentry-sdk — fonctionne aussi bien avec Sentry qu'avec GlitchTip.

GlitchTip expose la même API d'ingestion que Sentry, donc le même SDK côté client.
Si `SENTRY_DSN` est vide (défaut en dev), l'init est un no-op — aucun event envoyé.

Init appelée tôt dans :
- `main.py` (FastAPI) avant le démarrage de l'app
- `workers/celery_app.py` avant le `Celery(...)`
"""

from __future__ import annotations

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from meoxa_secretary.config import get_settings

_initialized = False


def init_sentry() -> None:
    """Idempotent. No-op si `SENTRY_DSN` vide."""
    global _initialized
    if _initialized:
        return

    settings = get_settings()
    dsn = settings.sentry_dsn
    if not dsn:
        return

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        release=f"{settings.app_name}@{_version()}",
        integrations=[
            FastApiIntegration(transaction_style="endpoint"),
            StarletteIntegration(transaction_style="endpoint"),
            CeleryIntegration(monitor_beat_tasks=True),
            SqlalchemyIntegration(),
            RedisIntegration(),
            AsyncioIntegration(),
        ],
        # Échantillonnage — ajustable via env. Par défaut 10% des transactions.
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,   # RGPD — ne pas envoyer IP/emails automatiquement
        attach_stacktrace=True,
        before_send=_scrub_pii,
    )
    _initialized = True


def _version() -> str:
    try:
        from meoxa_secretary import __version__

        return __version__
    except ImportError:
        return "unknown"


def _scrub_pii(event, _hint):
    """Masque les champs sensibles avant envoi à GlitchTip/Sentry."""
    # Supprime les headers d'auth
    request = event.get("request", {})
    headers = request.get("headers", {})
    for key in list(headers.keys()):
        if key.lower() in ("authorization", "cookie", "x-api-key"):
            headers[key] = "[redacted]"
    # Masque les valeurs contenant "secret"/"password"/"token" dans les query/data
    for section in ("query_string", "data"):
        val = request.get(section)
        if isinstance(val, dict):
            for k in list(val.keys()):
                if any(s in k.lower() for s in ("password", "secret", "token")):
                    val[k] = "[redacted]"
    return event
