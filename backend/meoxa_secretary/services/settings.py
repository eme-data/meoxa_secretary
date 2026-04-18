"""Service de configuration — source unique pour les clés stockées en DB.

- Lecture : DB (chiffré si secret) → fallback env var → défaut hardcodé.
- Cache TTL 60 s par processus (acceptable pour un VPS unique avec quelques workers).
- Ajout/MAJ : `set_platform` / `set_tenant` invalident le cache local immédiatement
  et tagguent une clé Redis pour que les autres workers rechargent.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from meoxa_secretary.core.crypto import decrypt, encrypt
from meoxa_secretary.core.logging import get_logger
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.setting import PlatformSetting, TenantSetting

logger = get_logger(__name__)

SettingKind = Literal["string", "int", "bool", "select", "secret", "text"]


@dataclass(frozen=True)
class SettingDef:
    key: str
    label: str
    description: str
    kind: SettingKind
    default: str = ""
    env_var: str | None = None
    options: tuple[str, ...] = ()

    @property
    def is_secret(self) -> bool:
        return self.kind == "secret"


# --- Registre des clés connues ----------------------------------------------
# Platform : édité par le super-admin (toi).
PLATFORM_SETTINGS: tuple[SettingDef, ...] = (
    # Anthropic
    SettingDef(
        "anthropic.api_key", "Clé API Anthropic",
        "Clé utilisée pour appeler Claude (rédaction d'emails, comptes-rendus).",
        "secret", env_var="ANTHROPIC_API_KEY",
    ),
    SettingDef(
        "anthropic.model_default", "Modèle Claude — défaut",
        "Modèle utilisé pour les tâches courantes (brouillons d'emails).",
        "select", default="claude-sonnet-4-6", env_var="ANTHROPIC_MODEL_DEFAULT",
        options=("claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-7"),
    ),
    SettingDef(
        "anthropic.model_advanced", "Modèle Claude — avancé",
        "Modèle utilisé pour les synthèses de réunions.",
        "select", default="claude-opus-4-7", env_var="ANTHROPIC_MODEL_ADVANCED",
        options=("claude-sonnet-4-6", "claude-opus-4-7"),
    ),
    # Microsoft 365 (une seule app Azure partagée)
    SettingDef(
        "microsoft.client_id", "Microsoft — Client ID",
        "Application ID de l'app Azure AD multi-tenant.",
        "string", env_var="MS_CLIENT_ID",
    ),
    SettingDef(
        "microsoft.client_secret", "Microsoft — Client Secret",
        "Secret de l'app Azure AD.",
        "secret", env_var="MS_CLIENT_SECRET",
    ),
    SettingDef(
        "microsoft.tenant_id", "Microsoft — Tenant",
        "Laisser 'common' pour accepter tous les tenants Microsoft 365.",
        "string", default="common", env_var="MS_TENANT_ID",
    ),
    SettingDef(
        "microsoft.redirect_uri", "Microsoft — Redirect URI",
        "URL de callback OAuth (doit matcher la configuration Azure).",
        "string", env_var="MS_REDIRECT_URI",
    ),
    SettingDef(
        "microsoft.graph_scopes", "Microsoft — Scopes Graph",
        "Scopes demandés au consentement (séparés par des espaces).",
        "text",
        default=(
            "offline_access User.Read Mail.ReadWrite Calendars.ReadWrite "
            "OnlineMeetings.ReadWrite.All"
        ),
        env_var="MS_GRAPH_SCOPES",
    ),
    # Bot Teams
    SettingDef(
        "teams_bot.app_id", "Bot Teams — App ID",
        "Identifiant Bot Framework.", "string", env_var="BOT_APP_ID",
    ),
    SettingDef(
        "teams_bot.app_password", "Bot Teams — App Password",
        "Secret Bot Framework.", "secret", env_var="BOT_APP_PASSWORD",
    ),
    SettingDef(
        "teams_bot.tenant_id", "Bot Teams — Tenant",
        "Tenant Azure associé au bot.", "string", env_var="BOT_TENANT_ID",
    ),
    # Stockage objet
    SettingDef(
        "storage.s3_endpoint", "S3 — Endpoint",
        "Endpoint S3-compatible (laisser vide pour AWS S3).",
        "string", env_var="S3_ENDPOINT",
    ),
    SettingDef("storage.s3_bucket", "S3 — Bucket", "Nom du bucket.", "string", env_var="S3_BUCKET"),
    SettingDef(
        "storage.s3_access_key", "S3 — Access Key", "", "secret", env_var="S3_ACCESS_KEY",
    ),
    SettingDef(
        "storage.s3_secret_key", "S3 — Secret Key", "", "secret", env_var="S3_SECRET_KEY",
    ),
    SettingDef(
        "storage.s3_region", "S3 — Région", "", "string", default="auto", env_var="S3_REGION",
    ),
    # Stripe
    SettingDef(
        "stripe.api_key", "Stripe — API Key",
        "Clé secrète Stripe (sk_live_... ou sk_test_...).",
        "secret",
    ),
    SettingDef(
        "stripe.price_id", "Stripe — Price ID",
        "ID du Price Stripe pour le Pack Secrétariat (price_...).",
        "string",
    ),
    SettingDef(
        "stripe.webhook_secret", "Stripe — Webhook Secret",
        "Secret pour signer les webhooks (whsec_...). À récupérer après création du endpoint "
        "dans le dashboard Stripe.",
        "secret",
    ),
    # Voyage AI (embeddings pour RAG)
    SettingDef(
        "voyage.api_key", "Voyage AI — API Key",
        "Clé utilisée pour générer les embeddings de la mémoire tenant (RAG).",
        "secret",
    ),
    SettingDef(
        "voyage.model", "Voyage AI — Modèle embeddings",
        "Modèle d'embeddings (voyage-3-large recommandé, multilingue 1024 dims).",
        "select", default="voyage-3-large",
        options=("voyage-3-large", "voyage-3", "voyage-3-lite"),
    ),
    # Whisper (transcription locale)
    SettingDef(
        "whisper.model", "Whisper — Modèle",
        "Taille du modèle faster-whisper. 'small' = bon compromis FR/CPU.",
        "select", default="small",
        options=("tiny", "base", "small", "medium", "large-v3"),
    ),
    SettingDef(
        "whisper.compute_type", "Whisper — Compute type",
        "int8 conseillé en CPU, float16 si GPU.",
        "select", default="int8",
        options=("int8", "int8_float16", "float16", "float32"),
    ),
    SettingDef(
        "whisper.language", "Whisper — Langue",
        "Code ISO (fr, en…). Laisser vide pour détection auto.",
        "string", default="fr",
    ),
)

# Tenant : édité par les admins/owners du tenant.
TENANT_SETTINGS: tuple[SettingDef, ...] = (
    SettingDef(
        "llm.model_preference", "Modèle LLM préféré",
        "Utiliser le modèle 'défaut' (plus économe) ou 'avancé' pour ce tenant.",
        "select", default="default", options=("default", "advanced"),
    ),
    SettingDef(
        "emails.reply_tone", "Ton des réponses email",
        "Style utilisé pour générer les brouillons.",
        "select", default="professionnel",
        options=("professionnel", "amical", "concis"),
    ),
    SettingDef(
        "emails.auto_draft", "Brouillons automatiques",
        "Générer automatiquement un brouillon à la réception d'un email.",
        "bool", default="true",
    ),
    SettingDef(
        "general.timezone", "Fuseau horaire",
        "Fuseau utilisé pour les rappels d'agenda.",
        "string", default="Europe/Paris",
    ),
    SettingDef(
        "general.email_signature", "Signature email",
        "Signature ajoutée en fin de brouillons.",
        "text", default="",
    ),
    SettingDef(
        "planner.default_plan_id", "Microsoft Planner — Plan ID",
        "ID du plan Planner dans lequel les actions extraites des CR seront créées. "
        "Vide = extraction sans push Planner. Crée un plan depuis tasks.office.com puis "
        "copie l'ID depuis l'URL.",
        "string", default="",
    ),
)

PLATFORM_BY_KEY = {s.key: s for s in PLATFORM_SETTINGS}
TENANT_BY_KEY = {s.key: s for s in TENANT_SETTINGS}


# --- Cache TTL simple --------------------------------------------------------
_CACHE_TTL = 60.0
_cache: dict[str, tuple[str, float]] = {}


def _cache_get(key: str) -> str | None:
    entry = _cache.get(key)
    if not entry:
        return None
    value, expires_at = entry
    if expires_at < time.time():
        _cache.pop(key, None)
        return None
    return value


def _cache_set(key: str, value: str) -> None:
    _cache[key] = (value, time.time() + _CACHE_TTL)


def _cache_drop(key: str) -> None:
    _cache.pop(key, None)


# --- API service -------------------------------------------------------------

class SettingsService:
    """Accès unifié aux settings plateforme et tenant.

    Utilisation typique :
        settings = SettingsService()
        api_key = settings.get_platform("anthropic.api_key")
    """

    # ---- Plateforme ----

    def get_platform(self, key: str) -> str:
        definition = PLATFORM_BY_KEY.get(key)
        if not definition:
            raise KeyError(f"Platform setting inconnu: {key}")

        cache_key = f"platform:{key}"
        if (cached := _cache_get(cache_key)) is not None:
            return cached

        with SessionLocal() as db:
            row = db.scalar(select(PlatformSetting).where(PlatformSetting.key == key))
            if row and row.value:
                value = decrypt(row.value) if row.is_secret else row.value
                _cache_set(cache_key, value)
                return value

        # Fallback .env puis défaut
        env_value = os.environ.get(definition.env_var, "") if definition.env_var else ""
        value = env_value or definition.default
        _cache_set(cache_key, value)
        return value

    def list_platform(self) -> list[dict[str, Any]]:
        """Renvoie la liste des settings plateforme, avec valeurs masquées si secret."""
        with SessionLocal() as db:
            rows = {
                r.key: r
                for r in db.scalars(select(PlatformSetting)).all()
            }
        out: list[dict[str, Any]] = []
        for d in PLATFORM_SETTINGS:
            row = rows.get(d.key)
            raw = ""
            if row and row.value:
                raw = decrypt(row.value) if row.is_secret else row.value
            elif d.env_var:
                raw = os.environ.get(d.env_var, "")
            raw = raw or d.default
            out.append(
                {
                    "key": d.key,
                    "label": d.label,
                    "description": d.description,
                    "kind": d.kind,
                    "options": list(d.options),
                    "is_secret": d.is_secret,
                    "has_value": bool(raw),
                    "value": "" if d.is_secret else raw,
                    "masked": _mask_if_needed(raw, d.is_secret),
                }
            )
        return out

    def set_platform(self, key: str, value: str) -> None:
        definition = PLATFORM_BY_KEY.get(key)
        if not definition:
            raise KeyError(f"Platform setting inconnu: {key}")

        stored = encrypt(value) if definition.is_secret else value

        with SessionLocal() as db:
            row = db.scalar(select(PlatformSetting).where(PlatformSetting.key == key))
            if row:
                row.value = stored
                row.is_secret = definition.is_secret
            else:
                db.add(PlatformSetting(key=key, value=stored, is_secret=definition.is_secret))
            db.commit()

        _cache_drop(f"platform:{key}")
        logger.info("settings.platform.updated", key=key)

    # ---- Tenant ----

    def get_tenant(self, tenant_id: str, key: str) -> str:
        definition = TENANT_BY_KEY.get(key)
        if not definition:
            raise KeyError(f"Tenant setting inconnu: {key}")

        cache_key = f"tenant:{tenant_id}:{key}"
        if (cached := _cache_get(cache_key)) is not None:
            return cached

        with SessionLocal() as db:
            row = db.scalar(
                select(TenantSetting).where(
                    TenantSetting.tenant_id == tenant_id, TenantSetting.key == key
                )
            )
            if row and row.value:
                value = decrypt(row.value) if row.is_secret else row.value
                _cache_set(cache_key, value)
                return value

        _cache_set(cache_key, definition.default)
        return definition.default

    def list_tenant(self, tenant_id: str, db: Session) -> list[dict[str, Any]]:
        rows = {
            r.key: r
            for r in db.scalars(
                select(TenantSetting).where(TenantSetting.tenant_id == tenant_id)
            ).all()
        }
        out: list[dict[str, Any]] = []
        for d in TENANT_SETTINGS:
            row = rows.get(d.key)
            raw = decrypt(row.value) if row and row.is_secret and row.value else (
                row.value if row else d.default
            )
            out.append(
                {
                    "key": d.key,
                    "label": d.label,
                    "description": d.description,
                    "kind": d.kind,
                    "options": list(d.options),
                    "is_secret": d.is_secret,
                    "value": "" if d.is_secret else (raw or ""),
                    "masked": _mask_if_needed(raw or "", d.is_secret),
                }
            )
        return out

    def set_tenant(self, tenant_id: str, key: str, value: str, db: Session) -> None:
        definition = TENANT_BY_KEY.get(key)
        if not definition:
            raise KeyError(f"Tenant setting inconnu: {key}")

        stored = encrypt(value) if definition.is_secret else value

        row = db.scalar(
            select(TenantSetting).where(
                TenantSetting.tenant_id == tenant_id, TenantSetting.key == key
            )
        )
        if row:
            row.value = stored
            row.is_secret = definition.is_secret
        else:
            db.add(
                TenantSetting(
                    tenant_id=tenant_id,
                    key=key,
                    value=stored,
                    is_secret=definition.is_secret,
                )
            )
        db.flush()
        _cache_drop(f"tenant:{tenant_id}:{key}")
        logger.info("settings.tenant.updated", tenant_id=tenant_id, key=key)


def _mask_if_needed(value: str, is_secret: bool) -> str:
    if not is_secret or not value:
        return value
    if len(value) <= 4:
        return "••••"
    return f"••••{value[-4:]}"
