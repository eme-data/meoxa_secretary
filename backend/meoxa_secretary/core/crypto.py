"""Chiffrement symétrique Fernet pour les secrets stockés en DB."""

from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken

from meoxa_secretary.config import get_settings


@lru_cache
def _fernet() -> Fernet:
    key = get_settings().settings_encryption_key.encode()
    return Fernet(key)


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode()).decode()


def decrypt(token: str) -> str:
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode()).decode()
    except InvalidToken:
        # Valeur non chiffrée (migration en cours) — on la renvoie telle quelle
        # plutôt que de casser l'app. À nettoyer via un script de migration dédié.
        return token


def mask(value: str) -> str:
    """Renvoie une forme masquée pour affichage côté UI (ex: 'sk-••••abcd')."""
    if not value:
        return ""
    if len(value) <= 4:
        return "••••"
    return f"••••{value[-4:]}"
