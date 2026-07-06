/**
 * REST API request/response contract types (task 1.3).
 *
 * These fix the SHARED request/response shapes for the five REST endpoints from
 * design.md "REST API 인터페이스". This is the frontend counterpart of the backend
 * contract in `backend/app/schemas.py`; both sides must stay in sync.
 *
 * These types only reuse the shared data models from ./index (task 1.2) — they
 * do NOT redefine ChatRoom / Message / WeeklyReport. The apiClient (task 3.1)
 * and the FastAPI endpoints (task 4.6) both reference these shapes; this module
 * is contract only.
 *
 * Endpoints (base path http://127.0.0.1:{PORT}):
 *
 *   | Method & Path                 | Request     | Response                          | Req
 *   | ----------------------------- | ----------- | --------------------------------- | -------------
 *   | POST /rooms                   | (none)      | { room: ChatRoom }                | 1.3, 8.2
 *   | GET  /rooms                   | (none)      | { rooms: ChatRoom[] }             | 7.1, 8.6
 *   | GET  /rooms/{roomId}/messages | (none)      | { messages: Message[] }           | 8.4
 *   | POST /rooms/{roomId}/messages | { content } | { message: Message }              | 3.1, 3.5, 8.3
 *   | POST /rooms/{roomId}/report   | (none)      | { report, closedRoomId, newRoom } | 4.2, 5.3,
 *   |                               |             |                                   | 6.1-6.3, 8.5
 *
 * Behavioral rules the backend enforces (documented here as part of the
 * contract; the frontend relies on them and surfaces the structured errors):
 *
 * - Closed room rejects messages: POST /rooms/{roomId}/messages against a room
 *   whose status === 'closed' fails with a structured error (code ROOM_CLOSED)
 *   and does not modify the room (Requirements 6.6, 6.2). The InputArea also
 *   disables input for closed rooms, but the backend defends against it too.
 * - Room with no messages rejects report generation: POST /rooms/{roomId}/report
 *   against a room with zero user messages fails with a structured error (code
 *   NO_MESSAGES). The GenerateButton blocks this preemptively (Requirement 4.5),
 *   and the backend defends against it as well.
 * - Report generation is atomic: on success the backend produces the report,
 *   closes the target room, and creates a new active room as a single logical
 *   transaction, so exactly one active room ever exists (Requirements 6.1, 6.3).
 *   The response carries the report, the closed room id, and the new active room.
 * - Invalid roomId returns a structured error (code ROOM_NOT_FOUND, Req 8.7).
 *
 * Every failing request returns the structured `ErrorResponse` from ./index
 * (see design.md "Error Handling"). The error-code catalog itself lives in a
 * separate module; codes are referenced here by name only.
 */

import type { ChatRoom, Message, WeeklyReport } from "./index";

/** Response for POST /rooms — the newly created active room (Req 1.3, 8.2). */
export interface CreateRoomResponse {
  room: ChatRoom;
}

/** Response for GET /rooms — all rooms, active and closed (Req 7.1, 8.6). */
export interface ListRoomsResponse {
  rooms: ChatRoom[];
}

/**
 * Response for GET /rooms/{roomId}/messages — messages in chronological order
 * (Req 8.4).
 */
export interface ListMessagesResponse {
  messages: Message[];
}

/**
 * Request body for POST /rooms/{roomId}/messages (Req 3.1, 3.5). `content` must
 * be non-blank after trim for a user message (see isUserMessageContentValid in
 * ./index); the backend rejects blank content (EMPTY_MESSAGE) and closed rooms
 * (ROOM_CLOSED, Req 6.6).
 */
export interface SendMessageRequest {
  content: string;
}

/** Response for POST /rooms/{roomId}/messages — the stored message (Req 3.1, 8.3). */
export interface SendMessageResponse {
  message: Message;
}

/**
 * Response for POST /rooms/{roomId}/report (Req 4.2, 5.3, 6.1, 6.3, 8.5).
 * On success the backend atomically produces the report, closes the target
 * room, and creates a new active room.
 * - report:       the produced weekly report (four sections guaranteed)
 * - closedRoomId: id of the room that was just closed
 * - newRoom:      the newly created active room
 */
export interface GenerateReportResponse {
  report: WeeklyReport;
  closedRoomId: string;
  newRoom: ChatRoom;
}
