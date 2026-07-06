"""Configuration loader for the weekly-report-chat backend.

Responsibilities (task 4.1):
- Load LLM_API_KEY, LLM_ENDPOINT, BACKEND_PORT from environment variables
- Validate required vars at startup; halt with identifying error if missing
- Provide runtime CONFIG_MISSING check for the report generation flow
- Persist/reload config values across restarts (Phase 2 readiness)
"""

import json
import os
from typing import Optional

from app.models import AppConfig

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Local loopback host. Frontend<->Backend traffic never leaves the machine.
BACKEND_HOST = "127.0.0.1"

# Default local port. Overridable via BACKEND_PORT env var.
DEFAULT_BACKEND_PORT = 8756

# Required environment variable names.
ENV_LLM_API_KEY = "LLM_API_KEY"
ENV_LLM_ENDPOINT = "LLM_ENDPOINT"
ENV_BACKEND_PORT = "BACKEND_PORT"


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ConfigValidationError(Exception):
    """Raised when required configuration is missing or invalid.

    The message always identifies the missing variable(s) by name
    (Requirements 10.6, 11.9).
    """

    pass


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


def load_config() -> AppConfig:
    """Load and validate configuration from environment variables.

    Returns a valid AppConfig or raises ConfigValidationError identifying
    each missing/empty required variable by name.
    """
    missing: list[str] = []

    api_key = os.environ.get(ENV_LLM_API_KEY, "").strip()
    endpoint = os.environ.get(ENV_LLM_ENDPOINT, "").strip()
    port_str = os.environ.get(ENV_BACKEND_PORT, "").strip()

    if not api_key:
        missing.append(ENV_LLM_API_KEY)
    if not endpoint:
        missing.append(ENV_LLM_ENDPOINT)

    if missing:
        names = ", ".join(missing)
        raise ConfigValidationError(
            f"Required environment variable(s) missing or empty: {names}"
        )

    port = int(port_str) if port_str else DEFAULT_BACKEND_PORT

    return AppConfig(llmApiKey=api_key, llmEndpoint=endpoint, backendPort=port)


# ---------------------------------------------------------------------------
# Runtime validation (CONFIG_MISSING check)
# ---------------------------------------------------------------------------


def validate_runtime_config(config: AppConfig) -> None:
    """Check config validity at runtime (e.g. before report generation).

    Raises ConfigValidationError with the missing variable name(s) if any
    required LLM setting is empty (Requirement 11.9).
    """
    missing: list[str] = []

    if not config.llmApiKey.strip():
        missing.append(ENV_LLM_API_KEY)
    if not config.llmEndpoint.strip():
        missing.append(ENV_LLM_ENDPOINT)

    if missing:
        names = ", ".join(missing)
        raise ConfigValidationError(
            f"Required LLM configuration missing: {names}"
        )


# ---------------------------------------------------------------------------
# Persistence (Phase 2 readiness — Requirement 11.8)
# ---------------------------------------------------------------------------


def save_config(
    path: str,
    *,
    llm_api_key: str,
    llm_endpoint: str,
    backend_port: int,
) -> None:
    """Persist config values to a JSON file so they survive restarts."""
    data = {
        "llm_api_key": llm_api_key,
        "llm_endpoint": llm_endpoint,
        "backend_port": backend_port,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)


def load_persisted_config(path: str) -> Optional[dict]:
    """Load previously persisted config. Returns None if file doesn't exist."""
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
