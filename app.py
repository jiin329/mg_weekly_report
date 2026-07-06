"""Desktop shell entry point for the weekly-report-chat Desktop_App.

This is a Phase 1 *skeleton* that documents the bootstrap flow. The full
integration (starting FastAPI in a background thread and opening the pywebview
window) is implemented by the [INTEGRATION] track (see tasks.md section 8.3).

Bootstrap flow (per design.md "데스크톱 셸"):

    1. Validate LLM environment variables (LLM_API_KEY, LLM_ENDPOINT).
       If any is missing/empty -> halt startup and report each missing var by
       name (Requirement 10.6).
    2. Start the FastAPI backend on the local loopback port in a background
       thread. If the port (BACKEND_PORT) is already in use -> halt and report
       the conflicting port (Requirement 10.8).
    3. Wait for the backend health check to pass.
    4. Open a native pywebview Application_Window and load the built React
       frontend assets (Requirement 10.1, 10.2). No web browser is opened.
    5. On any startup failure, show a shell-level error window/message and exit.

The Frontend<->Backend communication happens only over the local loopback
interface; the only outbound network call is to the external LLM API.

Run (Phase 1, after building the frontend and installing backend deps):

    python app.py
"""

from __future__ import annotations

import os

from backend.app.config import (
    BACKEND_HOST,
    DEFAULT_BACKEND_PORT,
    ENV_BACKEND_PORT,
    ENV_LLM_API_KEY,
    ENV_LLM_ENDPOINT,
)


class StartupError(RuntimeError):
    """Raised when the Desktop_App cannot complete its bootstrap sequence."""


def resolve_backend_port() -> int:
    """Resolve the local loopback port from BACKEND_PORT (default provided)."""
    raw = os.environ.get(ENV_BACKEND_PORT, "").strip()
    if not raw:
        return DEFAULT_BACKEND_PORT
    return int(raw)


def validate_env() -> None:
    """Validate required LLM environment variables.

    Skeleton: full implementation lives in the backend Config loader (task 4.1)
    and is wired into the shell at task 8.3. Documented here to fix the contract.
    """
    missing = [
        name
        for name in (ENV_LLM_API_KEY, ENV_LLM_ENDPOINT)
        if not os.environ.get(name, "").strip()
    ]
    if missing:
        raise StartupError(
            "Missing required environment variable(s): " + ", ".join(missing)
        )


def bootstrap() -> None:
    """Perform the full boot sequence. Skeleton pending task 8.3 integration."""
    # 1. validate_env()
    # 2. start_backend(host=BACKEND_HOST, port=resolve_backend_port())
    # 3. wait for /health
    # 4. open_window(f"http://{BACKEND_HOST}:{port}")  # or local built assets
    raise NotImplementedError(
        "Desktop shell integration is implemented in task 8.3. "
        f"Planned backend at {BACKEND_HOST}:{resolve_backend_port()}."
    )


if __name__ == "__main__":
    bootstrap()
