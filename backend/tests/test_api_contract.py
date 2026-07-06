"""Contract tests for the REST API request/response shapes (task 1.3).

These verify the shared contract models in `app.schemas` reuse the data models
from `app.models` (task 1.2) and serialize to the exact JSON shapes documented
in design.md "REST API 인터페이스" — including camelCase keys and nested shapes.

Endpoints under contract:
- POST /rooms                          -> {"room": ChatRoom}
- GET  /rooms                          -> {"rooms": ChatRoom[]}
- GET  /rooms/{roomId}/messages        -> {"messages": Message[]}
- POST /rooms/{roomId}/messages  req {"content": str} -> {"message": Message}
- POST /rooms/{roomId}/report          -> {"report": WeeklyReport,
                                            "closedRoomId": str, "newRoom": ChatRoom}
"""

from app.models import ChatRoom, Message, WeeklyReport
from app.schemas import (
    CreateRoomResponse,
    GenerateReportResponse,
    ListMessagesResponse,
    ListRoomsResponse,
    SendMessageRequest,
    SendMessageResponse,
)


def _active_room(room_id: str = "room-1") -> ChatRoom:
    return ChatRoom(id=room_id, status="active", createdAt="2024-01-01T00:00:00Z")


def _closed_room(room_id: str, report: WeeklyReport) -> ChatRoom:
    return ChatRoom(
        id=room_id,
        status="closed",
        createdAt="2024-01-01T00:00:00Z",
        closedAt="2024-01-07T00:00:00Z",
        report=report,
    )


def _report() -> WeeklyReport:
    return WeeklyReport(
        writtenDate="2024-01-07",
        achievements="did work",
        nextWeekPlan="more work",
        issues="none",
    )


def _message(room_id: str = "room-1") -> Message:
    return Message(
        id="msg-1",
        roomId=room_id,
        sender="user",
        content="hello",
        createdAt="2024-01-01T00:01:00Z",
    )


def test_create_room_response_shape():
    resp = CreateRoomResponse(room=_active_room())
    data = resp.model_dump(by_alias=True)
    assert set(data.keys()) == {"room"}
    assert data["room"]["status"] == "active"
    assert data["room"]["createdAt"] == "2024-01-01T00:00:00Z"
    assert data["room"]["closedAt"] is None
    assert data["room"]["report"] is None


def test_list_rooms_response_shape():
    resp = ListRoomsResponse(rooms=[_active_room("a"), _active_room("b")])
    data = resp.model_dump(by_alias=True)
    assert set(data.keys()) == {"rooms"}
    assert [r["id"] for r in data["rooms"]] == ["a", "b"]


def test_list_messages_response_shape():
    resp = ListMessagesResponse(messages=[_message()])
    data = resp.model_dump(by_alias=True)
    assert set(data.keys()) == {"messages"}
    assert data["messages"][0]["roomId"] == "room-1"
    assert data["messages"][0]["createdAt"] == "2024-01-01T00:01:00Z"


def test_send_message_request_parses_content():
    req = SendMessageRequest.model_validate({"content": "hello world"})
    assert req.content == "hello world"


def test_send_message_response_shape():
    resp = SendMessageResponse(message=_message())
    data = resp.model_dump(by_alias=True)
    assert set(data.keys()) == {"message"}
    assert data["message"]["sender"] == "user"


def test_generate_report_response_shape():
    report = _report()
    resp = GenerateReportResponse(
        report=report,
        closedRoomId="room-1",
        newRoom=_active_room("room-2"),
    )
    data = resp.model_dump(by_alias=True)
    assert set(data.keys()) == {"report", "closedRoomId", "newRoom"}
    assert data["closedRoomId"] == "room-1"
    assert data["report"]["nextWeekPlan"] == "more work"
    assert data["newRoom"]["status"] == "active"


def test_closed_room_serializes_report_and_closed_at():
    # Sanity: a closed room in a response carries its report and closedAt.
    room = _closed_room("room-1", _report())
    resp = CreateRoomResponse(room=room)
    data = resp.model_dump(by_alias=True)
    assert data["room"]["closedAt"] == "2024-01-07T00:00:00Z"
    assert data["room"]["report"]["writtenDate"] == "2024-01-07"
