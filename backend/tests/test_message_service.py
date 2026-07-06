"""Tests for MessageService — task 4.5.

Verifies:
- Sending a valid message stores it and returns the Message model
- Messages are retrieved in chronological order
- Blank/whitespace-only messages are rejected (EMPTY_MESSAGE)
- Sending a message to a closed room is rejected (ROOM_CLOSED)
- Sending a message to a non-existent room is rejected (ROOM_NOT_FOUND)

Requirements: 3.1, 3.2, 3.4, 3.5, 6.6
Dependencies: Repository (4.2), Models (4.3)
"""

import os
import tempfile

import pytest

from app.models import WeeklyReport
from app.repository import Repository
from app.room_service import RoomService
from app.message_service import MessageService, MessageServiceError


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def repo(db_path):
    return Repository(db_path)


@pytest.fixture
def room_service(repo):
    return RoomService(repo)


@pytest.fixture
def service(repo):
    return MessageService(repo)


@pytest.fixture
def active_room(room_service):
    return room_service.create_room()


@pytest.fixture
def closed_room(room_service, repo):
    room = room_service.create_room()
    repo.add_message(
        id="seed-msg", room_id=room.id, sender="user",
        content="seed", created_at="2024-01-01T00:00:00Z",
    )
    report = WeeklyReport(
        writtenDate="2024-01-05",
        achievements="Done",
        nextWeekPlan="Plan",
        issues="None",
    )
    result = room_service.close_room_with_report(room.id, report)
    return result.closed_room


class TestSendMessage:
    def test_send_valid_message_returns_message(self, service, active_room):
        msg = service.send_message(active_room.id, "Hello world")
        assert msg.roomId == active_room.id
        assert msg.sender == "user"
        assert msg.content == "Hello world"
        assert msg.id
        assert msg.createdAt

    def test_send_message_persists(self, service, active_room):
        service.send_message(active_room.id, "First")
        service.send_message(active_room.id, "Second")
        messages = service.get_messages(active_room.id)
        assert len(messages) == 2

    def test_send_message_preserves_content(self, service, active_room):
        msg = service.send_message(active_room.id, "  padded content  ")
        # content is stored as-is (not trimmed); validation only checks non-blank
        assert msg.content == "  padded content  "


class TestGetMessages:
    def test_get_messages_chronological_order(self, service, active_room):
        service.send_message(active_room.id, "First")
        service.send_message(active_room.id, "Second")
        service.send_message(active_room.id, "Third")
        messages = service.get_messages(active_room.id)
        assert messages[0].content == "First"
        assert messages[1].content == "Second"
        assert messages[2].content == "Third"
        # Verify timestamps are non-decreasing
        for i in range(len(messages) - 1):
            assert messages[i].createdAt <= messages[i + 1].createdAt

    def test_get_messages_empty_room(self, service, active_room):
        messages = service.get_messages(active_room.id)
        assert messages == []


class TestBlankMessageRejection:
    def test_empty_string_rejected(self, service, active_room):
        with pytest.raises(MessageServiceError) as exc_info:
            service.send_message(active_room.id, "")
        assert exc_info.value.code == "EMPTY_MESSAGE"

    def test_whitespace_only_rejected(self, service, active_room):
        with pytest.raises(MessageServiceError) as exc_info:
            service.send_message(active_room.id, "   \t\n  ")
        assert exc_info.value.code == "EMPTY_MESSAGE"


class TestClosedRoomRejection:
    def test_send_to_closed_room_rejected(self, service, closed_room):
        with pytest.raises(MessageServiceError) as exc_info:
            service.send_message(closed_room.id, "should fail")
        assert exc_info.value.code == "ROOM_CLOSED"


class TestRoomNotFound:
    def test_send_to_nonexistent_room_rejected(self, service):
        with pytest.raises(MessageServiceError) as exc_info:
            service.send_message("nonexistent-id", "should fail")
        assert exc_info.value.code == "ROOM_NOT_FOUND"

    def test_get_messages_nonexistent_room_rejected(self, service):
        with pytest.raises(MessageServiceError) as exc_info:
            service.get_messages("nonexistent-id")
        assert exc_info.value.code == "ROOM_NOT_FOUND"
