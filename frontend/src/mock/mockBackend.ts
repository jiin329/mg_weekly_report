/**
 * In-memory mock backend harness (task 3.1).
 *
 * `createMockFetch()` returns a `fetch`-compatible function backed by a small
 * in-memory store. It lets the whole UI run FE-only, with no real backend, while
 * emulating the REST contract (types/api.ts) and the documented behavioral rules
 * (see design.md "REST API 인터페이스"). The apiClient talks to it exactly as it
 * would to the real loopback backend.
 *
 * Emulated rules:
 * - Startup seeds exactly one active room.
 * - At most one active room ever exists (POST /rooms reuses the current active
 *   room instead of creating a second one).
 * - Closed room rejects messages and report generation (ROOM_CLOSED).
 * - Blank message content is rejected (EMPTY_MESSAGE).
 * - Report generation on a room with no user messages is rejected (NO_MESSAGES).
 * - Report generation is atomic: produce report, close the target room, create a
 *   new active room — so exactly one active room remains afterwards.
 * - Unknown room id -> ROOM_NOT_FOUND; every failure returns a structured
 *   ErrorResponse ({ error: { code, message } }).
 *
 * This is a development aid, not production code: responses are canned and kept
 * intentionally simple.
 */

import type {
  CreateRoomResponse,
  GenerateReportResponse,
  ListMessagesResponse,
  ListRoomsResponse,
  SendMessageResponse,
} from "../types/api";
import type { ChatRoom, ErrorResponse, Message, WeeklyReport } from "../types/index";
import { isUserMessageContentValid } from "../types/index";
import {
  ERROR_CODES,
  ERROR_STATUS_MAP,
  type ErrorCode,
} from "../types/errorCodes";

/** Human-readable messages for each emulated error code. */
const ERROR_MESSAGES: Record<ErrorCode, string> = {
  ROOM_NOT_FOUND: "요청한 채팅방을 찾을 수 없습니다.",
  ROOM_CLOSED: "이미 종료된 채팅방입니다.",
  EMPTY_MESSAGE: "빈 메시지는 전송할 수 없습니다.",
  NO_MESSAGES: "메시지가 없어 주간보고를 생성할 수 없습니다.",
  LLM_UNAVAILABLE: "보고서 생성 서비스에 연결할 수 없습니다.",
  LLM_TIMEOUT: "보고서 생성 시간이 초과되었습니다.",
  CONFIG_MISSING: "필수 설정이 누락되었습니다.",
  INTERNAL_ERROR: "요청을 처리할 수 없습니다.",
};

function nowIso(): string {
  return new Date().toISOString();
}

function newId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  return `id-${Math.random().toString(36).slice(2)}-${Date.now()}`;
}

function newActiveRoom(): ChatRoom {
  return {
    id: newId(),
    status: "active",
    createdAt: nowIso(),
    closedAt: null,
    report: null,
  };
}

function jsonResponse(body: unknown, status: number): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

function errorResponse(code: ErrorCode): Response {
  const body: ErrorResponse = { error: { code, message: ERROR_MESSAGES[code] } };
  return jsonResponse(body, ERROR_STATUS_MAP[code]);
}

export function createMockFetch() {
  const rooms: ChatRoom[] = [newActiveRoom()];
  const messagesByRoom = new Map<string, Message[]>();
  messagesByRoom.set(rooms[0].id, []);

  function findRoom(roomId: string): ChatRoom | undefined {
    return rooms.find((r) => r.id === roomId);
  }

  function activeRoom(): ChatRoom | undefined {
    return rooms.find((r) => r.status === "active");
  }

  function handleCreateRoom(): Response {
    // Preserve the single-active-room invariant: reuse the current active room
    // if one exists, otherwise start a fresh one.
    let room = activeRoom();
    if (!room) {
      room = newActiveRoom();
      rooms.push(room);
      messagesByRoom.set(room.id, []);
    }
    const body: CreateRoomResponse = { room };
    return jsonResponse(body, 201);
  }

  function handleListRooms(): Response {
    const body: ListRoomsResponse = { rooms };
    return jsonResponse(body, 200);
  }

  function handleListMessages(roomId: string): Response {
    const room = findRoom(roomId);
    if (!room) return errorResponse(ERROR_CODES.ROOM_NOT_FOUND);
    const body: ListMessagesResponse = {
      messages: messagesByRoom.get(roomId) ?? [],
    };
    return jsonResponse(body, 200);
  }

  function handleSendMessage(roomId: string, content: unknown): Response {
    const room = findRoom(roomId);
    if (!room) return errorResponse(ERROR_CODES.ROOM_NOT_FOUND);
    if (room.status === "closed") return errorResponse(ERROR_CODES.ROOM_CLOSED);
    if (typeof content !== "string" || !isUserMessageContentValid(content)) {
      return errorResponse(ERROR_CODES.EMPTY_MESSAGE);
    }
    const message: Message = {
      id: newId(),
      roomId,
      sender: "user",
      content,
      createdAt: nowIso(),
    };
    messagesByRoom.get(roomId)?.push(message);
    const body: SendMessageResponse = { message };
    return jsonResponse(body, 201);
  }

  function handleGenerateReport(roomId: string): Response {
    const room = findRoom(roomId);
    if (!room) return errorResponse(ERROR_CODES.ROOM_NOT_FOUND);
    if (room.status === "closed") return errorResponse(ERROR_CODES.ROOM_CLOSED);

    const userMessages = (messagesByRoom.get(roomId) ?? []).filter(
      (m) => m.sender === "user",
    );
    if (userMessages.length === 0) {
      return errorResponse(ERROR_CODES.NO_MESSAGES);
    }

    const report: WeeklyReport = {
      writtenDate: nowIso().slice(0, 10),
      achievements: userMessages.map((m) => `- ${m.content}`).join("\n"),
      nextWeekPlan: "차주 계획을 이어서 진행합니다.",
      issues: "특이사항 없음",
    };

    // Atomic: close the target room and create a new active room.
    const closedAt = nowIso();
    room.status = "closed";
    room.closedAt = closedAt;
    room.report = report;

    const created = newActiveRoom();
    rooms.push(created);
    messagesByRoom.set(created.id, []);

    const body: GenerateReportResponse = {
      report,
      closedRoomId: roomId,
      newRoom: created,
    };
    return jsonResponse(body, 201);
  }

  return async function mockFetch(
    input: RequestInfo | URL,
    init?: RequestInit,
  ): Promise<Response> {
    const url = new URL(
      typeof input === "string" ? input : input.toString(),
    );
    const path = url.pathname;
    const method = (init?.method ?? "GET").toUpperCase();

    if (path === "/rooms") {
      if (method === "POST") return handleCreateRoom();
      if (method === "GET") return handleListRooms();
    }

    const messagesMatch = path.match(/^\/rooms\/([^/]+)\/messages$/);
    if (messagesMatch) {
      const roomId = decodeURIComponent(messagesMatch[1]);
      if (method === "GET") return handleListMessages(roomId);
      if (method === "POST") {
        const content = parseBodyContent(init?.body);
        return handleSendMessage(roomId, content);
      }
    }

    const reportMatch = path.match(/^\/rooms\/([^/]+)\/report$/);
    if (reportMatch && method === "POST") {
      const roomId = decodeURIComponent(reportMatch[1]);
      return handleGenerateReport(roomId);
    }

    return errorResponse(ERROR_CODES.INTERNAL_ERROR);
  };
}

/** Extract `content` from a JSON request body, if present. */
function parseBodyContent(body: BodyInit | null | undefined): unknown {
  if (typeof body !== "string") return undefined;
  try {
    return (JSON.parse(body) as { content?: unknown }).content;
  } catch {
    return undefined;
  }
}
