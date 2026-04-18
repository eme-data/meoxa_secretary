"""Smoke test — la route /health répond 200."""

from fastapi.testclient import TestClient

from meoxa_secretary.main import app

client = TestClient(app)


def test_health() -> None:
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
