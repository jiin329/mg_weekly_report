"""Integration tests for the FastAPI router / endpoints — task 4.6.

Covers the five REST endpoints (design.md "REST API 인터페이스") and structured
error handling (design.md "Error Handling"):

- POST /rooms                    -> {"room": ChatRoom} (active)
- GET  /rooms                    -> {"rooms": ChatRoom[]}
- GET  /rooms/{roomId}/messages  -> {"messages": Message[]}
- POST /rooms/{roomId}/messages  -> {"message": Message}
- POST /rooms/{roomId}/report    -> HTTP/error wiring (LLM flow deferred to 4.7)

Structured errors:
- invalid roomId          -> 404 ROOM_NOT_FOUND
- message to closed room  -> 409 ROOM_CLOSED
- blank message           -> 400 EMPTY_MESSAGE
- error body shape        -> {"error": {"code", "message", "details"}}

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 6.6
"""

import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from app.api import get_report_service, get_repository
from app.main import app
from app.repository import Repository
from app.schemas import GenerateReportResponse


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
def client(repo):
    """TestClient with an isolated per-test Repository injected via DI override."""
    app.dependency_overrides[get_repository] = lambda: repo
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# POST /rooms
# ---------------------------------------------------------------------------


class TestCreateRoom:
    def test_create_room_returns_active_room(self, client):
        resp = client.post("/rooms")
        assert resp.status_code == 200
        body = resp.json()
        assert "room" in body
        room = body["room"]
        assert room["status"] == "active"
        assert room["report"] is None
        assert room["closedAt"] is None
        assert room["id"]


# ---------------------------------------------------------------------------
# GET /rooms
# ---------------------------------------------------------------------------


class TestListRooms:
    def test_list_rooms_empty(self, client):
        resp = client.get("/rooms")
        assert resp.status_code == 200
        assert resp.json() == {"rooms": []}

    def test_list_rooms_after_create(self, client):
        client.post("/rooms")
        resp = client.get("/rooms")
        assert resp.status_code == 200
        rooms = resp.json()["rooms"]
        assert len(rooms) == 1
        assert rooms[0]["status"] == "active"


# ---------------------------------------------------------------------------
# POST /rooms/{roomId}/messages
# ---------------------------------------------------------------------------


class TestSendMessage:
    def test_send_message_success(self, client):
        room = client.post("/rooms").json()["room"]
        resp = client.post(f"/rooms/{room['id']}/messages", json={"content": "hello"})
        assert resp.status_code == 200
        msg = resp.json()["message"]
        assert msg["content"] == "hello"
        assert msg["roomId"] == room["id"]
        assert msg["sender"] == "user"

    def test_send_blank_message_returns_400_empty_message(self, client):
        room = client.post("/rooms").json()["room"]
        resp = client.post(f"/rooms/{room['id']}/messages", json={"content": "   "})
        assert resp.status_code == 400
        err = resp.json()["error"]
        assert err["code"] == "EMPTY_MESSAGE"
        assert err["message"]

    def test_send_message_invalid_room_returns_404(self, client):
        resp = client.post("/rooms/no-such-id/messages", json={"content": "hi"})
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ROOM_NOT_FOUND"


# ---------------------------------------------------------------------------
# GET /rooms/{roomId}/messages
# ---------------------------------------------------------------------------


class TestGetMessages:
    def test_get_messages_for_valid_room(self, client):
        room = client.post("/rooms").json()["room"]
        client.post(f"/rooms/{room['id']}/messages", json={"content": "one"})
        client.post(f"/rooms/{room['id']}/messages", json={"content": "two"})
        resp = client.get(f"/rooms/{room['id']}/messages")
        assert resp.status_code == 200
        messages = resp.json()["messages"]
        assert [m["content"] for m in messages] == ["one", "two"]

    def test_get_messages_invalid_room_returns_404(self, client):
        resp = client.get("/rooms/no-such-id/messages")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ROOM_NOT_FOUND"


# ---------------------------------------------------------------------------
# POST /rooms/{roomId}/report — HTTP/error wiring only (LLM flow -> 4.7)
# ---------------------------------------------------------------------------


class TestGenerateReport:
    def test_report_invalid_room_returns_404(self, client):
        resp = client.post("/rooms/no-such-id/report")
        assert resp.status_code == 404
        assert resp.json()["error"]["code"] == "ROOM_NOT_FOUND"

    def test_report_success_shape_with_injected_service(self, client, repo):
        """The report endpoint delegates generation to ReportService (task 4.7).

        Here we inject a fake ReportService to verify the HTTP layer binds the
        contract response shape correctly.
        """
        room = client.post("/rooms").json()["room"]

        from app.room_service import RoomService
        from app.models import WeeklyReport

        class FakeReportService:
            def generate_report(self, room_id: str) -> GenerateReportResponse:
                report = WeeklyReport(
                    writtenDate="2024-01-05",
                    achievements="a",
                    nextWeekPlan="b",
                    issues="c",
                )
                result = RoomService(repo).close_room_with_report(room_id, report)
                return GenerateReportResponse(
                    report=report,
                    closedRoomId=result.closed_room.id,
                    newRoom=result.new_room,
                )

        # a message is needed for a legit close
        client.post(f"/rooms/{room['id']}/messages", json={"content": "work done"})
        app.dependency_overrides[get_report_service] = lambda: FakeReportService()

        resp = client.post(f"/rooms/{room['id']}/report")
        assert resp.status_code == 200
        body = resp.json()
        assert body["closedRoomId"] == room["id"]
        assert body["newRoom"]["status"] == "active"
        assert set(body["report"].keys()) == {
            "writtenDate",
            "achievements",
            "nextWeekPlan",
            "issues",
        }


# ---------------------------------------------------------------------------
# Closed-room rejection (Req 6.6) + structured error shape (Req 8.8)
# ---------------------------------------------------------------------------


class TestClosedRoomAndErrorShape:
    def test_send_message_to_closed_room_returns_409(self, client, repo):
        room = client.post("/rooms").json()["room"]
        client.post(f"/rooms/{room['id']}/messages", json={"content": "hi"})

        # Close the room directly through the service layer.
        from app.room_service import RoomService
        from app.models import WeeklyReport

        RoomService(repo).close_room_with_report(
            room["id"],
            WeeklyReport(
                writtenDate="2024-01-05",
                achievements="a",
                nextWeekPlan="b",
                issues="c",
            ),
        )

        resp = client.post(f"/rooms/{room['id']}/messages", json={"content": "again"})
        assert resp.status_code == 409
        assert resp.json()["error"]["code"] == "ROOM_CLOSED"

    def test_error_response_shape(self, client):
        resp = client.get("/rooms/no-such-id/messages")
        body = resp.json()
        assert "error" in body
        assert "code" in body["error"]
        assert "message" in body["error"]
        assert "details" in body["error"]
