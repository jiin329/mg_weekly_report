import { describe, expect, it } from "vitest";
import type {
    CreateRoomResponse,
    GenerateReportResponse,
    ListMessagesResponse,
    ListRoomsResponse,
    SendMessageRequest,
    SendMessageResponse,
} from "./api";
import type { ChatRoom, Message, WeeklyReport } from "./index";

// These tests are primarily compile-time contract checks: constructing each
// request/response type with the documented shape (design.md "REST API
// 인터페이스") ensures the types reuse the shared data models from ./index and
// stay in sync with the backend `app.schemas` contract.

const activeRoom: ChatRoom = {
  id: "room-1",
  status: "active",
  createdAt: "2024-01-01T00:00:00Z",
  closedAt: null,
  report: null,
};

const report: WeeklyReport = {
  writtenDate: "2024-01-07",
  achievements: "did work",
  nextWeekPlan: "more work",
  issues: "none",
};

const message: Message = {
  id: "msg-1",
  roomId: "room-1",
  sender: "user",
  content: "hello",
  createdAt: "2024-01-01T00:01:00Z",
};

describe("REST API contract types", () => {
  it("POST /rooms response wraps a room", () => {
    const resp: CreateRoomResponse = { room: activeRoom };
    expect(resp.room.status).toBe("active");
  });

  it("GET /rooms response wraps a rooms array", () => {
    const resp: ListRoomsResponse = { rooms: [activeRoom] };
    expect(resp.rooms).toHaveLength(1);
  });

  it("GET /rooms/{roomId}/messages response wraps a messages array", () => {
    const resp: ListMessagesResponse = { messages: [message] };
    expect(resp.messages[0].roomId).toBe("room-1");
  });

  it("POST /rooms/{roomId}/messages request carries content", () => {
    const req: SendMessageRequest = { content: "hello world" };
    expect(req.content).toBe("hello world");
  });

  it("POST /rooms/{roomId}/messages response wraps a message", () => {
    const resp: SendMessageResponse = { message };
    expect(resp.message.sender).toBe("user");
  });

  it("POST /rooms/{roomId}/report response carries report, closedRoomId, newRoom", () => {
    const resp: GenerateReportResponse = {
      report,
      closedRoomId: "room-1",
      newRoom: { ...activeRoom, id: "room-2" },
    };
    expect(resp.closedRoomId).toBe("room-1");
    expect(resp.report.nextWeekPlan).toBe("more work");
    expect(resp.newRoom.status).toBe("active");
  });
});
