"""Tests for the pywebview desktop shell bootstrap (task 8.3, [INTEGRATION]).

The shell entry point lives at the repository root as ``app.py``. Because the
backend package is *also* imported as ``app`` (``backend/app``), the shell
module must be loaded by file path under a distinct module name to avoid the
name collision. We load it once here as ``desktop_shell``.

pywebview and uvicorn are NOT imported at module import time by the shell, so
these tests run without those packages driving a real window/server: the
testable bootstrap seams (env validation, port-conflict detection,
StartupError -> error-window path, happy-path window open) are exercised with
injected fakes.

Validates: Requirements 1.1, 10.1, 10.2, 10.6, 10.8, 11.6
"""

import importlib.util
import socket
import sys
from pathlib import Path

import pytest

from app.models import AppConfig

_REPO_ROOT = Path(__file__).resolve().parents[2]
_APP_PY = _REPO_ROOT / "app.py"


def _load_shell():
    """Load the root ``app.py`` as ``desktop_shell`` (avoids the ``app`` clash)."""
    spec = importlib.util.spec_from_file_location("desktop_shell", _APP_PY)
    module = importlib.util.module_from_spec(spec)
    # Register before exec so @dataclass can resolve the module namespace.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


shell = _load_shell()


def _valid_config(port: int) -> AppConfig:
    return AppConfig(
        llmApiKey="k", llmEndpoint="https://llm.example/v1", backendPort=port
    )


# ---------------------------------------------------------------------------
# resolve_backend_port
# ---------------------------------------------------------------------------


def test_resolve_backend_port_default(monkeypatch):
    monkeypatch.delenv(shell.ENV_BACKEND_PORT, raising=False)
    assert shell.resolve_backend_port() == shell.DEFAULT_BACKEND_PORT


def test_resolve_backend_port_override(monkeypatch):
    monkeypatch.setenv(shell.ENV_BACKEND_PORT, "9123")
    assert shell.resolve_backend_port() == 9123


# ---------------------------------------------------------------------------
# validate_env (Requirement 10.6)
# ---------------------------------------------------------------------------


def test_validate_env_passes_when_all_present(monkeypatch):
    monkeypatch.setenv(shell.ENV_LLM_API_KEY, "key")
    monkeypatch.setenv(shell.ENV_LLM_ENDPOINT, "https://llm.example/v1")
    # Should not raise.
    shell.validate_env()


def test_validate_env_missing_api_key_names_it(monkeypatch):
    monkeypatch.delenv(shell.ENV_LLM_API_KEY, raising=False)
    monkeypatch.setenv(shell.ENV_LLM_ENDPOINT, "https://llm.example/v1")
    with pytest.raises(shell.StartupError) as exc:
        shell.validate_env()
    assert shell.ENV_LLM_API_KEY in str(exc.value)


def test_validate_env_reports_all_missing(monkeypatch):
    monkeypatch.delenv(shell.ENV_LLM_API_KEY, raising=False)
    monkeypatch.delenv(shell.ENV_LLM_ENDPOINT, raising=False)
    with pytest.raises(shell.StartupError) as exc:
        shell.validate_env()
    msg = str(exc.value)
    assert shell.ENV_LLM_API_KEY in msg
    assert shell.ENV_LLM_ENDPOINT in msg


# ---------------------------------------------------------------------------
# is_port_available (Requirement 10.8)
# ---------------------------------------------------------------------------


def test_is_port_available_true_for_free_port():
    # Bind to port 0 to get a free port, then release it.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        free_port = s.getsockname()[1]
    assert shell.is_port_available("127.0.0.1", free_port) is True


def test_is_port_available_false_when_bound():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        s.listen(1)
        bound_port = s.getsockname()[1]
        assert shell.is_port_available("127.0.0.1", bound_port) is False


# ---------------------------------------------------------------------------
# start_backend (Requirements 10.6, 10.8)
# ---------------------------------------------------------------------------


def test_start_backend_raises_on_missing_env(monkeypatch):
    monkeypatch.delenv(shell.ENV_LLM_API_KEY, raising=False)
    monkeypatch.setenv(shell.ENV_LLM_ENDPOINT, "https://llm.example/v1")
    with pytest.raises(shell.StartupError):
        shell.start_backend(
            _valid_config(9000),
            port_available=lambda host, port: True,
            run_server=lambda handle: None,
        )


def test_start_backend_raises_on_port_conflict(monkeypatch):
    monkeypatch.setenv(shell.ENV_LLM_API_KEY, "key")
    monkeypatch.setenv(shell.ENV_LLM_ENDPOINT, "https://llm.example/v1")
    with pytest.raises(shell.StartupError) as exc:
        shell.start_backend(
            _valid_config(9111),
            port_available=lambda host, port: False,
            run_server=lambda handle: None,
        )
    # The conflicting port must be identified (Req 10.8).
    assert "9111" in str(exc.value)


def test_start_backend_returns_handle_and_starts_thread(monkeypatch):
    monkeypatch.setenv(shell.ENV_LLM_API_KEY, "key")
    monkeypatch.setenv(shell.ENV_LLM_ENDPOINT, "https://llm.example/v1")
    started = []
    handle = shell.start_backend(
        _valid_config(9222),
        port_available=lambda host, port: True,
        run_server=lambda h: started.append(h),
    )
    assert handle.port == 9222
    assert handle.host == shell.BACKEND_HOST
    assert handle.base_url == f"http://{shell.BACKEND_HOST}:9222"
    if handle.thread is not None:
        handle.thread.join(timeout=2)
    assert started == [handle]


# ---------------------------------------------------------------------------
# wait_for_backend (Requirements 10.1, 10.2)
# ---------------------------------------------------------------------------


def test_wait_for_backend_returns_when_healthy():
    handle = shell.BackendHandle(host="127.0.0.1", port=9333)
    calls = {"n": 0}

    def health_check(url):
        calls["n"] += 1
        return calls["n"] >= 2  # healthy on the second poll

    shell.wait_for_backend(
        handle, timeout=5.0, health_check=health_check, sleep=lambda _s: None
    )
    assert calls["n"] >= 2


def test_wait_for_backend_times_out():
    handle = shell.BackendHandle(host="127.0.0.1", port=9444)
    with pytest.raises(shell.StartupError):
        shell.wait_for_backend(
            handle,
            timeout=0.05,
            health_check=lambda url: False,
            sleep=lambda _s: None,
        )


# ---------------------------------------------------------------------------
# bootstrap orchestration (Requirements 1.1, 10.1, 11.6)
# ---------------------------------------------------------------------------


def test_bootstrap_happy_path_opens_window():
    opened = {}
    errors = []
    handle = shell.BackendHandle(host="127.0.0.1", port=9555)

    shell.bootstrap(
        validate=lambda: None,
        load=lambda: _valid_config(9555),
        start=lambda cfg: handle,
        wait=lambda h: None,
        open_window_fn=lambda url: opened.setdefault("url", url),
        show_error=lambda msg: errors.append(msg),
    )

    assert opened["url"] == handle.base_url
    assert errors == []


def test_bootstrap_shows_error_window_on_startup_error():
    opened = []
    errors = []

    def failing_start(cfg):
        raise shell.StartupError("port 8756 already in use")

    shell.bootstrap(
        validate=lambda: None,
        load=lambda: _valid_config(8756),
        start=failing_start,
        wait=lambda h: None,
        open_window_fn=lambda url: opened.append(url),
        show_error=lambda msg: errors.append(msg),
    )

    # Shell-level error window is shown (Req 11.6) and no app window opens.
    assert opened == []
    assert len(errors) == 1
    assert "8756" in errors[0]


def test_bootstrap_shows_error_window_on_missing_env():
    opened = []
    errors = []

    def failing_validate():
        raise shell.StartupError(f"Missing: {shell.ENV_LLM_API_KEY}")

    shell.bootstrap(
        validate=failing_validate,
        load=lambda: _valid_config(8756),
        start=lambda cfg: shell.BackendHandle(host="127.0.0.1", port=8756),
        wait=lambda h: None,
        open_window_fn=lambda url: opened.append(url),
        show_error=lambda msg: errors.append(msg),
    )

    assert opened == []
    assert errors and shell.ENV_LLM_API_KEY in errors[0]


# ---------------------------------------------------------------------------
# build_asgi_app — the webview loads the built React assets over http so the FE
# resolves the backend to the same origin (design.md "데스크톱 셸").
# ---------------------------------------------------------------------------


def test_build_asgi_app_serves_frontend_and_health():
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    asgi_app = shell.build_asgi_app()
    client = TestClient(asgi_app)

    # Health endpoint still works (used to confirm startup).
    health = client.get("/health")
    assert health.status_code == 200

    # Built React index is served at the root when the dist bundle exists.
    if shell.FRONTEND_DIST.is_dir():
        root = client.get("/")
        assert root.status_code == 200
        assert "text/html" in root.headers.get("content-type", "")
