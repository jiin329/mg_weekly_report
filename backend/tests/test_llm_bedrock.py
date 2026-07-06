"""Tests for the AWS Bedrock LLMClient (provider option B).

The Bedrock client conforms to the shared LLMClient interface (task 1.5) and
reuses the shared generate flow, so prompt composition, response parsing, and
the error taxonomy match the OpenAI-compatible client. boto3 is never touched:
a fake invoker records what the client sent and returns a canned raw response.
"""

import json

import pytest

from app.config import ENV_BEDROCK_MODEL_ID
from app.llm import (
    DEFAULT_REPORT_TEMPLATE,
    LLMClient,
    LLMTimeoutError,
    LLMUnavailableError,
)
from app.llm_bedrock import BedrockLLMClient, _extract_text
from app.llm_client import LLMConfigError
from app.models import Message, WeeklyReport

_VALID_RAW = json.dumps(
    {
        "writtenDate": "2024-01-05",
        "achievements": "- Bedrock 연동 완료",
        "nextWeekPlan": "- 파싱 강화",
        "issues": "- 없음",
    }
)


class _FakeInvoker:
    """Records the prompt/timeout and returns a canned raw response."""

    def __init__(self, raw: str = _VALID_RAW, *, raise_exc: Exception | None = None):
        self._raw = raw
        self._raise_exc = raise_exc
        self.calls: list[dict] = []

    def invoke(self, prompt: str, timeout: float) -> str:
        self.calls.append({"prompt": prompt, "timeout": timeout})
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._raw


def _user_message(content: str = "이번 주에 Bedrock 클라이언트를 구현했습니다.") -> Message:
    return Message(
        id="m1",
        roomId="r1",
        sender="user",
        content=content,
        createdAt="2024-01-05T00:00:00Z",
    )


def _client(**kwargs) -> BedrockLLMClient:
    kwargs.setdefault("model_id", "anthropic.claude-3-5-sonnet-20240620-v1:0")
    kwargs.setdefault("invoker", _FakeInvoker())
    return BedrockLLMClient(**kwargs)


def test_client_conforms_to_shared_llmclient_interface():
    assert isinstance(_client(), LLMClient)


def test_reads_model_id_from_env(monkeypatch):
    monkeypatch.setenv(ENV_BEDROCK_MODEL_ID, "env.model-id")
    client = BedrockLLMClient(invoker=_FakeInvoker())
    # No exception means the env model id satisfied the required-config check.
    assert isinstance(client, BedrockLLMClient)


def test_missing_model_id_raises_and_names_the_variable(monkeypatch):
    monkeypatch.delenv(ENV_BEDROCK_MODEL_ID, raising=False)
    with pytest.raises(LLMConfigError) as exc:
        BedrockLLMClient(invoker=_FakeInvoker())
    assert ENV_BEDROCK_MODEL_ID in str(exc.value)
    assert ENV_BEDROCK_MODEL_ID in exc.value.missing


def test_blank_model_id_is_treated_as_missing():
    with pytest.raises(LLMConfigError):
        BedrockLLMClient(model_id="   ", invoker=_FakeInvoker())


def test_generate_returns_parsed_weekly_report():
    report = _client().generate([_user_message()])
    assert isinstance(report, WeeklyReport)
    assert report.writtenDate == "2024-01-05"
    assert report.achievements == "- Bedrock 연동 완료"


def test_generate_sends_prompt_with_user_message_and_sections():
    invoker = _FakeInvoker()
    _client(invoker=invoker).generate(
        [_user_message("보고서 자동화 작업을 진행했습니다.")], DEFAULT_REPORT_TEMPLATE
    )
    prompt = invoker.calls[0]["prompt"]
    assert "보고서 자동화 작업을 진행했습니다." in prompt
    for label in ("작성일", "금주 업무 실적", "차주 업무 계획", "이슈 및 건의사항"):
        assert label in prompt


def test_default_failure_budget_passed_to_invoker():
    invoker = _FakeInvoker()
    _client(invoker=invoker, timeout_seconds=30.0).generate([_user_message()])
    # A slow/dead endpoint must surface within ~5s (Req 9.4).
    assert invoker.calls[0]["timeout"] == 5.0


def test_timeout_maps_to_llm_timeout_error():
    invoker = _FakeInvoker(raise_exc=TimeoutError("slow"))
    with pytest.raises(LLMTimeoutError) as exc:
        _client(invoker=invoker).generate([_user_message()])
    assert exc.value.details and "cause" in exc.value.details


def test_connection_error_maps_to_llm_unavailable():
    invoker = _FakeInvoker(raise_exc=ConnectionError("refused"))
    with pytest.raises(LLMUnavailableError):
        _client(invoker=invoker).generate([_user_message()])


def test_botocore_named_timeout_is_normalised(monkeypatch):
    # A botocore-style timeout (matched by class name) is normalised by the
    # invoker to TimeoutError, which the shared flow maps to LLM_TIMEOUT.
    class ReadTimeoutError(Exception):
        pass

    from app.llm_bedrock import Boto3BedrockInvoker

    invoker = Boto3BedrockInvoker(
        model_id="m", region=None, max_tokens=10, timeout=5.0
    )

    class _FakeBoto:
        def converse(self, **kwargs):
            raise ReadTimeoutError("read timed out")

    monkeypatch.setattr(invoker, "_get_client", lambda: _FakeBoto())
    with pytest.raises(TimeoutError):
        invoker.invoke("hi", 5.0)


# --- response extraction ---------------------------------------------------


def test_extract_text_from_converse_shape():
    response = {"output": {"message": {"content": [{"text": _VALID_RAW}]}}}
    assert _extract_text(response) == _VALID_RAW


def test_extract_text_falls_back_to_json_dump_on_unexpected_shape():
    response = {"unexpected": "shape"}
    # Falls back to a JSON dump so the parser can still attempt extraction.
    assert "unexpected" in _extract_text(response)
