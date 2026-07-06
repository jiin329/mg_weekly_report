"""Tests for the LLM prompt-composition logic (task 6.2).

``build_report_prompt`` composes a structured, deterministic prompt for the LLM
from a room's chat messages and the Report_Template. The prompt must include the
content of every 'user' message and section instructions for all four
Report_Template sections using their Korean labels (Requirements 4.3, 9.2). These
example-based tests complement the property test in task 6.5 (Property 7).
"""

from app.llm import DEFAULT_REPORT_TEMPLATE, ReportTemplate
from app.llm_prompt import build_report_prompt
from app.models import Message


def _message(
    content: str,
    *,
    sender: str = "user",
    mid: str = "m1",
) -> Message:
    return Message(
        id=mid,
        roomId="r1",
        sender=sender,  # type: ignore[arg-type]
        content=content,
        createdAt="2024-01-01T00:00:00Z",
    )


def test_prompt_includes_every_user_message_content():
    messages = [
        _message("API 설계를 완료했습니다.", mid="m1"),
        _message("테스트 코드를 작성했습니다.", mid="m2"),
        _message("다음 주 배포를 준비합니다.", mid="m3"),
    ]
    prompt = build_report_prompt(messages)
    for msg in messages:
        assert msg.content in prompt


def test_prompt_includes_all_four_section_labels():
    prompt = build_report_prompt([_message("작업 내용")])
    for label in DEFAULT_REPORT_TEMPLATE.section_labels.values():
        assert label in prompt


def test_prompt_excludes_system_messages():
    system_content = "시스템이 생성한 보고서 내용 XYZ"
    messages = [
        _message("사용자 업무 노트", sender="user", mid="m1"),
        _message(system_content, sender="system", mid="m2"),
    ]
    prompt = build_report_prompt(messages)
    assert "사용자 업무 노트" in prompt
    assert system_content not in prompt


def test_prompt_is_deterministic():
    messages = [_message("작업 A", mid="m1"), _message("작업 B", mid="m2")]
    assert build_report_prompt(messages) == build_report_prompt(messages)


def test_prompt_uses_default_template_when_omitted():
    prompt_default = build_report_prompt([_message("작업")])
    prompt_explicit = build_report_prompt([_message("작업")], DEFAULT_REPORT_TEMPLATE)
    assert prompt_default == prompt_explicit


def test_prompt_returns_string():
    assert isinstance(build_report_prompt([_message("작업")]), str)


def test_prompt_with_custom_template_labels():
    custom = ReportTemplate(
        sections=("writtenDate", "achievements", "nextWeekPlan", "issues"),
        section_labels={
            "writtenDate": "DATE_LABEL",
            "achievements": "ACH_LABEL",
            "nextWeekPlan": "PLAN_LABEL",
            "issues": "ISSUE_LABEL",
        },
    )
    prompt = build_report_prompt([_message("작업")], custom)
    for label in custom.section_labels.values():
        assert label in prompt
