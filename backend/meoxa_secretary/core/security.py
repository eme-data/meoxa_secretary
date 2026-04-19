"""Hash de mots de passe + signature JWT."""

from datetime import UTC, datetime, timedelta
from typing import Any, Literal

import jwt
from passlib.context import CryptContext

from meoxa_secretary.config import get_settings

_settings = get_settings()
_pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")

TokenType = Literal["access", "refresh", "mfa_challenge"]


MFA_CHALLENGE_TTL_MINUTES = 5


def hash_password(password: str) -> str:
    return _pwd_ctx.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return _pwd_ctx.verify(plain, hashed)


def create_token(
    subject: str,
    tenant_id: str,
    token_type: TokenType = "access",
    extra_claims: dict[str, Any] | None = None,
) -> str:
    now = datetime.now(UTC)
    if token_type == "access":
        expire = now + timedelta(minutes=_settings.jwt_access_ttl_minutes)
    elif token_type == "refresh":
        expire = now + timedelta(days=_settings.jwt_refresh_ttl_days)
    else:  # mfa_challenge
        expire = now + timedelta(minutes=MFA_CHALLENGE_TTL_MINUTES)

    claims: dict[str, Any] = {
        "sub": subject,
        "tid": tenant_id,
        "typ": token_type,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
    }
    if extra_claims:
        claims.update(extra_claims)

    return jwt.encode(claims, _settings.jwt_secret, algorithm=_settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, _settings.jwt_secret, algorithms=[_settings.jwt_algorithm])
