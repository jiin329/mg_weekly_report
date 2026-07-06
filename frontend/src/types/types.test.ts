import { describe, expect, it } from "vitest";
import {
    isUserMessageContentValid,
    type AppConfig,
    type ChatRoom,
    type ErrorResponse,
    type Message,
    type WeeklyReport,
} from "./index";

// These tests exercise the shared TypeScript contract (task 1.2). The types are
// compile-time only, so we construct valid instances (compilation is the check)
// and unit-test the one runtime invariant helper (user message content).

describe("shared types", () => {
  it("constructs a valid active ChatRoom", () => {
    const room: ChatRoom = {
      id: "r1",
      status: "active",
      createdAt: "2024-01-05T10:00:00Z",
      closedAt: null,
      report: null,
    };
    expect(room.status).toBe("active");
  });

  it("constructs a valid closed ChatRoom with a report", () => {
    const report: WeeklyReport = {
      writtenDate: "2024-01-05",
      achievements: "A",
      nextWeekPlan: "B",
      issues: "C",
    };
    const room: ChatRoom = {
      id: "r1",
      status: "closed",
      createdAt: "2024-01-05T10:00:00Z",
      closedAt: "2024-01-05T12:00:00Z",
      report,
    };
    expect(room.report?.issues).toBe("C");
  });

  it("constructs a valid user Message", () => {
    const msg: Message = {
      id: "m1",
      roomId: "r1",
      sender: "user",
      content: "hello",
      createdAt: "2024-01-05T10:00:00Z",
    };
    expect(msg.sender).toBe("user");
  });

  it("constructs an ErrorResponse", () => {
    const err: ErrorResponse = {
      error: { code: "ROOM_NOT_FOUND", message: "not found" },
    };
    expect(err.error.code).toBe("ROOM_NOT_FOUND");
  });

  it("constructs an AppConfig", () => {
    const cfg: AppConfig = {
      llmApiKey: "key",
      llmEndpoint: "https://llm.example",
      backendPort: 8756,
    };
    expect(cfg.backendPort).toBe(8756);
  });
});

describe("isUserMessageContentValid", () => {
  it("accepts non-blank content", () => {
    expect(isUserMessageContentValid("hi")).toBe(true);
    expect(isUserMessageContentValid("  padded  ")).toBe(true);
  });

  it("rejects empty or whitespace-only content", () => {
    expect(isUserMessageContentValid("")).toBe(false);
    expect(isUserMessageContentValid("   \n\t  ")).toBe(false);
  });
});
