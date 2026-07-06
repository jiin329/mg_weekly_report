"""Prompt-composition logic for the LLM track (task 6.2).

``build_report_prompt`` turns a room's chat messages and a ``ReportTemplate``
into a single structured, deterministic prompt string for the LLM. It is a pure
function: no network calls, no environment access, no randomness — the same
inputs always produce the same output.

Contract (Requirements 4.3, 9.2; validated by Property 7 in task 6.5):
- Every 'user' message's content is included in the prompt (the user's work
  notes). 'system' messages are excluded, since they are not user input.
- Instructions for all four Report_Template sections are included using their
  Korean labels (작성일, 금주 업무 실적, 차주 업무 계획, 이슈 및 건의사항).

This module only REUSES the shared contract in ``app.llm`` and the ``Message``
model; it does not redefine or modify them.
"""

from app.llm import DEFAULT_REPORT_TEMPLATE, ReportTemplate
from app.models import Message

_SYSTEM_INSTRUCTION = (
    "당신은 주간 업무 보고서 작성 assistant입니다. "
    "아래 대화 내용을 바탕으로 다음 네 개의 섹션으로 구성된 주간 보고서를 작성하세요."
)


def build_report_prompt(
    messages: list[Message],
    template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
) -> str:
    """Compose a structured prompt from user messages and the report template.

    This is the shared interface consumed by the LLM client (task 6.1) and the
    parser boundary (task 6.3).

    Args:
        messages: the room's chat messages. Only 'user' messages are included as
            work notes; 'system' messages are filtered out.
        template: the Report_Template describing the required sections and their
            Korean labels. Defaults to the shared ``DEFAULT_REPORT_TEMPLATE``.

    Returns:
        A single deterministic prompt string containing every user message's
        content and instructions for all four template sections.
    """
    user_contents = [m.content for m in messages if m.sender == "user"]

    lines: list[str] = [_SYSTEM_INSTRUCTION, ""]

    # Section instructions, in the template's declared section order.
    lines.append("## 보고서 섹션 (Report_Template)")
    for key in template.sections:
        label = template.section_labels.get(key, key)
        lines.append(f"- {label}: 이 섹션의 내용을 작성하세요.")
    lines.append("")

    # User work notes.
    lines.append("## 대화 내용 (사용자 업무 노트)")
    if user_contents:
        for content in user_contents:
            lines.append(f"- {content}")
    else:
        lines.append("- (작성된 내용 없음)")

    return "\n".join(lines)


# Backward-compatible alias. ``build_prompt`` was the original public name and is
# imported by the LLM client (task 6.1, ``app.llm_client``); ``build_report_prompt``
# is the canonical name used by the prompt tests and this module's docstring. Both
# refer to the same pure function, so neither consumer breaks.
build_prompt = build_report_prompt
