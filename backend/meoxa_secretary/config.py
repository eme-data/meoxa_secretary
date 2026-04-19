"""Configuration globale — lue depuis l'environnement via pydantic-settings."""

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore", case_sensitive=False)

    # --- Général ---
    environment: Literal["development", "production", "test"] = "development"
    app_name: str = "meoxa_secretary"
    app_domain: str = "localhost"
    log_level: str = "INFO"

    # --- Backend ---
    backend_url: str = "http://localhost:8000"
    cors_origins: str = "http://localhost:3000"

    # --- JWT ---
    jwt_secret: str = Field(..., min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_access_ttl_minutes: int = 30
    jwt_refresh_ttl_days: int = 14

    # --- Chiffrement des secrets stockés en DB (Fernet key, 32 url-safe base64 bytes) ---
    settings_encryption_key: str = Field(..., min_length=32)

    # --- DB ---
    database_url: str

    # --- Redis / Celery ---
    redis_url: str = "redis://redis:6379/0"
    celery_broker_url: str = "redis://redis:6379/1"
    celery_result_backend: str = "redis://redis:6379/2"

    # --- Microsoft 365 ---
    ms_tenant_id: str = "common"
    ms_client_id: str = ""
    ms_client_secret: str = ""
    ms_redirect_uri: str = "http://localhost:8000/api/v1/integrations/microsoft/callback"
    ms_graph_scopes: str = (
        "offline_access User.Read Mail.ReadWrite Calendars.ReadWrite "
        "OnlineMeetings.ReadWrite.All Files.Read.All Tasks.ReadWrite"
    )

    # --- Bot Teams ---
    bot_app_id: str = ""
    bot_app_password: str = ""
    bot_tenant_id: str = ""

    # --- Anthropic ---
    anthropic_api_key: str = ""
    anthropic_model_default: str = "claude-sonnet-4-6"
    anthropic_model_advanced: str = "claude-opus-4-7"

    # --- S3 ---
    s3_endpoint: str = ""
    s3_bucket: str = ""
    s3_access_key: str = ""
    s3_secret_key: str = ""
    s3_region: str = "auto"

    # --- Observabilité (GlitchTip / Sentry) ---
    # DSN bootstrap : ne peut pas venir de la DB car les erreurs peuvent
    # survenir avant la disponibilité de la DB. Vide = no-op.
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.1

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
