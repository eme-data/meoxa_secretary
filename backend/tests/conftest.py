"""Fixtures pytest partagées."""

import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def _env_bootstrap():
    """Variables d'env minimales pour charger `meoxa_secretary.config`."""
    os.environ.setdefault("JWT_SECRET", "test-jwt-secret-at-least-32-chars-long")
    os.environ.setdefault(
        "SETTINGS_ENCRYPTION_KEY",
        "pXeWLB-qXkPc-n5yP0j8Z_bvJt8vHQFmjvSRlQ2qRiQ=",
    )
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql+psycopg://meoxa:test@localhost:5432/test",
    )
    os.environ.setdefault("ENVIRONMENT", "test")
