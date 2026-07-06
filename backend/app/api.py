"""FastAPI router, dependency wiring, and structured error handling (task 4.6).

This module implements the HTTP layer for the five REST endpoints defined in
design.md ("REST API 인터페이스") and turns invalid-roomId / internal errors into
the structured error responses from the error catalog (design.md
"Error Handling").

Layering:
- Request/response shapes come from ``app.schemas`` (task 1.3).
- Business logic lives in ``RoomService`` (task 4.4) and ``MessageService``
  (task 4.5). This module only binds HTTP <-> service calls and maps failures
  onto the ``ErrorCode`` catalog (task 1.4).
- Report generation (LLM flow) belongs to ``ReportService`` (task 4.7). This
  module wires the ``POST /rooms/{roomId}/report`` endpoint's HTTP/error layer
  and leaves a clear dependency seam (``get_report_service``) for that task.

Dependencies are provided through FastAPI's dependency-injection system so tests
can override the ``Repository`` (and the report service) with isolated instances
via ``app.dependency_overrides``.

Requirements: 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7, 8.8, 6.6
"""

from typing import Any, Optional, Protocol

from fastapi import APIRouter, Depends

from .error_codes import ErrorCode
from .llm import StubLLMClient
from .message_service import MessageService, MessageServiceError
from .report_service import ReportService, ReportServiceError
from .repository import Repository
from .room_service import RoomService
from .schemas import (
    CreateRoomResponse,
    GenerateReportResponse,
    ListMessagesResponse,
    ListRoomsResponse,
    SendMessageRequest,
    SendMessageResponse,
)


class APIError(Exception):
    """Typed exception carrying a catalog error code for structured responses.

    A single global handler (registered on the app) converts every APIError into
    the wire shape ``{"error": {"code", "message", "details"}}`` with the HTTP
    status mapped from the code (see ``app.error_codes.http_status_for``).
    """

    def __init__(
        self, code: ErrorCode, message: str, details: Optional[Any] = None
    ) -> None:
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


# ---------------------------------------------------------------------------
# Dependency providers
# ---------------------------------------------------------------------------

# A process-wide default Repository. The desktop shell / app startup (and tests)
# override this via ``app.dependency_overrides[get_repository]`` so the storage
# location is controlled from the outside and tests stay isolated.
_default_repository: Optional[Repository] = None


def configure_repository(repo: Repository) -> None:
    """Set the process-wide Repository used by the default dependency provider."""
    global _default_repository
    _default_repository = repo


def get_repository() -> Repository:
    """Provide the Repository. Overridden in tests / configured at startup."""
    if _default_repository is None:
        raise APIError(
            ErrorCode.INTERNAL_ERROR,
            "저장소가 초기화되지 않았습니다.",
        )
    return _default_repository


def get_room_service(repo: Repository = Depends(get_repository)) -> RoomService:
    """Provide a RoomService bound to the active Repository."""
    return RoomService(repo)


def get_message_service(repo: Repository = Depends(get_repository)) -> MessageService:
    """Provide a MessageService bound to the active Repository."""
    return MessageService(repo)


class ReportServiceProtocol(Protocol):
    """Interface the report endpoint depends on (implemented by task 4.7)."""

    def generate_report(self, room_id: str) -> GenerateReportResponse:
        ...


def get_report_service(
    repo: Repository = Depends(get_repository),
) -> ReportServiceProtocol:
    """Provide a ReportService (task 4.7) bound to the active Repository.

    Report generation (message aggregation -> LLM -> WeeklyReport -> atomic room
    close + new room) runs against the shared ``StubLLMClient`` (task 1.5), so
    the BE track stays independent of the real LLM track. The real ``LLMClient``
    is swapped in at integration (task 8.1). Tests may still override this
    provider to inject a fake service or configure the stub for error paths.
    """
    return ReportService(repo, StubLLMClient())


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter()


@router.post("/rooms", response_model=CreateRoomResponse)
def create_room(
    room_service: RoomService = Depends(get_room_service),
) -> CreateRoomResponse:
    """Create a new active Chat_Room (Requirements 1.3, 8.2)."""
    room = room_service.create_room()
    return CreateRoomResponse(room=room)


@router.get("/rooms", response_model=ListRoomsResponse)
def list_rooms(
    room_service: RoomService = Depends(get_room_service),
) -> ListRoomsResponse:
    """List all rooms, active and closed (Requirements 7.1, 8.6)."""
    return ListRoomsResponse(rooms=room_service.list_rooms())


@router.get("/rooms/{room_id}/messages", response_model=ListMessagesResponse)
def get_messages(
    room_id: str,
    message_service: MessageService = Depends(get_message_service),
) -> ListMessagesResponse:
    """Get a room's messages in chronological order (Requirement 8.4).

    Invalid roomId -> 404 ROOM_NOT_FOUND (Requirement 8.7).
    """
    messages = _call_message_service(message_service.get_messages, room_id)
    return ListMessagesResponse(messages=messages)


@router.post("/rooms/{room_id}/messages", response_model=SendMessageResponse)
def send_message(
    room_id: str,
    body: SendMessageRequest,
    message_service: MessageService = Depends(get_message_service),
) -> SendMessageResponse:
    """Send a user message to a room (Requirements 3.1, 3.5, 8.3).

    Blank content -> 400 EMPTY_MESSAGE; closed room -> 409 ROOM_CLOSED
    (Requirement 6.6); invalid roomId -> 404 ROOM_NOT_FOUND (Requirement 8.7).
    """
    message = _call_message_service(
        message_service.send_message, room_id, body.content
    )
    return SendMessageResponse(message=message)


@router.post("/rooms/{room_id}/report", response_model=GenerateReportResponse)
def generate_report(
    room_id: str,
    report_service: ReportServiceProtocol = Depends(get_report_service),
) -> GenerateReportResponse:
    """Request weekly-report generation for a room (task 4.7).

    Delegates to ReportService, which aggregates the room's messages, calls the
    LLM interface, and — on success — atomically closes the room and creates a
    new active room (Requirements 4.2, 5.3, 6.1-6.3, 8.5). Structured failures
    (ROOM_NOT_FOUND, ROOM_CLOSED, NO_MESSAGES, LLM_UNAVAILABLE, LLM_TIMEOUT) are
    mapped onto the error catalog (Requirements 5.7, 8.7, 9.4).
    """
    try:
        return report_service.generate_report(room_id)
    except ReportServiceError as exc:
        raise APIError(exc.code, exc.message) from exc


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _call_message_service(func, *args):
    """Call a MessageService method, mapping MessageServiceError -> APIError.

    MessageService raises ``MessageServiceError`` with a catalog code string;
    this translates it into the typed ``APIError`` the global handler renders.
    """
    try:
        return func(*args)
    except MessageServiceError as exc:
        raise APIError(ErrorCode(exc.code), exc.message) from exc
