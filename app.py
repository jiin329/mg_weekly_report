"""Desktop shell entry point for the weekly-report-chat Desktop_App.

This module is the single Python entry point that boots the whole Desktop_App
(design.md "데스크톱 셸"). It performs the full bootstrap sequence and opens a
native pywebview window — no web browser is involved (Requirements 10.1, 10.2).

Bootstrap flow:

    1. Validate the LLM environment variables (LLM_API_KEY, LLM_ENDPOINT).
       If any is missing/empty -> halt startup and report each missing var by
       name (Requirement 10.6).
    2. Start the FastAPI backend on the local loopback port in a background
       thread. If the configured port (BACKEND_PORT) is already in use -> halt
       and report the conflicting port (Requirement 10.8).
    3. Wait for the backend health check to pass (Requirements 10.1, 10.2).
    4. Open a native pywebview Application_Window and load the built React
       frontend assets served by the backend over http, so the Frontend
       resolves the backend to the same loopback origin (design "데스크톱 셸").
    5. On any startup failure, show a shell-level error window (Requirement
       11.6) and stop — the Application_Window is never opened.

The Frontend<->Backend communication happens only over the local loopback
interface; the only outbound network call is to the external LLM API.

Because the backend package is imported as ``app`` (``backend/app`` uses
``from app.xxx`` internally), this shell adds ``backend/`` to ``sys.path`` and
imports the backend via the same ``app.*`` names. pywebview and uvicorn are
imported lazily (inside the functions that need them) so the testable bootstrap
seams can run without a display server or those packages installed.

Run (Phase 1, after building the frontend and installing backend deps):

    python app.py
"""

from __future__ import annotations

import os
import socket
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Make the backend package importable. Backend modules use ``from app.xxx``
# (see backend/app/*.py), so the ``backend`` directory must be on sys.path.
# ---------------------------------------------------------------------------
_REPO_ROOT = Path(__file__).resolve().parent
_BACKEND_DIR = _REPO_ROOT / "backend"
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

from app.config import (  # noqa: E402  (import after sys.path setup)
    BACKEND_HOST,
    DEFAULT_BACKEND_PORT,
    ENV_BACKEND_PORT,
    ENV_LLM_API_KEY,
    ENV_LLM_ENDPOINT,
)
from app.models import AppConfig  # noqa: E402

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Directory holding the built React static assets (Vite `dist`).
FRONTEND_DIST = _REPO_ROOT / "frontend" / "dist"

# Native window title.
WINDOW_TITLE = "주간보고 채팅"
ERROR_WINDOW_TITLE = "주간보고 채팅 - 시작 오류"

# How long to wait for the backend /health probe to pass before giving up.
# Requirement 10.2 budgets 10 seconds for the window to appear after the
# documented start commands complete.
HEALTH_TIMEOUT_SECONDS = 10.0
HEALTH_POLL_INTERVAL_SECONDS = 0.1


class StartupError(RuntimeError):
    """Raised when the Desktop_App cannot complete its bootstrap sequence."""


# ---------------------------------------------------------------------------
# Backend handle
# ---------------------------------------------------------------------------


@dataclass
class BackendHandle:
    """Handle to the background FastAPI server.

    ``server`` is a ``uvicorn.Server`` (typed loosely so this module imports
    without uvicorn present); ``thread`` is the daemon thread running it.
    """

    host: str
    port: int
    thread: Optional[threading.Thread] = None
    server: object = None

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    def stop(self) -> None:
        """Ask the server to exit and join its thread (best effort)."""
        server = self.server
        if server is not None:
            # uvicorn.Server honours the should_exit flag on its next loop tick.
            setattr(server, "should_exit", True)
        if self.thread is not None:
            self.thread.join(timeout=5)


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------


def resolve_backend_port() -> int:
    """Resolve the local loopback port from BACKEND_PORT (default provided)."""
    raw = os.environ.get(ENV_BACKEND_PORT, "").strip()
    if not raw:
        return DEFAULT_BACKEND_PORT
    return int(raw)


def validate_env() -> None:
    """Validate required LLM environment variables (Requirement 10.6).

    Raises ``StartupError`` naming each missing/empty required variable so the
    shell-level error window can tell the user exactly what to set.
    """
    missing = [
        name
        for name in (ENV_LLM_API_KEY, ENV_LLM_ENDPOINT)
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        raise StartupError(
            "필수 환경 변수가 설정되지 않았습니다: " + ", ".join(missing)
        )


# ---------------------------------------------------------------------------
# Port binding check
# ---------------------------------------------------------------------------


def is_port_available(host: str, port: int) -> bool:
    """Return True if ``(host, port)`` can be bound (i.e. the port is free)."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        try:
            sock.bind((host, port))
        except OSError:
            return False
    return True


# ---------------------------------------------------------------------------
# ASGI app composition (backend + built frontend assets)
# ---------------------------------------------------------------------------


def build_asgi_app():
    """Return the FastAPI app, serving the built React assets over http.

    The webview loads ``http://{host}:{port}/`` so the Frontend resolves the
    backend to the same origin (see frontend/src/api/backend.ts). The static
    mount is registered *after* the API routes so it only catches unmatched
    paths (``/``, ``/assets/*``), and is added at most once.
    """
    from app.main import app as fastapi_app

    already_mounted = any(
        getattr(route, "name", None) == "frontend" for route in fastapi_app.routes
    )
    if FRONTEND_DIST.is_dir() and not already_mounted:
        from starlette.staticfiles import StaticFiles

        fastapi_app.mount(
            "/",
            StaticFiles(directory=str(FRONTEND_DIST), html=True),
            name="frontend",
        )
    return fastapi_app


def _run_uvicorn(handle: BackendHandle) -> None:
    """Run the FastAPI app with uvicorn (blocking; runs in the background thread)."""
    import uvicorn

    asgi_app = build_asgi_app()
    server = uvicorn.Server(
        uvicorn.Config(
            asgi_app,
            host=handle.host,
            port=handle.port,
            log_level="warning",
        )
    )
    handle.server = server
    server.run()


# ---------------------------------------------------------------------------
# Backend startup
# ---------------------------------------------------------------------------


def start_backend(
    config: AppConfig,
    *,
    port_available: Callable[[str, int], bool] = is_port_available,
    run_server: Callable[[BackendHandle], None] = _run_uvicorn,
) -> BackendHandle:
    """Start the FastAPI backend in a background thread.

    Raises ``StartupError`` when a required LLM env var is missing (Req 10.6)
    or the configured local port is already in use (Req 10.8).
    """
    validate_env()

    host = BACKEND_HOST
    port = config.backendPort

    if not port_available(host, port):
        raise StartupError(
            f"로컬 포트 {port} 이(가) 이미 사용 중입니다. "
            f"BACKEND_PORT 를 변경하거나 사용 중인 프로세스를 종료해 주세요."
        )

    handle = BackendHandle(host=host, port=port)
    thread = threading.Thread(
        target=run_server,
        args=(handle,),
        name="weekly-report-backend",
        daemon=True,
    )
    handle.thread = thread
    thread.start()
    return handle


# ---------------------------------------------------------------------------
# Health probe
# ---------------------------------------------------------------------------


def _check_health(base_url: str) -> bool:
    """Return True when the backend /health endpoint responds with 200."""
    import urllib.error
    import urllib.request

    try:
        with urllib.request.urlopen(base_url + "/health", timeout=1) as resp:
            return resp.status == 200
    except (urllib.error.URLError, OSError):
        return False


def wait_for_backend(
    handle: BackendHandle,
    *,
    timeout: float = HEALTH_TIMEOUT_SECONDS,
    health_check: Callable[[str], bool] = _check_health,
    sleep: Callable[[float], None] = time.sleep,
) -> None:
    """Block until the backend is healthy or ``timeout`` seconds elapse.

    Raises ``StartupError`` if the backend never becomes healthy in time.
    """
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if health_check(handle.base_url):
            return
        sleep(HEALTH_POLL_INTERVAL_SECONDS)
    raise StartupError(
        f"백엔드가 {timeout:.0f}초 안에 준비되지 않았습니다 ({handle.base_url})."
    )


# ---------------------------------------------------------------------------
# Window creation (pywebview)
# ---------------------------------------------------------------------------


def open_window(url: str, *, webview=None) -> None:
    """Create the Application_Window and load the local Frontend URL.

    pywebview is imported lazily so this module (and its testable seams) can be
    imported without the package or a display server present.
    """
    if webview is None:
        import webview  # type: ignore

    webview.create_window(WINDOW_TITLE, url, width=1024, height=768)
    webview.start()


def _error_html(message: str) -> str:
    """Render a minimal error page for the shell-level error window."""
    safe = (
        message.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    )
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<title>시작 오류</title></head>"
        "<body style=\"font-family:sans-serif;padding:24px;color:#333\">"
        "<h2 style='color:#c0392b'>주간보고 채팅을 시작할 수 없습니다</h2>"
        f"<p>{safe}</p>"
        "<p style='color:#777;font-size:0.9em'>환경 설정을 확인한 뒤 다시 실행해 주세요.</p>"
        "</body></html>"
    )


def show_error_window(message: str, *, webview=None) -> None:
    """Show a shell-level error window describing a startup failure (Req 11.6).

    Falls back to stderr when pywebview is unavailable so the failure is never
    silent.
    """
    if webview is None:
        try:
            import webview  # type: ignore
        except ImportError:
            print(f"[시작 오류] {message}", file=sys.stderr)
            return

    webview.create_window(
        ERROR_WINDOW_TITLE, html=_error_html(message), width=640, height=360
    )
    webview.start()


# ---------------------------------------------------------------------------
# Bootstrap orchestration
# ---------------------------------------------------------------------------


def bootstrap(
    *,
    validate: Callable[[], None] = validate_env,
    load: Optional[Callable[[], AppConfig]] = None,
    start: Callable[[AppConfig], BackendHandle] = start_backend,
    wait: Callable[[BackendHandle], None] = wait_for_backend,
    open_window_fn: Callable[[str], None] = open_window,
    show_error: Callable[[str], None] = show_error_window,
) -> None:
    """Perform the full boot sequence.

    On any ``StartupError`` (missing env / port conflict / backend not ready),
    a shell-level error window is shown and the Application_Window is not opened
    (Requirements 10.6, 10.8, 11.6). Dependencies are injectable for testing.
    """
    if load is None:
        from app.config import load_config

        load = load_config

    try:
        from app.config import load_env_file

        load_env_file()  # .env를 os.environ으로 로드
        validate()
        config = load()
        handle = start(config)
        wait(handle)
    except StartupError as exc:
        show_error(str(exc))
        return

    # Startup succeeded: open the Application_Window on the Active_Chat_Room
    # (Requirements 1.1, 10.1). This call blocks until the window is closed.
    open_window_fn(handle.base_url)


if __name__ == "__main__":
    bootstrap()
