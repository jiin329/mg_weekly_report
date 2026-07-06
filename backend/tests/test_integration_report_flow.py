"""Integration wiring tests for task 8.1.

Verifies the report endpoint is wired to the real, `.env`-selected LLMClient via
`LazyLLMClient` / `build_llm_client()` instead of the BE-track `StubLLMClient`:

- LazyLLMClient defers provider construction until the first generate call.
- The atomic report flow (close room + create new active room) still holds when
  the report service runs against a lazily-built client.
- A misconfigured environment surfaces as a structured CONFIG_MISSING error
  through the HTTP layer (no partial state transition).
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api import get_report_service, get_repository
from app.config import ENV_LLM_API_KEY, ENV_LLM_ENDPOINT, ENV_LLM_PROVIDER
from app.llm import StubLLMClient
from app.llm_factory import LazyLLMClient
from app.main import app
from app.report_service import ReportService
from app.repository import Repository


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def repo(db_path):
    r = Repository(db_path)
    yield r
    r.close()


@pytest.fixture
def client(repo):
    app.dependency_overrides[get_repository] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# --- LazyLLMClient unit behavior -------------------------------------------


def test_lazy_client_does_not_build_provider_until_generate():
    calls = {"n": 0}

    def factory():
        calls["n"] += 1
        return StubLLMClient()

    lazy = LazyLLMClient(factory=factory)
    # Construction alone must not build the provider (Req: non-LLM paths work
    # without provider config).
    assert calls["n"] == 0

    lazy.generate([])
    assert calls["n"] == 1
    # Second call reuses the cached provider.
    lazy.generate([])
    assert calls["n"] == 1


# --- Atomic flow with a lazily-built (real-path) client --------------------


def test_report_endpoint_atomic_flow_with_lazy_client(client, repo):
    """The endpoint's real wiring (LazyLLMClient) drives the atomic close flow.

    A fake factory returns a StubLLMClient so no network is touched, but the
    report still flows through ReportService + LazyLLMClient exactly as in
    production.
    """
    app.dependency_overrides[get_report_service] = lambda: ReportService(
        repo, LazyLLMClient(factory=lambda: StubLLMClient())
    )

    room = client.post("/rooms").json()["room"]
    client.post(f"/rooms/{room['id']}/messages", json={"content": "이번 주 작업 완료"})

    resp = client.post(f"/rooms/{room['id']}/report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["closedRoomId"] == room["id"]
    assert body["newRoom"]["status"] == "active"
    assert body["newRoom"]["id"] != room["id"]

    # Exactly one active room remains after the atomic transition.
    rooms = client.get("/rooms").json()["rooms"]
    active = [r for r in rooms if r["status"] == "active"]
    assert len(active) == 1
    assert active[0]["id"] == body["newRoom"]["id"]


def test_report_endpoint_surfaces_config_missing_when_unconfigured(
    client, monkeypatch
):
    """The DEFAULT wiring builds the real client; a missing config -> CONFIG_MISSING.

    Uses the default get_report_service (LazyLLMClient -> build_llm_client) with
    the OpenAI provider and no credentials, so the first generation attempt fails
    with a structured CONFIG_MISSING error and the room stays active.
    """
    monkeypatch.delenv(ENV_LLM_PROVIDER, raising=False)  # default: openai
    monkeypatch.delenv(ENV_LLM_API_KEY, raising=False)
    monkeypatch.delenv(ENV_LLM_ENDPOINT, raising=False)

    room = client.post("/rooms").json()["room"]
    client.post(f"/rooms/{room['id']}/messages", json={"content": "work"})

    resp = client.post(f"/rooms/{room['id']}/report")
    assert resp.status_code == 500
    assert resp.json()["error"]["code"] == "CONFIG_MISSING"

    # No partial transition: room stays active.
    fetched = client.get("/rooms").json()["rooms"]
    assert [r["status"] for r in fetched] == ["active"]
