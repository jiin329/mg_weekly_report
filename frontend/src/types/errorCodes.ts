/**
 * Shared error-code catalog and HTTP status mapping (task 1.4).
 *
 * This module mirrors the Backend catalog in `backend/app/error_codes.py`; both
 * sides must be kept in sync. It lets the apiClient branch on `error.code`
 * (see the ErrorResponse type in ./index) instead of parsing messages.
 *
 * The error *shape* (ErrorResponse) is owned by task 1.2 and lives in ./index —
 * this module does NOT redefine it, it only adds the code constants and the
 * HTTP status mapping.
 */

/**
 * Catalog of structured error codes. Each documents the situation that
 * produces it (see design.md "오류 코드 카탈로그").
 */
export const ERROR_CODES = {
  ROOM_NOT_FOUND: "ROOM_NOT_FOUND", // 존재하지 않는 room id 요청 (Req 8.7)
  ROOM_CLOSED: "ROOM_CLOSED", // Closed 방에 메시지/보고서 요청 (Req 6.6)
  EMPTY_MESSAGE: "EMPTY_MESSAGE", // 공백 전용 메시지 전송 - Backend 방어 (Req 3.3)
  NO_MESSAGES: "NO_MESSAGES", // 메시지 없는 방의 보고서 생성 시도 (Req 4.5)
  LLM_UNAVAILABLE: "LLM_UNAVAILABLE", // LLM API 미도달/오류 (Req 5.7, 9.4)
  LLM_TIMEOUT: "LLM_TIMEOUT", // LLM 응답 시간 초과 (Req 5.3, 9.4)
  CONFIG_MISSING: "CONFIG_MISSING", // 필수 LLM 설정 누락 - 실행 중 감지 (Req 11.9)
  INTERNAL_ERROR: "INTERNAL_ERROR", // 그 외 내부 오류 (Req 8.8)
} as const;

export type ErrorCode = (typeof ERROR_CODES)[keyof typeof ERROR_CODES];

/** Code -> HTTP status mapping, matching design.md's catalog table. */
export const ERROR_STATUS_MAP: Record<ErrorCode, number> = {
  ROOM_NOT_FOUND: 404,
  ROOM_CLOSED: 409,
  EMPTY_MESSAGE: 400,
  NO_MESSAGES: 400,
  LLM_UNAVAILABLE: 502,
  LLM_TIMEOUT: 504,
  CONFIG_MISSING: 500,
  INTERNAL_ERROR: 500,
};

/** Narrow an unknown string to a known ErrorCode. */
export function isErrorCode(value: unknown): value is ErrorCode {
  return (
    typeof value === "string" &&
    Object.prototype.hasOwnProperty.call(ERROR_STATUS_MAP, value)
  );
}
