"""Tests for the shared Pydantic data models (task 1.2).

These assert the data-model invariants documented in design.md "Data Models"
and that valid instances construct correctly. The wire contract (JSON field
names) must match the TypeScript definitions in frontend/src/types, so we also
check camelCase serialization.
"""

import pytest
from pydantic import ValidationError

from app.models import (
    AppConfig,
    ChatRoom,
    ErrorDetail,
    ErrorResponse,
    Message,
    WeeklyReport,
)


def _report() -> WeeklyReport:
    return WeeklyReport(
        writtenDate="2024-01-05",
        achievements="A",
        nextWeekPlan="B",
        issues="C",
    )


# --- WeeklyReport ---------------------------------------------------------


def test_weekly_report_requires_all_four_sections():
    with pytest.raises(ValidationError):
        WeeklyReport(writtenDate="2024-01-05", achievements="A", nextWeekPlan="B")


def test_weekly_report_valid_construction():
    report = _report()
    assert report.writtenDate == "2024-01-05"
    assert report.issues == "C"


# --- Message --------------------------------------------------------------


def test_user_message_valid_construction():
    msg = Message(
        id="m1",
        roomId="r1",
        sender="user",
        content="worked on the API",
        createdAt="2024-01-05T10:00:00Z",
    )
    assert msg.sender == "user"


def test_user_message_blank_content_rejected():
    with pytest.raises(ValidationError):
        Message(
            id="m1",
            roomId="r1",
            sender="user",
            content="   \n\t  ",
            createdAt="2024-01-05T10:00:00Z",
        )


def test_message_serializes_with_camelcase_keys():
    msg = Message(
        id="m1",
        roomId="r1",
        sender="user",
        content="hi",
        createdAt="2024-01-05T10:00:00Z",
    )
    data = msg.model_dump(by_alias=True)
    assert "roomId" in data
    assert "createdAt" in data


# --- ChatRoom -------------------------------------------------------------


def test_active_room_valid_construction():
    room = ChatRoom(
        id="r1",
        status="active",
        createdAt="2024-01-05T10:00:00Z",
        closedAt=None,
        report=None,
    )
    assert room.status == "active"
    assert room.report is None


def test_closed_room_valid_construction():
    room = ChatRoom(
        id="r1",
        status="closed",
        createdAt="2024-01-05T10:00:00Z",
        closedAt="2024-01-05T12:00:00Z",
        report=_report(),
    )
    assert room.status == "closed"
    assert room.report is not None


def test_active_room_with_report_rejected():
    with pytest.raises(ValidationError):
        ChatRoom(
            id="r1",
            status="active",
            createdAt="2024-01-05T10:00:00Z",
            closedAt=None,
            report=_report(),
        )


def test_active_room_with_closed_at_rejected():
    with pytest.raises(ValidationError):
        ChatRoom(
            id="r1",
            status="active",
            createdAt="2024-01-05T10:00:00Z",
            closedAt="2024-01-05T12:00:00Z",
            report=None,
        )


def test_closed_room_without_report_rejected():
    with pytest.raises(ValidationError):
        ChatRoom(
            id="r1",
            status="closed",
            createdAt="2024-01-05T10:00:00Z",
            closedAt="2024-01-05T12:00:00Z",
            report=None,
        )


def test_closed_room_without_closed_at_rejected():
    with pytest.raises(ValidationError):
        ChatRoom(
            id="r1",
            status="closed",
            createdAt="2024-01-05T10:00:00Z",
            closedAt=None,
            report=_report(),
        )


def test_chatroom_serializes_report_with_camelcase_keys():
    room = ChatRoom(
        id="r1",
        status="closed",
        createdAt="2024-01-05T10:00:00Z",
        closedAt="2024-01-05T12:00:00Z",
        report=_report(),
    )
    data = room.model_dump(by_alias=True)
    assert "closedAt" in data
    assert "writtenDate" in data["report"]
    assert "nextWeekPlan" in data["report"]


# --- ErrorResponse --------------------------------------------------------


def test_error_response_construction():
    err = ErrorResponse(error=ErrorDetail(code="ROOM_NOT_FOUND", message="not found"))
    assert err.error.code == "ROOM_NOT_FOUND"
    assert err.error.details is None


# --- AppConfig ------------------------------------------------------------


def test_app_config_construction():
    cfg = AppConfig(
        llmApiKey="key",
        llmEndpoint="https://llm.example",
        backendPort=8756,
    )
    assert cfg.backendPort == 8756
