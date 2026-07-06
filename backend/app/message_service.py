"""MessageService — message storage and retrieval (task 4.5).

Responsibilities:
- Store user messages in chronological order
- Retrieve messages for a room in chronological order
- Reject blank/whitespace-only messages (EMPTY_MESSAGE)
- Reject messages to closed rooms (ROOM_CLOSED)
- Reject messages to non-existent rooms (ROOM_NOT_FOUND)

Requirements: 3.1, 3.2, 3.4, 3.5, 6.6
Dependencies: Repository (4.2), Models (4.3)
"""

import uuid
from datetime import datetime, timezone

from .error_codes import ErrorCode
from .models import Message
from .repository import Repository


class MessageServiceError(Exception):
    """Structured error raised by MessageService operations."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(message)


class MessageService:
    """Handles message sending and retrieval with business-rule enforcement."""

    def __init__(self, repo: Repository) -> None:
        self._repo = repo

    def send_message(self, room_id: str, content: str) -> Message:
        """Send a user message to a room.

        Raises MessageServiceError if:
        - content is blank (EMPTY_MESSAGE)
        - room does not exist (ROOM_NOT_FOUND)
        - room is closed (ROOM_CLOSED)
        """
        # Validate content is not blank
        if not content.strip():
            raise MessageServiceError(
                code=ErrorCode.EMPTY_MESSAGE.value,
                message="메시지 내용이 비어있습니다.",
            )

        # Validate room exists
        room = self._repo.get_room(room_id)
        if room is None:
            raise MessageServiceError(
                code=ErrorCode.ROOM_NOT_FOUND.value,
                message=f"채팅방을 찾을 수 없습니다: {room_id}",
            )

        # Validate room is active
        if room["status"] == "closed":
            raise MessageServiceError(
                code=ErrorCode.ROOM_CLOSED.value,
                message="종료된 채팅방에는 메시지를 보낼 수 없습니다.",
            )

        # Store the message
        msg_id = str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()

        row = self._repo.add_message(
            id=msg_id,
            room_id=room_id,
            sender="user",
            content=content,
            created_at=created_at,
        )

        return Message(
            id=row["id"],
            roomId=row["room_id"],
            sender=row["sender"],
            content=row["content"],
            createdAt=row["created_at"],
        )

    def get_messages(self, room_id: str) -> list[Message]:
        """Get all messages for a room in chronological order.

        Raises MessageServiceError if room does not exist (ROOM_NOT_FOUND).
        """
        room = self._repo.get_room(room_id)
        if room is None:
            raise MessageServiceError(
                code=ErrorCode.ROOM_NOT_FOUND.value,
                message=f"채팅방을 찾을 수 없습니다: {room_id}",
            )

        rows = self._repo.get_messages(room_id)
        return [
            Message(
                id=r["id"],
                roomId=r["room_id"],
                sender=r["sender"],
                content=r["content"],
                createdAt=r["created_at"],
            )
            for r in rows
        ]
