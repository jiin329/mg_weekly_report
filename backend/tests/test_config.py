"""Tests for the Config loader (task 4.1).

Covers:
- Loading config from environment variables
- Startup validation (missing LLM_API_KEY / LLM_ENDPOINT raises)
- BACKEND_PORT defaults and override
- Persistence layer: save and reload config values
- Runtime CONFIG_MISSING check
"""

import os
import tempfile
from unittest.mock import patch

import pytest


class TestConfigFromEnv:
    """Config loads correctly from environment variables."""

    def test_loads_all_required_env_vars(self):
        """Valid env produces a valid AppConfig."""
        from app.config import load_config

        env = {
            "LLM_API_KEY": "test-key-123",
            "LLM_ENDPOINT": "https://api.example.com/v1",
            "BACKEND_PORT": "9000",
        }
        with patch.dict(os.environ, env, clear=False):
            config = load_config()

        assert config.llmApiKey == "test-key-123"
        assert config.llmEndpoint == "https://api.example.com/v1"
        assert config.backendPort == 9000

    def test_default_port_when_not_set(self):
        """BACKEND_PORT defaults to DEFAULT_BACKEND_PORT when env is unset."""
        from app.config import DEFAULT_BACKEND_PORT, load_config

        env = {
            "LLM_API_KEY": "key",
            "LLM_ENDPOINT": "https://llm.test",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("BACKEND_PORT", None)
            config = load_config()

        assert config.backendPort == DEFAULT_BACKEND_PORT


class TestConfigStartupValidation:
    """Missing/empty required vars halt startup with identifying messages."""

    def test_missing_api_key_raises(self):
        """Missing LLM_API_KEY raises with variable name identified."""
        from app.config import ConfigValidationError, load_config

        env = {
            "LLM_ENDPOINT": "https://llm.test",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("LLM_API_KEY", None)
            os.environ.pop("BACKEND_PORT", None)
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config()

        assert "LLM_API_KEY" in str(exc_info.value)

    def test_missing_endpoint_raises(self):
        """Missing LLM_ENDPOINT raises with variable name identified."""
        from app.config import ConfigValidationError, load_config

        env = {
            "LLM_API_KEY": "key",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("LLM_ENDPOINT", None)
            os.environ.pop("BACKEND_PORT", None)
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config()

        assert "LLM_ENDPOINT" in str(exc_info.value)

    def test_empty_api_key_raises(self):
        """Empty string LLM_API_KEY is treated as missing."""
        from app.config import ConfigValidationError, load_config

        env = {
            "LLM_API_KEY": "",
            "LLM_ENDPOINT": "https://llm.test",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("BACKEND_PORT", None)
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config()

        assert "LLM_API_KEY" in str(exc_info.value)

    def test_empty_endpoint_raises(self):
        """Empty string LLM_ENDPOINT is treated as missing."""
        from app.config import ConfigValidationError, load_config

        env = {
            "LLM_API_KEY": "key",
            "LLM_ENDPOINT": "",
        }
        with patch.dict(os.environ, env, clear=False):
            os.environ.pop("BACKEND_PORT", None)
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config()

        assert "LLM_ENDPOINT" in str(exc_info.value)

    def test_both_missing_reports_both_names(self):
        """When both required vars are missing, both names appear in error."""
        from app.config import ConfigValidationError, load_config

        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("LLM_API_KEY", None)
            os.environ.pop("LLM_ENDPOINT", None)
            os.environ.pop("BACKEND_PORT", None)
            with pytest.raises(ConfigValidationError) as exc_info:
                load_config()

        msg = str(exc_info.value)
        assert "LLM_API_KEY" in msg
        assert "LLM_ENDPOINT" in msg


class TestConfigPersistence:
    """Config values persist across save/reload (Phase 2 readiness)."""

    def test_save_and_reload(self):
        """Saved config can be reloaded with identical values."""
        from app.config import load_persisted_config, save_config

        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = os.path.join(tmpdir, "config.json")
            save_config(
                config_path,
                llm_api_key="persist-key",
                llm_endpoint="https://persist.test/v1",
                backend_port=7777,
            )
            loaded = load_persisted_config(config_path)

        assert loaded["llm_api_key"] == "persist-key"
        assert loaded["llm_endpoint"] == "https://persist.test/v1"
        assert loaded["backend_port"] == 7777

    def test_reload_nonexistent_returns_none(self):
        """Loading from a nonexistent file returns None (no config persisted yet)."""
        from app.config import load_persisted_config

        result = load_persisted_config("/nonexistent/path/config.json")
        assert result is None


class TestRuntimeConfigCheck:
    """Runtime CONFIG_MISSING check for report generation flow."""

    def test_validate_runtime_config_raises_on_missing_key(self):
        """Runtime check raises when API key is missing."""
        from app.config import ConfigValidationError, validate_runtime_config
        from app.models import AppConfig

        config = AppConfig(llmApiKey="", llmEndpoint="https://x.com", backendPort=8756)
        with pytest.raises(ConfigValidationError) as exc_info:
            validate_runtime_config(config)

        assert "LLM_API_KEY" in str(exc_info.value)

    def test_validate_runtime_config_passes_when_valid(self):
        """Runtime check passes without raising when config is valid."""
        from app.config import validate_runtime_config
        from app.models import AppConfig

        config = AppConfig(
            llmApiKey="key", llmEndpoint="https://x.com", backendPort=8756
        )
        # Should not raise
        validate_runtime_config(config)
