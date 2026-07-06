"""REST API request/response contract models (task 1.3).

This module fixes the SHARED request/response shapes for the five REST endpoints
described in design.md "REST API 인터페이스". It is the backend counterpart of the
TypeScript contract in `frontend/src/types/api.ts`; both sides must stay in sync.

These models only wrap the shared data models from `app.models` (task 1.2) —
they do NOT redefine ChatRoom / Message / WeeklyReport. They also inherit the
camelCase alias behaviour from `_CamelModel`, so a response serialized with
`by_alias=True` matches the wire JSON the frontend expects. Implementing the
FastAPI endpoints themselves is task 4.6; this module is contract only.

Endpoints (base path http://127.0.0.1:{PORT}):

    | Method & Path                 | Request          | Response                                      | Req
    | ----------------------------- | ---------------- | --------------------------------------------- | -------------
    | POST /rooms                   | (none)           | {"room": ChatRoom}                            | 1.3, 8.2
    | GET  /rooms                   | (none)           | {"rooms": ChatRoom[]}                         | 7.1, 8.6
    | GET  /rooms/{roomId}/messages | (none)           | {"messages": Message[]}                       | 8.4
    | POST /rooms/{roomId}/messages | {"content": str} | {"message": Message}                          | 3.1, 3.5, 8.3
    | POST /rooms/{roomId}/report   | (none)           | {"report": WeeklyReport,                      | 4.2, 5.3,
    |                               |                  |  "closedRoomId": str, "newRoom": ChatRoom}    | 6.1-6.3, 8.5

Behavioral rules that endpoint implementations (tasks 4.5/4.6/4.7) MUST enforce.
They are documented here because they are part of the API contract even though
this module only fixes the data shapes:

- Closed room rejects messages: POST /rooms/{roomId}/messages against a room
  whose status == "closed" MUST fail with a structured error (code ROOM_CLOSED)
  and MUST NOT modify the room (Requirements 6.6, 6.2). The frontend also
  disables input for closed rooms, but the backend defends against it too.
- Room with no messages rejects report generation: POST /rooms/{roomId}/report
  against a room with zero user messages MUST fail with a structured error
  (code NO_MESSAGES). The frontend blocks this preemptively (Requirement 4.5),
  and the backend defends against it as well.
- Report generation is atomic: on success POST /rooms/{roomId}/report performs,
  as a single logical transaction, (a) produce the WeeklyReport, (b) close the
  target room (status -> "closed", set report + closedAt), and (c) create a new
  active room. If any step fails, no state change is committed, preserving the
  invariant that exactly one active room exists (Requirements 6.1, 6.3). The
  response returns the produced report, the id of the now-closed room
  (closedRoomId), and the newly created active room (newRoom).
- Invalid roomId (any path with {roomId}) MUST return a structured error
  (code ROOM_NOT_FOUND) (Requirement 8.7).

Every failing request returns the structured ErrorResponse from `app.models`
(see design.md "Error Handling"). The error-code catalog itself is owned by a
separate task; error codes are referenced here by name only.
"""

from typing import List

from .models import ChatRoom, Message, WeeklyReport, _CamelModel


class CreateRoomResponse(_CamelModel):
    """Response for POST /rooms — the newly created active ChatRoom.

    Requirements: 1.3, 8.2. The returned room always satisfies the active-room
    invariant (status == "active", report is None, closedAt is None); enforcing
    that is RoomService's job (task 4.4).
    """

    room: ChatRoom


class ListRoomsResponse(_CamelModel):
    """Response for GET /rooms — all rooms (active and closed).

    Requirements: 7.1, 8.6.
    """

    rooms: List[ChatRoom]


class ListMessagesResponse(_CamelModel):
    """Response for GET /rooms/{roomId}/messages — messages in chronological order.

    Requirement 8.4. Ordering (createdAt ascending) is guaranteed by the storage
    /service layer (tasks 4.2/4.5).
    """

    messages: List[Message]


class SendMessageRequest(_CamelModel):
    """Request body for POST /rooms/{roomId}/messages.

    Requirements: 3.1, 3.5. `content` must be non-blank after trimming for a user
    message; blank content is rejected (code EMPTY_MESSAGE) by MessageService
    (task 4.5), and a closed target room is rejected (code ROOM_CLOSED, Req 6.6).
    """

    content: str


class SendMessageResponse(_CamelModel):
    """Response for POST /rooms/{roomId}/messages — the stored message.

    Requirements: 3.1, 8.3.
    """

    message: Message


class GenerateReportResponse(_CamelModel):
    """Response for POST /rooms/{roomId}/report.

    Requirements: 4.2, 5.3, 6.1, 6.3, 8.5. On success the report is produced, the
    target room is atomically closed, and a new active room is created. The
    response carries all three results:
    - report:       the produced WeeklyReport (four sections guaranteed)
    - closedRoomId: id of the room that was just closed
    - newRoom:      the newly created active room
    """

    report: WeeklyReport
    closedRoomId: str
    newRoom: ChatRoom
