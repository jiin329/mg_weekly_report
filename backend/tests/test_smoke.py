"""Smoke tests for the backend scaffold.

Verify the app imports cleanly and the health endpoint responds. Feature and
property-based tests are added by the [BE]/[LLM] track tasks.
"""

from fastapi.testclient import TestClient

from app.config import DEFAULT_BACKEND_PORT
from app.main import app

client = TestClient(app)


def test_health_endpoint_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_default_backend_port_is_defined():
    assert isinstance(DEFAULT_BACKEND_PORT, int)
    assert 1024 <= DEFAULT_BACKEND_PORT <= 65535
