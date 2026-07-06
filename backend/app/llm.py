"""LLM module interface boundary and shared stub (task 1.5).

This module fixes the SHARED contract between the Backend (BE) track and the LLM
track for turning a room's chat messages into a structured ``WeeklyReport``:

- ``LLMClient``   — the interface both tracks agree on. BE's ReportService
                    (task 4.7) depends only on this; the real LLM track
                    (task 6.x) provides a concrete implementation.
- ``ReportTemplate`` / ``DEFAULT_REPORT_TEMPLATE`` — the representation of the
                    Report_Template, i.e. the four report sections
                    (작성일/writtenDate, 금주 업무 실적/achievements,
                    차주 업무 계획/nextWeekPlan, 이슈 및 건의사항/issues).
- ``LLMError`` / ``LLMUnavailableError`` / ``LLMTimeoutError`` — the error
                    contract. An unreachable/errored LLM raises
                    ``LLMUnavailableError`` (maps to ``ErrorCode.LLM_UNAVAILABLE``)
                    and a slow LLM raises ``LLMTimeoutError`` (maps to
                    ``ErrorCode.LLM_TIMEOUT``). ReportService translates these
                    into structured error responses via ``app.error_codes``.
- ``StubLLMClient`` — a fixed-response implementation of ``LLMClient``. BE
                    develops against it (task 4.7); it can also be configured to
                    raise the error above for error-path testing.

The data models (``Message``, ``WeeklyReport``) and the error-code catalog are
owned by other tasks and only REUSED here; this module does not redefine them.

Contract notes (Requirements 9.1–9.4):
- 9.1/9.2: ``generate`` receives the room's user messages plus a
  ``ReportTemplate`` describing the required sections.
- 9.3: the return value is an already-parsed ``WeeklyReport`` (all four
  sections present, enforced by the model).
- 9.4/5.3/5.7: failures surface as ``LLMUnavailableError`` / ``LLMTimeoutError``
  carrying the matching ``ErrorCode``.
"""

from dataclasses import dataclass, field
from typing import Optional, Protocol, runtime_checkable

from app.error_codes import ErrorCode
from app.models import Message, WeeklyReport

# Section keys of a WeeklyReport, in display order (Requirement 5.2). Kept in
# sync with the fields of app.models.WeeklyReport.
_SECTION_KEYS = ("writtenDate", "achievements", "nextWeekPlan", "issues")

# Human-readable Korean labels used when composing the LLM prompt (task 4.7).
_SECTION_LABELS = {
    "writtenDate": "작성일",
    "achievements": "금주 업무 실적",
    "nextWeekPlan": "차주 업무 계획",
    "issues": "이슈 및 건의사항",
}


@dataclass(frozen=True)
class ReportTemplate:
    """Representation of the Report_Template passed to the LLM.

    Fixes which sections the report must contain and their Korean labels. It is
    frozen so the shared ``DEFAULT_REPORT_TEMPLATE`` cannot be mutated by a
    caller. A custom template can be constructed if a future caller needs
    different labels, but the section keys must match ``WeeklyReport``.
    """

    sections: tuple[str, ...] = _SECTION_KEYS
    section_labels: dict[str, str] = field(
        default_factory=lambda: dict(_SECTION_LABELS)
    )


# The single shared template used by BE and the LLM track.
DEFAULT_REPORT_TEMPLATE = ReportTemplate()


class LLMError(Exception):
    """Base class for LLM failures.

    Carries the ``ErrorCode`` that ReportService (task 4.7) uses to build a
    structured error response.
    """

    #: Subclasses set this to the matching catalog code.
    code: ErrorCode = ErrorCode.LLM_UNAVAILABLE

    def __init__(self, message: str = "", *, details: Optional[object] = None) -> None:
        super().__init__(message)
        self.details = details


class LLMUnavailableError(LLMError):
    """LLM API is unreachable or returned an error (Requirements 5.7, 9.4).

    Maps to ``ErrorCode.LLM_UNAVAILABLE`` (HTTP 502).
    """

    code = ErrorCode.LLM_UNAVAILABLE


class LLMTimeoutError(LLMError):
    """LLM response exceeded the allowed time (Requirements 5.3, 9.4).

    Maps to ``ErrorCode.LLM_TIMEOUT`` (HTTP 504).
    """

    code = ErrorCode.LLM_TIMEOUT


@runtime_checkable
class LLMClient(Protocol):
    """Interface for generating a WeeklyReport from chat messages.

    Both the BE stub and the real LLM implementation satisfy this Protocol.

    ``generate`` takes the room's messages and a ``ReportTemplate`` and returns a
    parsed ``WeeklyReport``. Implementations MUST raise ``LLMUnavailableError``
    when the LLM is unreachable/errored and ``LLMTimeoutError`` when it times out.
    """

    def generate(
        self,
        messages: list[Message],
        template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
    ) -> WeeklyReport:
        ...


class StubLLMClient:
    """Fixed-response ``LLMClient`` shared by the BE track (task 4.7).

    Returns a valid four-section ``WeeklyReport`` regardless of input, so BE can
    build and test the report flow before the real LLM exists. For error-path
    testing it can be configured with ``raise_error`` to raise an ``LLMError``
    (e.g. ``LLMUnavailableError`` or ``LLMTimeoutError``) instead.
    """

    def __init__(self, raise_error: Optional[LLMError] = None) -> None:
        self._raise_error = raise_error

    def generate(
        self,
        messages: list[Message],
        template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
    ) -> WeeklyReport:
        if self._raise_error is not None:
            raise self._raise_error
        return WeeklyReport(
            writtenDate="2024-01-01",
            achievements="- 주간보고 채팅 기능 인터페이스 설계 완료",
            nextWeekPlan="- 백엔드 서비스 계층 구현",
            issues="- 특이사항 없음",
        )
