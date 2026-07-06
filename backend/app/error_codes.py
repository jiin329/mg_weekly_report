"""Shared error-code catalog and HTTP status mapping (task 1.4).

This module is the single source of truth on the Backend for the structured
error codes defined in design.md's "오류 코드 카탈로그". It mirrors the
TypeScript catalog in `frontend/src/types/errorCodes.ts`; both sides must be
kept in sync.

The error *shape* (ErrorResponse / ErrorDetail) is owned by task 1.2 and lives
in `app.models`. This module does NOT redefine it — it reuses those models and
only adds the code catalog, the HTTP status mapping, and a small builder.

Every failing endpoint should return an ErrorResponse whose `error.code` is one
of these codes, and should send the HTTP status given by ``http_status_for``.
"""

from enum import Enum
from typing import Any, Optional

from app.models import ErrorDetail, ErrorResponse


class ErrorCode(str, Enum):
    """Catalog of structured error codes (see design.md).

    Each member documents the situation that produces it and the related
    requirement(s).
    """

    # 존재하지 않는 room id 요청 (Req 8.7)
    ROOM_NOT_FOUND = "ROOM_NOT_FOUND"
    # Closed 방에 메시지/보고서 요청 (Req 6.6)
    ROOM_CLOSED = "ROOM_CLOSED"
    # 공백 전용 메시지 전송 - Backend 방어 (Req 3.3)
    EMPTY_MESSAGE = "EMPTY_MESSAGE"
    # 메시지 없는 방의 보고서 생성 시도 (Req 4.5)
    NO_MESSAGES = "NO_MESSAGES"
    # LLM API 미도달/오류 (Req 5.7, 9.4)
    LLM_UNAVAILABLE = "LLM_UNAVAILABLE"
    # LLM 응답 시간 초과 (Req 5.3, 9.4)
    LLM_TIMEOUT = "LLM_TIMEOUT"
    # 필수 LLM 설정 누락 - 실행 중 감지 (Req 11.9)
    CONFIG_MISSING = "CONFIG_MISSING"
    # 그 외 내부 오류 (Req 8.8)
    INTERNAL_ERROR = "INTERNAL_ERROR"


# Code -> HTTP status mapping, taken verbatim from design.md's catalog table.
ERROR_STATUS_MAP: dict[ErrorCode, int] = {
    ErrorCode.ROOM_NOT_FOUND: 404,
    ErrorCode.ROOM_CLOSED: 409,
    ErrorCode.EMPTY_MESSAGE: 400,
    ErrorCode.NO_MESSAGES: 400,
    ErrorCode.LLM_UNAVAILABLE: 502,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.CONFIG_MISSING: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


def http_status_for(code: ErrorCode) -> int:
    """Return the HTTP status code for a catalog error code.

    Unknown/unmapped codes fall back to 500 so a missing mapping never crashes
    error handling.
    """
    return ERROR_STATUS_MAP.get(code, 500)


def build_error_response(
    code: ErrorCode, message: str, details: Optional[Any] = None
) -> ErrorResponse:
    """Build a structured ErrorResponse (reusing the task 1.2 shared models).

    The returned model serializes to the wire shape
    ``{"error": {"code", "message", "details"}}`` via the camelCase-aliased
    models in ``app.models``.
    """
    return ErrorResponse(
        error=ErrorDetail(code=code.value, message=message, details=details)
    )
