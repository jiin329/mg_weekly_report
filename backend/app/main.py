"""FastAPI application skeleton for the weekly-report-chat backend.

Phase 1 skeleton only. The REST endpoints (POST /rooms, GET /rooms,
GET/POST /rooms/{roomId}/messages, POST /rooms/{roomId}/report) and the
services behind them are implemented by the [BE] track tasks (see tasks.md
section 4). This module exposes a minimal app plus a health check so the
scaffold imports and runs cleanly.
"""

from fastapi import FastAPI

from . import __version__

app = FastAPI(
    title="weekly-report-chat backend",
    version=__version__,
    description="Local loopback REST API for the weekly-report-chat Desktop_App.",
)


@app.get("/health")
def health() -> dict[str, str]:
    """Liveness probe used by the desktop shell to confirm the backend started."""
    return {"status": "ok", "version": __version__}
