"""Endpoint /status — health check enrichi pour monitoring.

Vérifie :
- Connexion PostgreSQL (SELECT 1)
- Connexion Redis (PING)
- Présence des credentials externes (sans les tester — juste configured/not)
"""

import redis
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from meoxa_secretary import __version__
from meoxa_secretary.config import get_settings
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.services.settings import SettingsService

router = APIRouter()


class CheckResult(BaseModel):
    ok: bool
    detail: str | None = None


class StatusResponse(BaseModel):
    status: str                      # ok | degraded | down
    version: str
    environment: str
    checks: dict[str, CheckResult]


@router.get("", response_model=StatusResponse, tags=["status"])
def status_endpoint() -> StatusResponse:
    settings = get_settings()
    checks: dict[str, CheckResult] = {}

    # DB
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
        checks["database"] = CheckResult(ok=True)
    except Exception as exc:
        checks["database"] = CheckResult(ok=False, detail=str(exc))

    # Redis
    try:
        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        client.ping()
        checks["redis"] = CheckResult(ok=True)
    except Exception as exc:
        checks["redis"] = CheckResult(ok=False, detail=str(exc))

    # Config externe (présence, sans appel réseau)
    s = SettingsService()
    checks["anthropic"] = CheckResult(
        ok=bool(s.get_platform("anthropic.api_key")),
        detail=None if s.get_platform("anthropic.api_key") else "anthropic.api_key non configurée",
    )
    checks["microsoft"] = CheckResult(
        ok=bool(s.get_platform("microsoft.client_id") and s.get_platform("microsoft.client_secret")),
        detail=None
        if s.get_platform("microsoft.client_id")
        else "microsoft.client_id/secret non configurés",
    )

    critical_ok = checks["database"].ok and checks["redis"].ok
    any_config_missing = not (checks["anthropic"].ok and checks["microsoft"].ok)
    status = "ok" if critical_ok and not any_config_missing else (
        "down" if not critical_ok else "degraded"
    )

    return StatusResponse(
        status=status,
        version=__version__,
        environment=settings.environment,
        checks=checks,
    )
