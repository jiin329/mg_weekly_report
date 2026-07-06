"""Configuration loader for the weekly-report-chat backend.

Responsibilities (task 4.1):
- Load a project-root ``.env`` file into the process environment (load_env_file)
- Load LLM_API_KEY, LLM_ENDPOINT, BACKEND_PORT from environment variables
- Validate required vars at startup; halt with identifying error if missing
- Provide runtime CONFIG_MISSING check for the report generation flow
- Persist/reload config values across restarts (Phase 2 readiness)
"""

import json
import os
from pathlib import Path
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
# LLM provider selection (option A: OpenAI-compatible / option B: AWS Bedrock)
# ---------------------------------------------------------------------------
# ``LLM_PROVIDER`` selects which concrete LLMClient the factory builds
# (see ``app.llm_factory.build_llm_client``). It does not change the shared
# ``LLMClient`` interface (task 1.5) — only how the connection is made.
ENV_LLM_PROVIDER = "LLM_PROVIDER"

# Provider values.
PROVIDER_OPENAI = "openai"    # option A: OpenAI-compatible chat/completions
PROVIDER_BEDROCK = "bedrock"  # option B: AWS Bedrock (converse API)
DEFAULT_LLM_PROVIDER = PROVIDER_OPENAI

# Optional model override for the OpenAI-compatible provider (option A).
ENV_LLM_MODEL = "LLM_MODEL"

# AWS Bedrock (option B) configuration.
# - BEDROCK_MODEL_ID: required when LLM_PROVIDER=bedrock (e.g. an Anthropic
#   Claude model id or an inference-profile ARN).
# - AWS_REGION / AWS_DEFAULT_REGION: region for the bedrock-runtime client.
# Credentials come from the standard AWS chain (env keys, shared profile, or a
# Bedrock API key via AWS_BEARER_TOKEN_BEDROCK) — boto3 resolves them.
ENV_BEDROCK_MODEL_ID = "BEDROCK_MODEL_ID"
ENV_AWS_REGION = "AWS_REGION"
ENV_AWS_DEFAULT_REGION = "AWS_DEFAULT_REGION"


def resolve_provider() -> str:
    """Return the configured LLM provider (lowercased), defaulting to OpenAI."""
    return (
        os.environ.get(ENV_LLM_PROVIDER, "").strip().lower() or DEFAULT_LLM_PROVIDER
    )


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

# Project root = <root>/backend/app/config.py -> parents[2] == <root>.
# The Desktop_App keeps its ``.env`` next to ``app.py`` at the project root
# (see ``.env.example``).
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / ".env"


def load_env_file(path: Optional[str] = None, *, override: bool = False) -> bool:
    """Load variables from a ``.env`` file into ``os.environ``.

    This is the seam that lets configuration come from a ``.env`` file: it
    populates the process environment so ``load_config`` (and the LLM provider
    clients) can read the values via ``os.environ`` as they already do.

    Call this once at process startup (the desktop shell / FastAPI entrypoint)
    *before* ``load_config``. ``load_config`` itself intentionally does not call
    this, so unit tests can drive it purely from a patched ``os.environ``.

    Args:
        path: Explicit ``.env`` path. Defaults to the project-root ``.env``.
        override: When False (default), existing ``os.environ`` values win over
            file values, so real environment variables and test patches are not
            clobbered.

    Returns:
        True if a ``.env`` file was found and loaded, False otherwise.
    """
    env_path = Path(path) if path is not None else DEFAULT_ENV_FILE
    if not env_path.is_file():
        return False

    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - python-dotenv is a runtime dep
        return _load_env_file_fallback(env_path, override=override)

    return load_dotenv(dotenv_path=str(env_path), override=override)


def _load_env_file_fallback(env_path: Path, *, override: bool) -> bool:
    """Minimal ``.env`` parser used only if python-dotenv is unavailable.

    Supports ``KEY=VALUE`` lines, ignores blanks and ``#`` comments, and strips
    surrounding single/double quotes. Does not handle multiline or interpolated
    values (python-dotenv covers those when installed).
    """
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
    return True


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
