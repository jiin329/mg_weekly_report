"""Tests for the shared error-code catalog (task 1.4).

Verifies each catalog code maps to the HTTP status defined in design.md's
"오류 코드 카탈로그" and that the ErrorResponse builder produces the shared
structure from app.models.
"""

import pytest

from app.error_codes import (
    ERROR_STATUS_MAP,
    ErrorCode,
    build_error_response,
    http_status_for,
)
from app.models import ErrorResponse

# Expected code -> HTTP status mapping straight from design.md.
EXPECTED = {
    ErrorCode.ROOM_NOT_FOUND: 404,
    ErrorCode.ROOM_CLOSED: 409,
    ErrorCode.EMPTY_MESSAGE: 400,
    ErrorCode.NO_MESSAGES: 400,
    ErrorCode.LLM_UNAVAILABLE: 502,
    ErrorCode.LLM_TIMEOUT: 504,
    ErrorCode.CONFIG_MISSING: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}


def test_catalog_contains_exactly_the_expected_codes():
    assert {code.value for code in ErrorCode} == {
        "ROOM_NOT_FOUND",
        "ROOM_CLOSED",
        "EMPTY_MESSAGE",
        "NO_MESSAGES",
        "LLM_UNAVAILABLE",
        "LLM_TIMEOUT",
        "CONFIG_MISSING",
        "INTERNAL_ERROR",
    }


@pytest.mark.parametrize("code,status", list(EXPECTED.items()))
def test_each_code_maps_to_expected_http_status(code, status):
    assert http_status_for(code) == status
    assert ERROR_STATUS_MAP[code] == status


def test_status_map_covers_every_code():
    for code in ErrorCode:
        assert code in ERROR_STATUS_MAP


def test_build_error_response_produces_shared_structure():
    resp = build_error_response(ErrorCode.ROOM_NOT_FOUND, "no room")
    assert isinstance(resp, ErrorResponse)
    assert resp.error.code == "ROOM_NOT_FOUND"
    assert resp.error.message == "no room"
    assert resp.error.details is None


def test_build_error_response_accepts_details():
    resp = build_error_response(
        ErrorCode.EMPTY_MESSAGE, "blank", details={"field": "content"}
    )
    assert resp.error.details == {"field": "content"}
    # camelCase wire serialization is inherited from app.models.
    assert resp.model_dump(by_alias=True) == {
        "error": {
            "code": "EMPTY_MESSAGE",
            "message": "blank",
            "details": {"field": "content"},
        }
    }
