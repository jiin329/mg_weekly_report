"""Tests for the LLM client factory (provider A/B selection from .env)."""

import pytest

from app.config import (
    ENV_BEDROCK_MODEL_ID,
    ENV_LLM_API_KEY,
    ENV_LLM_ENDPOINT,
    ENV_LLM_PROVIDER,
)
from app.llm_bedrock import BedrockLLMClient
from app.llm_client import HttpLLMClient, LLMConfigError
from app.llm_factory import UnsupportedProviderError, build_llm_client


def _clear_provider_env(monkeypatch):
    for name in (
        ENV_LLM_PROVIDER,
        ENV_LLM_API_KEY,
        ENV_LLM_ENDPOINT,
        ENV_BEDROCK_MODEL_ID,
    ):
        monkeypatch.delenv(name, raising=False)


def test_defaults_to_openai_when_provider_unset(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")
    assert isinstance(build_llm_client(), HttpLLMClient)


def test_openai_provider_explicit(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_PROVIDER, "openai")
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")
    assert isinstance(build_llm_client(), HttpLLMClient)


def test_provider_value_is_case_insensitive(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_PROVIDER, "  BEDROCK ")
    monkeypatch.setenv(ENV_BEDROCK_MODEL_ID, "some.model-id")
    assert isinstance(build_llm_client(), BedrockLLMClient)


def test_bedrock_provider(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_PROVIDER, "bedrock")
    monkeypatch.setenv(ENV_BEDROCK_MODEL_ID, "some.model-id")
    assert isinstance(build_llm_client(), BedrockLLMClient)


def test_openai_missing_config_raises(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_PROVIDER, "openai")
    with pytest.raises(LLMConfigError):
        build_llm_client()


def test_bedrock_missing_model_id_raises(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_PROVIDER, "bedrock")
    with pytest.raises(LLMConfigError):
        build_llm_client()


def test_unknown_provider_raises(monkeypatch):
    _clear_provider_env(monkeypatch)
    monkeypatch.setenv(ENV_LLM_PROVIDER, "azure")
    with pytest.raises(UnsupportedProviderError) as exc:
        build_llm_client()
    assert "azure" in str(exc.value)
