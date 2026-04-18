"""Dépendances FastAPI : authentification + scope tenant."""

from collections.abc import Iterator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from meoxa_secretary.core.security import decode_token
from meoxa_secretary.database import SessionLocal
from meoxa_secretary.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


class AuthContext:
    """Contexte résolu par la dépendance `current_user` : user + tenant_id actif."""

    def __init__(self, user: User, tenant_id: str) -> None:
        self.user = user
        self.tenant_id = tenant_id


def get_db_with_tenant(tenant_id: str) -> Iterator[Session]:
    """Session DB avec `app.tenant_id` positionné pour RLS."""
    session = SessionLocal()
    try:
        session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def current_auth(
    token: Annotated[str | None, Depends(oauth2_scheme)],
) -> AuthContext:
    """Décode le JWT et renvoie le contexte (user_id, tenant_id)."""
    if not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token manquant")

    try:
        payload = decode_token(token)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expiré") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalide") from exc

    if payload.get("typ") != "access":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Type de token invalide")

    user_id = payload.get("sub")
    tenant_id = payload.get("tid")
    if not user_id or not tenant_id:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Claims manquants")

    # On charge l'utilisateur dans une session scopée au tenant (RLS).
    session = SessionLocal()
    try:
        session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": tenant_id})
        user = session.get(User, user_id)
        if not user or not user.is_active:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Utilisateur inconnu ou désactivé")
        return AuthContext(user=user, tenant_id=tenant_id)
    finally:
        session.close()


CurrentAuth = Annotated[AuthContext, Depends(current_auth)]


def tenant_db(auth: CurrentAuth) -> Iterator[Session]:
    """Session scopée au tenant courant — à utiliser dans les routes métier."""
    yield from get_db_with_tenant(auth.tenant_id)


TenantDB = Annotated[Session, Depends(tenant_db)]


def require_superadmin(auth: CurrentAuth) -> AuthContext:
    """Dépendance pour les routes réservées au super-admin plateforme."""
    if not auth.user.is_superadmin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Accès super-admin requis")
    return auth


SuperAdmin = Annotated[AuthContext, Depends(require_superadmin)]


def require_tenant_admin(auth: CurrentAuth) -> AuthContext:
    """Dépendance pour les routes de configuration tenant (OWNER ou ADMIN uniquement)."""
    from meoxa_secretary.models.user import Role

    # On recharge le membership dans une session scopée au tenant.
    with SessionLocal() as session:
        session.execute(text("SELECT set_config('app.tenant_id', :tid, true)"), {"tid": auth.tenant_id})
        from meoxa_secretary.models.user import Membership

        membership = session.scalar(
            select(Membership).where(
                Membership.user_id == auth.user.id, Membership.tenant_id == auth.tenant_id
            )
        )
    if not membership or membership.role not in (Role.OWNER, Role.ADMIN):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Rôle admin requis")
    return auth


TenantAdmin = Annotated[AuthContext, Depends(require_tenant_admin)]
