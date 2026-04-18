"""Connexion PostgreSQL + session SQLAlchemy scope tenant."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from meoxa_secretary.config import get_settings

_settings = get_settings()

engine = create_engine(
    _settings.database_url,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    """Dépendance FastAPI : session DB sans tenant (auth, bootstrap)."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@contextmanager
def tenant_session(tenant_id: str) -> Iterator[Session]:
    """
    Session DB avec `app.tenant_id` positionné pour Row-Level Security.

    Chaque table métier doit avoir une policy RLS qui lit `current_setting('app.tenant_id')`.
    """
    session = SessionLocal()
    try:
        session.execute(text("SET LOCAL app.tenant_id = :tid"), {"tid": tenant_id})
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
