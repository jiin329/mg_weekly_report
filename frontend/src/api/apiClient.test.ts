import { describe, expect, it } from "vitest";
import { ERROR_CODES } from "../types/errorCodes";
import { ApiError, CONNECTION_ERROR, createApiClient } from "./apiClient";
import { createMockFetch } from "../mock/mockBackend";

// These tests exercise the apiClient AND the mock backend harness together:
// the mock provides a fetch-compatible function, and the apiClient talks to it
// exactly as it would to the real loopback backend. This mirrors how the UI
// runs during FE-only development (task 3.1).

function makeClient() {
  return createApiClient({ baseUrl: "http://mock", fetchFn: createMockFetch() });
}

describe("apiClient + mock backend", () => {
  it("createRoom returns a valid active room", async () => {
    const client = makeClient();
    const room = await client.createRoom();
    expect(room.status).toBe("active");
    expect(room.report).toBeNull();
    expect(room.closedAt).toBeNull();
    expect(typeof room.id).toBe("string");
    expect(room.id.length).toBeGreaterThan(0);
  });

  it("listRooms returns the seeded active room", async () => {
    const client = makeClient();
    const rooms = await client.listRooms();
    expect(rooms.length).toBeGreaterThanOrEqual(1);
    expect(rooms.some((r) => r.status === "active")).toBe(true);
  });

  it("sendMessage then listMessages round-trips the content", async () => {
    const client = makeClient();
    const rooms = await client.listRooms();
    const roomId = rooms[0].id;

    const sent = await client.sendMessage(roomId, "이번 주에 API 작업을 했다");
    expect(sent.content).toBe("이번 주에 API 작업을 했다");
    expect(sent.sender).toBe("user");

    const messages = await client.listMessages(roomId);
    expect(messages.some((m) => m.content === "이번 주에 API 작업을 했다")).toBe(
      true,
    );
  });

  it("rejects a blank message with EMPTY_MESSAGE", async () => {
    const client = makeClient();
    const rooms = await client.listRooms();
    await expect(client.sendMessage(rooms[0].id, "   ")).rejects.toMatchObject({
      code: ERROR_CODES.EMPTY_MESSAGE,
      httpStatus: 400,
    });
  });

  it("returns ROOM_NOT_FOUND for an unknown room id", async () => {
    const client = makeClient();
    await expect(client.listMessages("does-not-exist")).rejects.toMatchObject({
      code: ERROR_CODES.ROOM_NOT_FOUND,
      httpStatus: 404,
    });
  });

  it("generateReport closes the room and creates exactly one new active room", async () => {
    const client = makeClient();
    const rooms = await client.listRooms();
    const roomId = rooms[0].id;
    await client.sendMessage(roomId, "작업 내용");

    const result = await client.generateReport(roomId);
    expect(result.closedRoomId).toBe(roomId);
    expect(result.newRoom.status).toBe("active");
    // report has all four sections
    expect(result.report.writtenDate).toBeTruthy();
    expect(result.report.achievements).toBeTruthy();
    expect(result.report.nextWeekPlan).toBeTruthy();
    expect(result.report.issues).toBeTruthy();

    const after = await client.listRooms();
    const active = after.filter((r) => r.status === "active");
    expect(active).toHaveLength(1);
    expect(active[0].id).toBe(result.newRoom.id);

    const closed = after.find((r) => r.id === roomId);
    expect(closed?.status).toBe("closed");
    expect(closed?.report).not.toBeNull();
    expect(closed?.closedAt).not.toBeNull();
  });

  it("closed room rejects further messages and report with ROOM_CLOSED", async () => {
    const client = makeClient();
    const rooms = await client.listRooms();
    const roomId = rooms[0].id;
    await client.sendMessage(roomId, "작업 내용");
    await client.generateReport(roomId);

    await expect(client.sendMessage(roomId, "더 보낼래")).rejects.toMatchObject({
      code: ERROR_CODES.ROOM_CLOSED,
      httpStatus: 409,
    });
    await expect(client.generateReport(roomId)).rejects.toMatchObject({
      code: ERROR_CODES.ROOM_CLOSED,
    });
  });

  it("rejects report generation on a room with no messages (NO_MESSAGES)", async () => {
    const client = makeClient();
    const rooms = await client.listRooms();
    await expect(client.generateReport(rooms[0].id)).rejects.toMatchObject({
      code: ERROR_CODES.NO_MESSAGES,
      httpStatus: 400,
    });
  });

  it("surfaces a distinct connection error when the backend is unreachable", async () => {
    const failingFetch = () => Promise.reject(new TypeError("Failed to fetch"));
    const client = createApiClient({ baseUrl: "http://down", fetchFn: failingFetch });
    const err = await client.createRoom().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe(CONNECTION_ERROR);
    expect(err.httpStatus).toBeNull();
  });
});
