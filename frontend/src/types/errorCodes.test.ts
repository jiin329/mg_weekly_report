import { describe, expect, it } from "vitest";
import {
    ERROR_CODES,
    ERROR_STATUS_MAP,
    isErrorCode,
    type ErrorCode,
} from "./errorCodes";

// Expected code -> HTTP status mapping from design.md's "오류 코드 카탈로그".
const EXPECTED: Record<ErrorCode, number> = {
  ROOM_NOT_FOUND: 404,
  ROOM_CLOSED: 409,
  EMPTY_MESSAGE: 400,
  NO_MESSAGES: 400,
  LLM_UNAVAILABLE: 502,
  LLM_TIMEOUT: 504,
  CONFIG_MISSING: 500,
  INTERNAL_ERROR: 500,
};

describe("error-code catalog", () => {
  it("contains exactly the expected codes", () => {
    expect(new Set(Object.values(ERROR_CODES))).toEqual(
      new Set(Object.keys(EXPECTED)),
    );
  });

  it("maps every code to the expected HTTP status", () => {
    for (const [code, status] of Object.entries(EXPECTED)) {
      expect(ERROR_STATUS_MAP[code as ErrorCode]).toBe(status);
    }
  });

  it("recognizes known codes and rejects unknown ones", () => {
    expect(isErrorCode("ROOM_NOT_FOUND")).toBe(true);
    expect(isErrorCode("NOPE")).toBe(false);
    expect(isErrorCode(undefined)).toBe(false);
  });
});
