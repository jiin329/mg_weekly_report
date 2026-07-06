"""Tests for the env-based HttpLLMClient (task 6.1).

The LLM track's concrete LLMClient connects to an external LLM API using the
API key and endpoint supplied through environment variables (LLM_API_KEY,
LLM_ENDPOINT — Requirements 9.1, 9.5) and conforms to the shared interface
boundary fixed in task 1.5 (``LLMClient.generate(messages, template) ->
WeeklyReport``).

Network I/O is isolated behind a pluggable transport so these tests never touch
the network: a fake transport records what the client sent and returns a canned
raw response for the parser (task 6.3) to turn into a WeeklyReport.
"""

import json

import pytest

from app.config import ENV_LLM_API_KEY, ENV_LLM_ENDPOINT
from app.llm import DEFAULT_REPORT_TEMPLATE, LLMClient, LLMError
from app.llm_client import HttpLLMClient, LLMConfigError
from app.models import Message, WeeklyReport

_VALID_RAW = json.dumps(
    {
        "writtenDate": "2024-01-05",
        "achievements": "- API 연동 완료",
        "nextWeekPlan": "- 파싱 로직 강화",
        "issues": "- 없음",
    }
)


class _FakeTransport:
    """Records the request and returns a canned raw response."""

    def __init__(self, raw: str = _VALID_RAW, *, raise_exc: Exception | None = None):
        self._raw = raw
        self._raise_exc = raise_exc
        self.calls: list[dict] = []

    def send(self, *, endpoint: str, api_key: str, prompt: str, timeout: float) -> str:
        self.calls.append(
            {
                "endpoint": endpoint,
                "api_key": api_key,
                "prompt": prompt,
                "timeout": timeout,
            }
        )
        if self._raise_exc is not None:
            raise self._raise_exc
        return self._raw


def _user_message(content: str = "이번 주에 LLM 클라이언트를 구현했습니다.") -> Message:
    return Message(
        id="m1",
        roomId="r1",
        sender="user",
        content=content,
        createdAt="2024-01-05T00:00:00Z",
    )


def test_client_reads_api_key_and_endpoint_from_env(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "env-key")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")

    transport = _FakeTransport()
    client = HttpLLMClient(transport=transport)
    client.generate([_user_message()])

    # The env-provided credentials/endpoint are what actually get used (Req 9.5).
    assert transport.calls[0]["api_key"] == "env-key"
    assert transport.calls[0]["endpoint"] == "https://llm.example/v1"


def test_client_conforms_to_shared_llmclient_interface(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")
    # Structural conformance to the task 1.5 boundary.
    assert isinstance(HttpLLMClient(transport=_FakeTransport()), LLMClient)


def test_explicit_args_override_env(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "env-key")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://env.example/v1")

    transport = _FakeTransport()
    client = HttpLLMClient(
        api_key="explicit-key",
        endpoint="https://explicit.example/v1",
        transport=transport,
    )
    client.generate([_user_message()])

    assert transport.calls[0]["api_key"] == "explicit-key"
    assert transport.calls[0]["endpoint"] == "https://explicit.example/v1"


def test_missing_api_key_raises_and_names_the_variable(monkeypatch):
    monkeypatch.delenv(ENV_LLM_API_KEY, raising=False)
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")
    with pytest.raises(LLMConfigError) as exc:
        HttpLLMClient(transport=_FakeTransport())
    assert ENV_LLM_API_KEY in str(exc.value)
    assert ENV_LLM_API_KEY in exc.value.missing


def test_missing_endpoint_raises_and_names_the_variable(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.delenv(ENV_LLM_ENDPOINT, raising=False)
    with pytest.raises(LLMConfigError) as exc:
        HttpLLMClient(transport=_FakeTransport())
    assert ENV_LLM_ENDPOINT in str(exc.value)
    assert ENV_LLM_ENDPOINT in exc.value.missing


def test_blank_env_value_is_treated_as_missing(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "   ")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")
    with pytest.raises(LLMConfigError) as exc:
        HttpLLMClient(transport=_FakeTransport())
    assert ENV_LLM_API_KEY in exc.value.missing


def test_generate_returns_parsed_weekly_report(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")

    report = HttpLLMClient(transport=_FakeTransport()).generate([_user_message()])

    assert isinstance(report, WeeklyReport)
    assert report.writtenDate == "2024-01-05"
    assert report.achievements == "- API 연동 완료"
    assert report.nextWeekPlan == "- 파싱 로직 강화"
    assert report.issues == "- 없음"


def test_generate_sends_prompt_containing_user_message_and_sections(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")

    transport = _FakeTransport()
    HttpLLMClient(transport=transport).generate(
        [_user_message("보고서 자동화 작업을 진행했습니다.")], DEFAULT_REPORT_TEMPLATE
    )

    prompt = transport.calls[0]["prompt"]
    # The user's work note and the four template section labels reach the LLM.
    assert "보고서 자동화 작업을 진행했습니다." in prompt
    for label in ("작성일", "금주 업무 실적", "차주 업무 계획", "이슈 및 건의사항"):
        assert label in prompt


def test_transport_timeout_maps_to_llm_timeout_error(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")

    from app.llm import LLMTimeoutError

    transport = _FakeTransport(raise_exc=TimeoutError("slow"))
    with pytest.raises(LLMTimeoutError):
        HttpLLMClient(transport=transport).generate([_user_message()])


def test_transport_connection_error_maps_to_llm_unavailable(monkeypatch):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")

    from app.llm import LLMUnavailableError

    transport = _FakeTransport(raise_exc=ConnectionError("refused"))
    with pytest.raises(LLMUnavailableError):
        HttpLLMClient(transport=transport).generate([_user_message()])


def test_llm_config_error_is_an_llm_error():
    # The config failure carries the shared CONFIG_MISSING code so callers can
    # translate it into a structured error response.
    err = LLMConfigError([ENV_LLM_API_KEY])
    assert isinstance(err, LLMError)


# ---------------------------------------------------------------------------
# Task 6.4 — timeout / error handling (Requirements 9.4, 5.7)
#
# Req 9.4: an unavailable/errored/slow LLM must surface a descriptive error
# within ~5 seconds — the FAILURE-PATH budget is 5s, NOT the 30s success
# budget. These tests assert the failure budget is what the client passes to
# the transport (no real sleeps, no network) and that the error taxonomy is
# robust: timeouts -> LLM_TIMEOUT, everything else -> LLM_UNAVAILABLE.
# ---------------------------------------------------------------------------

import socket
import urllib.error

from app.llm import LLMTimeoutError, LLMUnavailableError
from app.llm_client import (
    DEFAULT_FAILURE_TIMEOUT_SECONDS,
    UrllibTransport,
)


def _client(monkeypatch, transport, **kwargs):
    monkeypatch.setenv(ENV_LLM_API_KEY, "k")
    monkeypatch.setenv(ENV_LLM_ENDPOINT, "https://llm.example/v1")
    return HttpLLMClient(transport=transport, **kwargs)


def test_default_failure_budget_is_five_seconds():
    # The default budget honours the 5s failure-path contract (Req 9.4).
    assert DEFAULT_FAILURE_TIMEOUT_SECONDS == 5.0


def test_client_passes_five_second_budget_to_transport(monkeypatch):
    transport = _FakeTransport()
    _client(monkeypatch, transport).generate([_user_message()])
    # By default the transport is given the 5s failure budget, so an
    # unreachable/slow endpoint surfaces an error within ~5s (Req 9.4).
    assert transport.calls[0]["timeout"] == 5.0


def test_failure_budget_caps_a_larger_request_timeout(monkeypatch):
    transport = _FakeTransport()
    # Even if a caller asks for the full 30s success budget, the failure budget
    # caps the wait passed to the transport so failures stay within ~5s.
    _client(monkeypatch, transport, timeout_seconds=30.0).generate([_user_message()])
    assert transport.calls[0]["timeout"] == 5.0


def test_smaller_request_timeout_is_not_raised_by_the_budget(monkeypatch):
    transport = _FakeTransport()
    # A request timeout below the budget is respected (never inflated).
    _client(monkeypatch, transport, timeout_seconds=2.0).generate([_user_message()])
    assert transport.calls[0]["timeout"] == 2.0


def test_failure_budget_is_configurable(monkeypatch):
    transport = _FakeTransport()
    _client(
        monkeypatch, transport, timeout_seconds=30.0, failure_timeout_seconds=3.0
    ).generate([_user_message()])
    assert transport.calls[0]["timeout"] == 3.0


def test_socket_timeout_maps_to_llm_timeout_with_descriptive_error(monkeypatch):
    transport = _FakeTransport(raise_exc=socket.timeout("timed out"))
    with pytest.raises(LLMTimeoutError) as exc:
        _client(monkeypatch, transport).generate([_user_message()])
    # Descriptive: carries a message and the underlying cause.
    assert str(exc.value)
    assert exc.value.details and "cause" in exc.value.details


def test_connection_refused_maps_to_llm_unavailable_with_descriptive_error(monkeypatch):
    transport = _FakeTransport(raise_exc=ConnectionRefusedError("refused"))
    with pytest.raises(LLMUnavailableError) as exc:
        _client(monkeypatch, transport).generate([_user_message()])
    assert str(exc.value)
    assert exc.value.details and "cause" in exc.value.details


def test_generic_transport_failure_maps_to_llm_unavailable(monkeypatch):
    transport = _FakeTransport(raise_exc=RuntimeError("boom"))
    with pytest.raises(LLMUnavailableError):
        _client(monkeypatch, transport).generate([_user_message()])


# --- UrllibTransport error normalisation (no real network) -----------------


class _FakeUrlopen:
    """Stand-in for urllib.request.urlopen that raises a preset exception."""

    def __init__(self, exc: Exception):
        self._exc = exc

    def __call__(self, request, timeout=None):  # noqa: D401 - matches urlopen signature
        raise self._exc


def _send_with_urlopen_error(monkeypatch, exc: Exception):
    monkeypatch.setattr(urllib.request, "urlopen", _FakeUrlopen(exc))
    return UrllibTransport().send(
        endpoint="https://llm.example/v1",
        api_key="k",
        prompt="hi",
        timeout=5.0,
    )


def test_transport_normalises_socket_timeout_to_timeouterror(monkeypatch):
    with pytest.raises(TimeoutError):
        _send_with_urlopen_error(monkeypatch, socket.timeout("timed out"))


def test_transport_normalises_urlerror_wrapped_timeout_to_timeouterror(monkeypatch):
    err = urllib.error.URLError(socket.timeout("timed out"))
    with pytest.raises(TimeoutError):
        _send_with_urlopen_error(monkeypatch, err)


def test_transport_normalises_dns_urlerror_to_connectionerror(monkeypatch):
    # A DNS / name-resolution failure is a plain URLError -> ConnectionError,
    # which the client maps to LLM_UNAVAILABLE.
    err = urllib.error.URLError(socket.gaierror("name or service not known"))
    with pytest.raises(ConnectionError):
        _send_with_urlopen_error(monkeypatch, err)


def test_transport_normalises_http_error_to_connectionerror(monkeypatch):
    # An HTTP error response (e.g. 500) from the endpoint is a transport
    # failure -> ConnectionError -> LLM_UNAVAILABLE.
    err = urllib.error.HTTPError(
        url="https://llm.example/v1/chat/completions",
        code=500,
        msg="Internal Server Error",
        hdrs=None,
        fp=None,
    )
    with pytest.raises(ConnectionError):
        _send_with_urlopen_error(monkeypatch, err)
