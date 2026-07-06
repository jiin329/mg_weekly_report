"""Tests for Pydantic model invariants (task 4.3).

These tests verify the data-model invariants specific to task 4.3:
- ChatRoom: status↔report/closedAt lifecycle consistency
- Message: user message content must not be blank (Requirement 3.3)
- WeeklyReport: all four sections are required (Requirement 5.2)

TDD Red phase: write failing tests for any gaps, then implement to pass.
"""

import pytest
from pydantic import ValidationError

from app.models import ChatRoom, Message, WeeklyReport


# --- Message invariant: user content not blank (Req 3.3) ---


class TestUserMessageBlankRejection:
    """Property 6: 공백 전용 메시지는 거부된다."""

    def test_empty_string_rejected(self):
        with pytest.raises(ValidationError):
            Message(
                id="m1", roomId="r1", sender="user", content="", createdAt="2024-01-05T10:00:00Z"
            )

    def test_spaces_only_rejected(self):
        with pytest.raises(ValidationError):
            Message(
                id="m1", roomId="r1", sender="user", content="     ", createdAt="2024-01-05T10:00:00Z"
            )

    def test_tabs_and_newlines_only_rejected(self):
        with pytest.raises(ValidationError):
            Message(
                id="m1", roomId="r1", sender="user", content="\t\n\r\n", createdAt="2024-01-05T10:00:00Z"
            )

    def test_valid_content_accepted(self):
        msg = Message(
            id="m1", roomId="r1", sender="user", content="hello", createdAt="2024-01-05T10:00:00Z"
        )
        assert msg.content == "hello"

    def test_content_with_leading_trailing_spaces_accepted(self):
        """Content with some whitespace around valid text is allowed."""
        msg = Message(
            id="m1", roomId="r1", sender="user", content="  hello  ", createdAt="2024-01-05T10:00:00Z"
        )
        assert msg.content == "  hello  "

    def test_system_message_allows_any_content(self):
        """System messages (e.g. reports) are exempt from blank check."""
        msg = Message(
            id="m1", roomId="r1", sender="system", content="", createdAt="2024-01-05T10:00:00Z"
        )
        assert msg.content == ""


# --- ChatRoom invariant: status↔report/closedAt (Req 1.3) ---


class TestChatRoomLifecycleInvariant:
    """Closed room requires report+closedAt; active room forbids them."""

    def test_active_room_cannot_have_report(self):
        with pytest.raises(ValidationError, match="active room must have report and closedAt set to None"):
            ChatRoom(
                id="r1",
                status="active",
                createdAt="2024-01-05T10:00:00Z",
                closedAt=None,
                report=WeeklyReport(writtenDate="2024-01-05", achievements="A", nextWeekPlan="B", issues="C"),
            )

    def test_active_room_cannot_have_closedAt(self):
        with pytest.raises(ValidationError, match="active room must have report and closedAt set to None"):
            ChatRoom(
                id="r1",
                status="active",
                createdAt="2024-01-05T10:00:00Z",
                closedAt="2024-01-05T12:00:00Z",
                report=None,
            )

    def test_closed_room_must_have_report(self):
        with pytest.raises(ValidationError, match="closed room requires both report and closedAt"):
            ChatRoom(
                id="r1",
                status="closed",
                createdAt="2024-01-05T10:00:00Z",
                closedAt="2024-01-05T12:00:00Z",
                report=None,
            )

    def test_closed_room_must_have_closedAt(self):
        with pytest.raises(ValidationError, match="closed room requires both report and closedAt"):
            ChatRoom(
                id="r1",
                status="closed",
                createdAt="2024-01-05T10:00:00Z",
                closedAt=None,
                report=WeeklyReport(writtenDate="2024-01-05", achievements="A", nextWeekPlan="B", issues="C"),
            )

    def test_valid_active_room(self):
        room = ChatRoom(id="r1", status="active", createdAt="2024-01-05T10:00:00Z")
        assert room.status == "active"
        assert room.report is None
        assert room.closedAt is None

    def test_valid_closed_room(self):
        room = ChatRoom(
            id="r1",
            status="closed",
            createdAt="2024-01-05T10:00:00Z",
            closedAt="2024-01-05T12:00:00Z",
            report=WeeklyReport(writtenDate="2024-01-05", achievements="A", nextWeekPlan="B", issues="C"),
        )
        assert room.status == "closed"
        assert room.report is not None
        assert room.closedAt is not None


# --- WeeklyReport invariant: all four sections (Req 5.2) ---


class TestWeeklyReportSections:
    """All four sections must be present."""

    def test_missing_writtenDate(self):
        with pytest.raises(ValidationError):
            WeeklyReport(achievements="A", nextWeekPlan="B", issues="C")  # type: ignore[call-arg]

    def test_missing_achievements(self):
        with pytest.raises(ValidationError):
            WeeklyReport(writtenDate="2024-01-05", nextWeekPlan="B", issues="C")  # type: ignore[call-arg]

    def test_missing_nextWeekPlan(self):
        with pytest.raises(ValidationError):
            WeeklyReport(writtenDate="2024-01-05", achievements="A", issues="C")  # type: ignore[call-arg]

    def test_missing_issues(self):
        with pytest.raises(ValidationError):
            WeeklyReport(writtenDate="2024-01-05", achievements="A", nextWeekPlan="B")  # type: ignore[call-arg]

    def test_all_sections_present(self):
        report = WeeklyReport(writtenDate="2024-01-05", achievements="A", nextWeekPlan="B", issues="C")
        assert report.writtenDate == "2024-01-05"
        assert report.achievements == "A"
        assert report.nextWeekPlan == "B"
        assert report.issues == "C"
