"""Tests for LLM response parsing (task 6.3).

``parse_report_response`` turns a raw LLM response (a JSON string or an
already-decoded dict) into a validated ``WeeklyReport`` containing all four
sections. Because all four sections are mandatory (Requirement 5.2 / 9.3), a
response that is missing (or leaves blank) any section is treated as an unusable
LLM output and surfaces as ``LLMUnavailableError`` — never a silent default.
"""

import json

import pytest

from app.llm import LLMUnavailableError
from app.llm_parsing import parse_report_response
from app.models import WeeklyReport

_VALID = {
    "writtenDate": "2024-01-01",
    "achievements": "- API 설계 완료",
    "nextWeekPlan": "- 서비스 계층 구현",
    "issues": "- 특이사항 없음",
}


def test_parses_dict_with_four_sections():
    report = parse_report_response(dict(_VALID))
    assert isinstance(report, WeeklyReport)
    assert report.writtenDate == _VALID["writtenDate"]
    assert report.achievements == _VALID["achievements"]
    assert report.nextWeekPlan == _VALID["nextWeekPlan"]
    assert report.issues == _VALID["issues"]


def test_parses_json_string():
    report = parse_report_response(json.dumps(_VALID))
    assert isinstance(report, WeeklyReport)
    assert report.issues == _VALID["issues"]


def test_parses_json_wrapped_in_markdown_fence():
    raw = f"다음은 보고서입니다:\n```json\n{json.dumps(_VALID)}\n```\n감사합니다."
    report = parse_report_response(raw)
    assert report.nextWeekPlan == _VALID["nextWeekPlan"]


def test_result_contains_all_four_sections():
    report = parse_report_response(dict(_VALID))
    assert set(report.model_dump().keys()) == {
        "writtenDate",
        "achievements",
        "nextWeekPlan",
        "issues",
    }


@pytest.mark.parametrize("missing", list(_VALID.keys()))
def test_missing_section_raises_unavailable(missing):
    partial = {k: v for k, v in _VALID.items() if k != missing}
    with pytest.raises(LLMUnavailableError):
        parse_report_response(partial)


@pytest.mark.parametrize("blank", list(_VALID.keys()))
def test_blank_section_raises_unavailable(blank):
    data = dict(_VALID)
    data[blank] = "   "
    with pytest.raises(LLMUnavailableError):
        parse_report_response(data)


def test_non_json_string_raises_unavailable():
    with pytest.raises(LLMUnavailableError):
        parse_report_response("죄송합니다, 보고서를 만들 수 없습니다.")


def test_non_object_json_raises_unavailable():
    # A JSON array is valid JSON but not the expected object shape.
    with pytest.raises(LLMUnavailableError):
        parse_report_response("[1, 2, 3]")


def test_unsupported_type_raises_unavailable():
    with pytest.raises(LLMUnavailableError):
        parse_report_response(123)  # type: ignore[arg-type]
