"""Tests for the shared LLM module interface boundary (task 1.5).

Covers the interface/exception/stub contract that the BE track develops against
and the LLM track implements: the LLMClient interface signature, the dedicated
timeout/unavailable exceptions carrying the shared ErrorCode, and the shared
stub client returning a valid four-section WeeklyReport.
"""

import pytest

from app.error_codes import ErrorCode
from app.llm import (
    DEFAULT_REPORT_TEMPLATE,
    LLMClient,
    LLMError,
    LLMTimeoutError,
    LLMUnavailableError,
    ReportTemplate,
    StubLLMClient,
)
from app.models import Message, WeeklyReport


def _user_message(content: str = "이번 주에 API 설계를 완료했습니다.") -> Message:
    return Message(
        id="m1",
        roomId="r1",
        sender="user",
        content=content,
        createdAt="2024-01-01T00:00:00Z",
    )


def test_report_template_defines_the_four_sections():
    # The template describes the four report sections from Requirement 5.2.
    assert DEFAULT_REPORT_TEMPLATE.sections == (
        "writtenDate",
        "achievements",
        "nextWeekPlan",
        "issues",
    )
    # Each section carries a human-readable Korean label for the prompt.
    assert set(DEFAULT_REPORT_TEMPLATE.section_labels) == {
        "writtenDate",
        "achievements",
        "nextWeekPlan",
        "issues",
    }


def test_stub_is_an_llm_client():
    # The stub must satisfy the shared interface so BE and LLM tracks agree.
    assert isinstance(StubLLMClient(), LLMClient)


def test_stub_generate_returns_valid_four_section_report():
    stub = StubLLMClient()
    report = stub.generate([_user_message()], DEFAULT_REPORT_TEMPLATE)

    assert isinstance(report, WeeklyReport)
    # All four sections present and non-empty (Requirement 5.2 / Property 8).
    assert report.writtenDate.strip()
    assert report.achievements.strip()
    assert report.nextWeekPlan.strip()
    assert report.issues.strip()


def test_stub_generate_uses_default_template_when_omitted():
    report = StubLLMClient().generate([_user_message()])
    assert isinstance(report, WeeklyReport)


def test_stub_can_be_configured_to_raise_unavailable():
    stub = StubLLMClient(raise_error=LLMUnavailableError("down"))
    with pytest.raises(LLMUnavailableError) as exc:
        stub.generate([_user_message()], DEFAULT_REPORT_TEMPLATE)
    # Unavailable maps to LLM_UNAVAILABLE (Requirements 9.4 / 5.7).
    assert exc.value.code is ErrorCode.LLM_UNAVAILABLE


def test_stub_can_be_configured_to_raise_timeout():
    stub = StubLLMClient(raise_error=LLMTimeoutError("slow"))
    with pytest.raises(LLMTimeoutError) as exc:
        stub.generate([_user_message()], DEFAULT_REPORT_TEMPLATE)
    # Timeout maps to LLM_TIMEOUT (Requirements 9.4 / 5.3).
    assert exc.value.code is ErrorCode.LLM_TIMEOUT


def test_llm_errors_share_a_base_and_expose_error_code():
    unavailable = LLMUnavailableError("x")
    timeout = LLMTimeoutError("y")
    assert isinstance(unavailable, LLMError)
    assert isinstance(timeout, LLMError)
    assert unavailable.code is ErrorCode.LLM_UNAVAILABLE
    assert timeout.code is ErrorCode.LLM_TIMEOUT


def test_report_template_is_immutable_contract():
    # A caller must not accidentally mutate the shared default template.
    with pytest.raises(Exception):
        DEFAULT_REPORT_TEMPLATE.sections = ("x",)  # type: ignore[misc]
    assert isinstance(ReportTemplate, type)
