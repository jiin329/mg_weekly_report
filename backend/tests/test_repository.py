"""Tests for the Repository (local persistent storage) layer — task 4.2.

Verifies:
- Room CRUD (create, get by id, list all)
- Message storage and chronological retrieval
- Report persistence via room closure
- Data survives across repository instances (simulating restart)

Requirements: 3.4 (chronological messages), 8.4 (retrieve messages).
"""

import os
import tempfile

import pytest

from app.repository import Repository


@pytest.fixture
def db_path():
    """Provide a temp file path for the SQLite database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)  # repository creates the file
    yield path
    if os.path.exists(path):
        os.unlink(path)


@pytest.fixture
def repo(db_path):
    """Create a fresh repository instance."""
    return Repository(db_path)


class TestRoomOperations:
    def test_create_room_returns_active_room(self, repo):
        room = repo.create_room()
        assert room["status"] == "active"
        assert room["closed_at"] is None
        assert room["report"] is None
        assert room["id"]
        assert room["created_at"]

    def test_get_room_by_id(self, repo):
        room = repo.create_room()
        fetched = repo.get_room(room["id"])
        assert fetched is not None
        assert fetched["id"] == room["id"]

    def test_get_room_not_found_returns_none(self, repo):
        assert repo.get_room("nonexistent-id") is None

    def test_list_rooms_returns_all(self, repo):
        repo.create_room()
        repo.create_room()
        rooms = repo.list_rooms()
        assert len(rooms) == 2

    def test_close_room(self, repo):
        room = repo.create_room()
        report_data = {
            "written_date": "2024-01-05",
            "achievements": "Did stuff",
            "next_week_plan": "Plan stuff",
            "issues": "No issues",
        }
        repo.close_room(room["id"], closed_at="2024-01-05T12:00:00Z", report=report_data)
        closed = repo.get_room(room["id"])
        assert closed["status"] == "closed"
        assert closed["closed_at"] == "2024-01-05T12:00:00Z"
        assert closed["report"] == report_data


class TestMessageOperations:
    def test_add_and_get_messages(self, repo):
        room = repo.create_room()
        repo.add_message(
            id="m1",
            room_id=room["id"],
            sender="user",
            content="Hello",
            created_at="2024-01-05T10:00:00Z",
        )
        messages = repo.get_messages(room["id"])
        assert len(messages) == 1
        assert messages[0]["content"] == "Hello"
        assert messages[0]["sender"] == "user"

    def test_messages_returned_in_chronological_order(self, repo):
        room = repo.create_room()
        repo.add_message(
            id="m1",
            room_id=room["id"],
            sender="user",
            content="First",
            created_at="2024-01-05T10:00:00Z",
        )
        repo.add_message(
            id="m2",
            room_id=room["id"],
            sender="user",
            content="Second",
            created_at="2024-01-05T11:00:00Z",
        )
        repo.add_message(
            id="m3",
            room_id=room["id"],
            sender="user",
            content="Third",
            created_at="2024-01-05T09:00:00Z",
        )
        messages = repo.get_messages(room["id"])
        timestamps = [m["created_at"] for m in messages]
        assert timestamps == sorted(timestamps)

    def test_messages_scoped_to_room(self, repo):
        room1 = repo.create_room()
        room2 = repo.create_room()
        repo.add_message(
            id="m1", room_id=room1["id"], sender="user",
            content="Room1 msg", created_at="2024-01-05T10:00:00Z",
        )
        repo.add_message(
            id="m2", room_id=room2["id"], sender="user",
            content="Room2 msg", created_at="2024-01-05T10:00:00Z",
        )
        assert len(repo.get_messages(room1["id"])) == 1
        assert len(repo.get_messages(room2["id"])) == 1


class TestPersistence:
    def test_data_survives_restart(self, db_path):
        """Simulate app restart by creating a new Repository instance."""
        repo1 = Repository(db_path)
        room = repo1.create_room()
        repo1.add_message(
            id="m1",
            room_id=room["id"],
            sender="user",
            content="Persistent",
            created_at="2024-01-05T10:00:00Z",
        )

        # New instance — simulates restart
        repo2 = Repository(db_path)
        rooms = repo2.list_rooms()
        assert len(rooms) == 1
        assert rooms[0]["id"] == room["id"]

        messages = repo2.get_messages(room["id"])
        assert len(messages) == 1
        assert messages[0]["content"] == "Persistent"
