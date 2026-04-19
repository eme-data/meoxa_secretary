"""Point d'entrée FastAPI."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from meoxa_secretary.api.v1 import api_router
from meoxa_secretary.config import get_settings
from meoxa_secretary.core.logging import configure_logging
from meoxa_secretary.core.observability import init_sentry
from meoxa_secretary.core.rate_limit import limiter

# Init Sentry/GlitchTip avant la création de l'app FastAPI — les intégrations
# FastApi/Starlette/Sqlalchemy/Redis captureront ensuite toutes les exceptions.
# No-op si SENTRY_DSN n'est pas défini (cas dev/CI).
init_sentry()

settings = get_settings()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging(settings.log_level)
    yield


app = FastAPI(
    title="meoxa_secretary API",
    version="0.1.0",
    description="API SaaS multi-tenant — emails, CR réunions, agenda.",
    lifespan=lifespan,
    docs_url="/docs" if not settings.is_production else None,
    redoc_url=None,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["health"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
