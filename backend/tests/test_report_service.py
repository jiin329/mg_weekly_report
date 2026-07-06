"""Tests for ReportService wired to the stub LLM client — task 4.7.

Verifies the report generation flow:
- Aggregate a room's user messages -> call the LLM interface (task 1.5) ->
  accept the response as a WeeklyReport.
- Reject report generation for a room with no messages (NO_MESSAGES).
- Reject report generation for a closed / non-existent room.
- On LLM failure, keep the room Active (no partial transition) and surface the
  matching structured error (LLM_UNAVAILABLE / LLM_TIMEOUT).
- On success, atomically close the room and create a new active room.

Requirements: 4.2, 4.3, 5.3, 5.7, 6.1, 9.4
Dependencies: RoomService (4.4), API wiring (4.6), LLM interface/stub (1.5)
"""

import os
import tempfile

import pytest

from app.error_codes import ErrorCode
from app.llm import LLMTimeoutError, LLMUnavailableError, StubLLMClient
from app.models import WeeklyReport
from app.report_service import ReportService, ReportServiceError
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


def _make_room_with_message(repo: Repository, content: str = "이번 주 작업 완료") -> str:
    row = repo.create_room()
    repo.add_message(
        id="m1",
        room_id=row["id"],
        sender="user",
        content=content,
        created_at="2024-01-01T00:00:00Z",
    )
    return row["id"]


class TestGenerateReportSuccess:
    def test_returns_generate_report_response_with_report(self, repo):
        room_id = _make_room_with_message(repo)
        service = ReportService(repo, StubLLMClient())

        result = service.generate_report(room_id)

        assert isinstance(result, GenerateReportResponse)
        assert isinstance(result.report, WeeklyReport)
        assert result.closedRoomId == room_id

    def test_closes_room_and_creates_new_active_room(self, repo):
        room_id = _make_room_with_message(repo)
        service = ReportService(repo, StubLLMClient())

        result = service.generate_report(room_id)

        closed = repo.get_room(room_id)
        assert closed["status"] == "closed"
        assert result.newRoom.status == "active"
        assert result.newRoom.id != room_id


class TestGenerateReportRejections:
    def test_no_messages_raises_no_messages(self, repo):
        row = repo.create_room()
        service = ReportService(repo, StubLLMClient())

        with pytest.raises(ReportServiceError) as exc:
            service.generate_report(row["id"])
        assert exc.value.code is ErrorCode.NO_MESSAGES

    def test_nonexistent_room_raises_room_not_found(self, repo):
        service = ReportService(repo, StubLLMClient())

        with pytest.raises(ReportServiceError) as exc:
            service.generate_report("no-such-id")
        assert exc.value.code is ErrorCode.ROOM_NOT_FOUND

    def test_closed_room_raises_room_closed(self, repo):
        room_id = _make_room_with_message(repo)
        service = ReportService(repo, StubLLMClient())
        service.generate_report(room_id)  # closes it

        with pytest.raises(ReportServiceError) as exc:
            service.generate_report(room_id)
        assert exc.value.code is ErrorCode.ROOM_CLOSED


class TestGenerateReportLLMFailure:
    def test_llm_unavailable_keeps_room_active(self, repo):
        room_id = _make_room_with_message(repo)
        service = ReportService(
            repo, StubLLMClient(raise_error=LLMUnavailableError("down"))
        )

        with pytest.raises(ReportServiceError) as exc:
            service.generate_report(room_id)
        assert exc.value.code is ErrorCode.LLM_UNAVAILABLE

        # No partial transition: room is still active and no new room created.
        room = repo.get_room(room_id)
        assert room["status"] == "active"
        assert len(repo.list_rooms()) == 1

    def test_llm_timeout_keeps_room_active(self, repo):
        room_id = _make_room_with_message(repo)
        service = ReportService(
            repo, StubLLMClient(raise_error=LLMTimeoutError("slow"))
        )

        with pytest.raises(ReportServiceError) as exc:
            service.generate_report(room_id)
        assert exc.value.code is ErrorCode.LLM_TIMEOUT

        room = repo.get_room(room_id)
        assert room["status"] == "active"
        assert len(repo.list_rooms()) == 1
