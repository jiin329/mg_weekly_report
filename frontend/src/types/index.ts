/**
 * Shared data model types for the weekly-report-chat frontend (task 1.2).
 *
 * These TypeScript definitions express the SAME contract as the Pydantic models
 * in `backend/app/models.py`. Both sides must be kept in sync. The field names
 * here are the wire (JSON) names the backend serializes with camelCase aliases.
 *
 * Documented data-model invariants (see design.md "Data Models"):
 * - ChatRoom: status === 'closed'  =>  report !== null AND closedAt !== null
 * - ChatRoom: status === 'active'  =>  report === null AND closedAt === null
 * - At most one 'active' room exists in the whole system at any time. This is a
 *   system-level invariant across rooms, enforced by the backend RoomService,
 *   not expressible in a single type.
 * - Message: for a 'user' message, content.trim().length > 0 (see
 *   `isUserMessageContentValid`).
 * - Messages within a room are ordered chronologically (createdAt ascending),
 *   enforced by the backend.
 */

export type RoomStatus = "active" | "closed";

export type MessageSender = "user" | "system";

export interface WeeklyReport {
  writtenDate: string; // 작성일 (ISO 8601 or display date)
  achievements: string; // 금주 업무 실적
  nextWeekPlan: string; // 차주 업무 계획
  issues: string; // 이슈 및 건의사항
}

export interface ChatRoom {
  id: string; // UUID
  status: RoomStatus;
  createdAt: string; // ISO 8601
  closedAt: string | null; // set when closed; null while active
  report: WeeklyReport | null; // the generated report; null while active
}

export interface Message {
  id: string; // UUID
  roomId: string; // owning ChatRoom id
  sender: MessageSender; // 'user' | 'system' (report, etc.)
  content: string; // for a user message, non-blank after trim
  createdAt: string; // ISO 8601
}

export interface ErrorResponse {
  error: {
    code: string; // e.g. 'ROOM_NOT_FOUND', 'ROOM_CLOSED', 'LLM_UNAVAILABLE'
    message: string; // human-readable description
    details?: unknown; // optional extra context
  };
}

export interface AppConfig {
  llmApiKey: string; // env LLM_API_KEY
  llmEndpoint: string; // env LLM_ENDPOINT
  backendPort: number; // env BACKEND_PORT (default provided by backend)
}

/**
 * Encodes the user-message invariant: a user message must have non-blank
 * content (content.trim().length > 0). Used by the InputArea to block empty
 * sends (Requirement 3.3) and mirrors the backend Message validator.
 */
export function isUserMessageContentValid(content: string): boolean {
  return content.trim().length > 0;
}
