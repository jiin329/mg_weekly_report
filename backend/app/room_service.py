"""RoomService — chat room lifecycle management (task 4.4).

Responsibilities:
- Room creation/retrieval/listing
- Active↔Closed state transitions
- Atomic report generation: close room + create new active room
- Maintains the system invariant: at most 1 active room at any time

Requirements: 1.3, 6.1, 6.3, 7.1, 8.2, 8.6
Dependencies: Repository (task 4.2), Models (task 4.3)
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional

from .models import ChatRoom, WeeklyReport
from .repository import Repository


@dataclass
class CloseRoomResult:
    """Result of closing a room with a report."""

    closed_room: ChatRoom
    new_room: ChatRoom


class RoomService:
    """Manages chat room lifecycle and enforces the single-active-room invariant."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def create_room(self) -> ChatRoom:
        """Create a new active room.

        Enforces the single-active-room invariant: if an active room already
        exists, it is closed (bare close with empty report) before creating
        the new one. The normal flow closes rooms via close_room_with_report;
        this is a safety net for edge cases.
        """
        existing_rooms = self._repo.list_rooms()
        for room in existing_rooms:
            if room["status"] == "active":
                closed_at = datetime.now(timezone.utc).isoformat()
                self._repo.close_room(
                    room["id"],
                    closed_at=closed_at,
                    report={
                        "writtenDate": closed_at,
                        "achievements": "",
                        "nextWeekPlan": "",
                        "issues": "",
                    },
                )

        row = self._repo.create_room()
        return self._row_to_chatroom(row)

    def get_room(self, room_id: str) -> Optional[ChatRoom]:
        """Get a room by id. Returns None if not found."""
        row = self._repo.get_room(room_id)
        if row is None:
            return None
        return self._row_to_chatroom(row)

    def list_rooms(self) -> list[ChatRoom]:
        """List all rooms (active and closed), newest first."""
        rows = self._repo.list_rooms()
        return [self._row_to_chatroom(r) for r in rows]

    def close_room_with_report(self, room_id: str, report: WeeklyReport) -> CloseRoomResult:
        """Atomically close a room with a report and create a new active room.

        This is the ONLY legitimate way to transition Active -> Closed.
        On success: target room becomes closed, a new active room is created.

        Raises ValueError if:
        - room_id does not exist
        - room is already closed
        """
        room_row = self._repo.get_room(room_id)
        if room_row is None:
            raise ValueError(f"Room not found: {room_id}")
        if room_row["status"] == "closed":
            raise ValueError(f"Room already closed: {room_id}")

        closed_at = datetime.now(timezone.utc).isoformat()
        report_dict = report.model_dump()

        # Atomic: close room + create new active room
        self._repo.close_room(room_id, closed_at=closed_at, report=report_dict)
        new_room_row = self._repo.create_room()

        closed_room = self._row_to_chatroom(self._repo.get_room(room_id))  # type: ignore
        new_room = self._row_to_chatroom(new_room_row)

        return CloseRoomResult(closed_room=closed_room, new_room=new_room)

    @staticmethod
    def _row_to_chatroom(row: dict) -> ChatRoom:
        """Convert a repository dict to a ChatRoom model."""
        report_data = row.get("report")
        report = WeeklyReport(**report_data) if report_data else None
        return ChatRoom(
            id=row["id"],
            status=row["status"],
            createdAt=row["created_at"],
            closedAt=row.get("closed_at"),
            report=report,
        )
