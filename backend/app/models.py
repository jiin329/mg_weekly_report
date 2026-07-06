"""Shared data models for the weekly-report-chat backend (task 1.2).

These Pydantic models express the SAME contract as the TypeScript definitions in
`frontend/src/types/index.ts`. Both sides must be kept in sync. To match the
JSON field names used on the wire (and by the TypeScript interfaces), the models
serialize/deserialize using camelCase aliases (e.g. `roomId`, `createdAt`,
`closedAt`, `writtenDate`, `nextWeekPlan`, `llmApiKey`, `backendPort`).

Documented data-model invariants (see design.md "Data Models"):
- ChatRoom: status == 'closed'  ==>  report is not None AND closedAt is not None
- ChatRoom: status == 'active'  ==>  report is None AND closedAt is None
- At most one 'active' room exists in the whole system at any time. This is a
  SYSTEM-LEVEL invariant across rooms and cannot be enforced by a single model;
  RoomService (task 4.4) is responsible for maintaining it.
- Message: for a 'user' message, content.strip() must be non-empty
  (content.trim().length > 0 on the frontend).
- Messages within a room are stored/retrieved in chronological (createdAt
  ascending) order; ordering is enforced by the storage/service layer.
"""

from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, model_validator
from pydantic.alias_generators import to_camel

RoomStatus = Literal["active", "closed"]
MessageSender = Literal["user", "system"]


class _CamelModel(BaseModel):
    """Base model that serializes with camelCase aliases to match the TS contract.

    `populate_by_name=True` lets code construct instances using the Python field
    names as well as the camelCase aliases, so tests and internal callers are not
    forced to use the wire names.
    """

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class WeeklyReport(_CamelModel):
    """Structured weekly report produced by the LLM.

    Invariant: all four sections are always present (Requirement 5.2). Pydantic
    enforces this because every field is required (no default).
    """

    writtenDate: str  # 작성일 (ISO 8601 or display date)
    achievements: str  # 금주 업무 실적
    nextWeekPlan: str  # 차주 업무 계획
    issues: str  # 이슈 및 건의사항


class Message(_CamelModel):
    """A single chat message within a ChatRoom."""

    id: str
    roomId: str
    sender: MessageSender
    content: str
    createdAt: str  # ISO 8601

    @model_validator(mode="after")
    def _user_content_not_blank(self) -> "Message":
        # Invariant: a 'user' message must have non-blank content
        # (content.trim().length > 0). System messages (e.g. reports) are exempt.
        if self.sender == "user" and not self.content.strip():
            raise ValueError("user message content must not be blank")
        return self


class ChatRoom(_CamelModel):
    """A chat space for producing one weekly report."""

    id: str
    status: RoomStatus
    createdAt: str  # ISO 8601
    closedAt: Optional[str] = None  # set when the room is closed; None while active
    report: Optional[WeeklyReport] = None  # the generated report; None while active

    @model_validator(mode="after")
    def _status_matches_lifecycle_fields(self) -> "ChatRoom":
        # Invariant: closed  ==>  report and closedAt are both present.
        # Invariant: active  ==>  report and closedAt are both None.
        if self.status == "closed":
            if self.report is None or self.closedAt is None:
                raise ValueError(
                    "closed room requires both report and closedAt to be set"
                )
        else:  # active
            if self.report is not None or self.closedAt is not None:
                raise ValueError(
                    "active room must have report and closedAt set to None"
                )
        return self


class ErrorDetail(_CamelModel):
    """Body of a structured error (see design.md Error Handling)."""

    code: str  # e.g. 'ROOM_NOT_FOUND', 'ROOM_CLOSED', 'LLM_UNAVAILABLE'
    message: str  # human-readable description
    details: Optional[Any] = None  # optional extra context


class ErrorResponse(_CamelModel):
    """Structured error response returned by every failing endpoint."""

    error: ErrorDetail


class AppConfig(_CamelModel):
    """Application configuration sourced from environment variables.

    Invariant: llmApiKey and llmEndpoint must be non-empty; an empty value must
    raise a startup error (Requirements 10.6, 11.9). That validation lives in the
    Config loader (task 4.1); this model only fixes the shared shape.
    """

    llmApiKey: str  # env LLM_API_KEY
    llmEndpoint: str  # env LLM_ENDPOINT
    backendPort: int  # env BACKEND_PORT (default provided by the loader)
