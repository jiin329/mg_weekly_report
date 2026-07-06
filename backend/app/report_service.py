"""ReportService — weekly-report generation flow (task 4.7).

Responsibilities:
- Aggregate a room's user messages, call the LLM interface (task 1.5), and
  accept the response as a ``WeeklyReport``.
- Reject report generation for a room with no user messages (``NO_MESSAGES``),
  a closed room (``ROOM_CLOSED``), or a non-existent room (``ROOM_NOT_FOUND``).
- On LLM failure, keep the room Active with no partial transition and surface a
  structured error (``LLM_UNAVAILABLE`` / ``LLM_TIMEOUT``).
- On success, atomically close the room and create a new active room via
  ``RoomService.close_room_with_report`` (Requirements 6.1, 6.3, 8.5).

The service depends only on the shared ``LLMClient`` interface (task 1.5), so it
develops against ``StubLLMClient`` and is unaffected by the real LLM track; the
real client is swapped in at integration (task 8.1).

Requirements: 4.2, 4.3, 5.3, 5.7, 6.1, 9.4
Dependencies: Repository (4.2), RoomService (4.4), MessageService (4.5),
              LLM interface/stub (1.5)
"""

from .error_codes import ErrorCode
from .llm import DEFAULT_REPORT_TEMPLATE, LLMClient, LLMError, ReportTemplate
from .message_service import MessageService
from .repository import Repository
from .room_service import RoomService
from .schemas import GenerateReportResponse


class ReportServiceError(Exception):
    """Structured error raised by ReportService operations.

    Carries an ``ErrorCode`` from the shared catalog so the HTTP layer (task 4.6)
    can render it as a structured error response.
    """

    def __init__(self, code: ErrorCode, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class ReportService:
    """Generates a WeeklyReport for a room via the LLM interface."""

    def __init__(
        self,
        repo: Repository,
        llm_client: LLMClient,
        template: ReportTemplate = DEFAULT_REPORT_TEMPLATE,
    ) -> None:
        self._repo = repo
        self._llm = llm_client
        self._template = template
        self._room_service = RoomService(repo)
        self._message_service = MessageService(repo)

    def generate_report(self, room_id: str) -> GenerateReportResponse:
        """Generate a report for a room and atomically close it.

        Raises ReportServiceError with:
        - ROOM_NOT_FOUND if the room does not exist
        - ROOM_CLOSED if the room is already closed
        - NO_MESSAGES if the room has no user messages
        - LLM_UNAVAILABLE / LLM_TIMEOUT if the LLM call fails (room stays active)
        """
        room = self._repo.get_room(room_id)
        if room is None:
            raise ReportServiceError(
                ErrorCode.ROOM_NOT_FOUND,
                f"채팅방을 찾을 수 없습니다: {room_id}",
            )
        if room["status"] == "closed":
            raise ReportServiceError(
                ErrorCode.ROOM_CLOSED,
                "종료된 채팅방에서는 보고서를 생성할 수 없습니다.",
            )

        # Aggregate the room's user messages (Requirement 4.3).
        messages = self._message_service.get_messages(room_id)
        user_messages = [m for m in messages if m.sender == "user"]
        if not user_messages:
            raise ReportServiceError(
                ErrorCode.NO_MESSAGES,
                "보고서를 생성하려면 메시지가 필요합니다.",
            )

        # Call the LLM interface. On failure keep the room Active with no partial
        # transition and surface the matching structured error (Req 5.7, 9.4).
        try:
            report = self._llm.generate(user_messages, self._template)
        except LLMError as exc:
            raise ReportServiceError(
                exc.code,
                str(exc) or "보고서 생성 중 LLM 오류가 발생했습니다.",
            ) from exc

        # Success: atomically close the room + create a new active room.
        result = self._room_service.close_room_with_report(room_id, report)
        return GenerateReportResponse(
            report=report,
            closedRoomId=result.closed_room.id,
            newRoom=result.new_room,
        )
