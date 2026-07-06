"""Tests for RoomService (room lifecycle) — task 4.4.

Verifies:
- Room creation returns a valid active room
- Get room by id / not found
- List rooms
- Active room uniqueness invariant (at most 1 active)
- Atomic report generation: close room + create new active room
- Closed room cannot be closed again

Requirements: 1.3, 6.1, 6.3, 7.1, 8.2, 8.6
"""

import os
import tempfile

import pytest

from app.models import WeeklyReport
from app.repository import Repository
from app.room_service import RoomService


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
    r = Repository(db_path)
    yield r
    r.close()


@pytest.fixture
def service(repo):
    return RoomService(repo)


class TestCreateRoom:
    def test_create_room_returns_active_chatroom(self, service):
        room = service.create_room()
        assert room.status == "active"
        assert room.report is None
        assert room.closedAt is None
        assert room.id

    def test_create_room_enforces_single_active(self, service):
        """Creating a room when one already exists should still yield exactly 1 active."""
        room1 = service.create_room()
        room2 = service.create_room()
        # Only the latest should be active
        rooms = service.list_rooms()
        active_rooms = [r for r in rooms if r.status == "active"]
        assert len(active_rooms) == 1
        assert active_rooms[0].id == room2.id


class TestGetRoom:
    def test_get_existing_room(self, service):
        room = service.create_room()
        fetched = service.get_room(room.id)
        assert fetched is not None
        assert fetched.id == room.id

    def test_get_nonexistent_room_returns_none(self, service):
        result = service.get_room("no-such-id")
        assert result is None


class TestListRooms:
    def test_list_rooms_returns_all(self, service):
        service.create_room()
        rooms = service.list_rooms()
        assert len(rooms) >= 1

    def test_list_rooms_empty_initially(self, service):
        rooms = service.list_rooms()
        assert rooms == []


class TestCloseRoomWithReport:
    def test_close_room_transitions_to_closed(self, service):
        room = service.create_room()
        # Add a message so close is valid
        service._repo.add_message(
            id="m1", room_id=room.id, sender="user",
            content="test msg", created_at="2024-01-01T00:00:00Z",
        )
        report = WeeklyReport(
            writtenDate="2024-01-05",
            achievements="Done stuff",
            nextWeekPlan="Plan more",
            issues="None",
        )
        result = service.close_room_with_report(room.id, report)
        assert result.closed_room.status == "closed"
        assert result.closed_room.report is not None
        assert result.closed_room.closedAt is not None

    def test_close_room_creates_new_active_room(self, service):
        room = service.create_room()
        service._repo.add_message(
            id="m1", room_id=room.id, sender="user",
            content="test msg", created_at="2024-01-01T00:00:00Z",
        )
        report = WeeklyReport(
            writtenDate="2024-01-05",
            achievements="Done stuff",
            nextWeekPlan="Plan more",
            issues="None",
        )
        result = service.close_room_with_report(room.id, report)
        assert result.new_room.status == "active"
        assert result.new_room.id != room.id

    def test_close_room_preserves_single_active_invariant(self, service):
        room = service.create_room()
        service._repo.add_message(
            id="m1", room_id=room.id, sender="user",
            content="test msg", created_at="2024-01-01T00:00:00Z",
        )
        report = WeeklyReport(
            writtenDate="2024-01-05",
            achievements="Done stuff",
            nextWeekPlan="Plan more",
            issues="None",
        )
        service.close_room_with_report(room.id, report)
        rooms = service.list_rooms()
        active_rooms = [r for r in rooms if r.status == "active"]
        assert len(active_rooms) == 1

    def test_close_nonexistent_room_raises(self, service):
        report = WeeklyReport(
            writtenDate="2024-01-05",
            achievements="X",
            nextWeekPlan="Y",
            issues="Z",
        )
        with pytest.raises(ValueError, match="not found"):
            service.close_room_with_report("bad-id", report)

    def test_close_already_closed_room_raises(self, service):
        room = service.create_room()
        service._repo.add_message(
            id="m1", room_id=room.id, sender="user",
            content="msg", created_at="2024-01-01T00:00:00Z",
        )
        report = WeeklyReport(
            writtenDate="2024-01-05",
            achievements="X",
            nextWeekPlan="Y",
            issues="Z",
        )
        service.close_room_with_report(room.id, report)
        with pytest.raises(ValueError, match="closed"):
            service.close_room_with_report(room.id, report)
