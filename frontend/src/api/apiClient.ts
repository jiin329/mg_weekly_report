/**
 * REST API client (task 3.1).
 *
 * A thin `fetch` wrapper over the five REST endpoints fixed by the contract
 * (types/api.ts). It reuses the shared data models (types/index.ts) and the
 * error-code catalog (types/errorCodes.ts) — it does not redefine any of them.
 *
 * The client is deliberately simple: each method issues one request and either
 * returns the parsed payload or throws an `ApiError`. Structured error bodies
 * ({ error: { code, message, details? } }, see ErrorResponse) are parsed so the
 * UI can branch on `error.code` and show a friendly message. A failed network
 * call (backend unreachable) is surfaced as a distinct CONNECTION_ERROR so the
 * UI can tell "backend is down" apart from "backend said no".
 *
 * A `fetchFn` can be injected; during FE-only development the mock backend
 * harness (mock/mockBackend.ts) supplies a fetch-compatible function, so the
 * exact same client code drives the real loopback backend and the mock.
 */

import type {
  CreateRoomResponse,
  GenerateReportResponse,
  ListMessagesResponse,
  ListRoomsResponse,
  SendMessageResponse,
} from "../types/api";
import type { ChatRoom, ErrorResponse, Message } from "../types/index";
import { ERROR_CODES } from "../types/errorCodes";

/** Fetch-compatible function; matches the global `fetch` signature. */
export type FetchFn = (
  input: RequestInfo | URL,
  init?: RequestInit,
) => Promise<Response>;

/**
 * Code used when the request never reached the backend (network failure,
 * connection refused). It is intentionally NOT part of the backend error
 * catalog because the backend never produces it — only the client does.
 */
export const CONNECTION_ERROR = "CONNECTION_ERROR";

/**
 * Error thrown by every apiClient method on failure. Carries the structured
 * `code` (an ErrorCode from the catalog, or CONNECTION_ERROR) plus the HTTP
 * status when there was a response (`null` for a connection failure).
 */
export class ApiError extends Error {
  readonly code: string;
  readonly httpStatus: number | null;
  readonly details?: unknown;

  constructor(
    code: string,
    message: string,
    httpStatus: number | null,
    details?: unknown,
  ) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.httpStatus = httpStatus;
    this.details = details;
  }
}

export interface ApiClientOptions {
  /** Base URL of the backend, e.g. `http://127.0.0.1:8765`. */
  baseUrl: string;
  /** Fetch implementation to use; defaults to the global `fetch`. */
  fetchFn?: FetchFn;
}

export interface ApiClient {
  createRoom(): Promise<ChatRoom>;
  listRooms(): Promise<ChatRoom[]>;
  listMessages(roomId: string): Promise<Message[]>;
  sendMessage(roomId: string, content: string): Promise<Message>;
  generateReport(roomId: string): Promise<GenerateReportResponse>;
}

export function createApiClient(options: ApiClientOptions): ApiClient {
  const { baseUrl, fetchFn = fetch } = options;

  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    let response: Response;
    try {
      response = await fetchFn(baseUrl + path, init);
    } catch {
      // The request never completed (backend down, DNS/connection error).
      throw new ApiError(
        CONNECTION_ERROR,
        "백엔드에 연결할 수 없습니다. 앱을 다시 시작해 주세요.",
        null,
      );
    }

    const body = await parseJson(response);

    if (!response.ok) {
      const parsed = (body as ErrorResponse | undefined)?.error;
      const code = parsed?.code ?? ERROR_CODES.INTERNAL_ERROR;
      const message = parsed?.message ?? "요청 처리 중 오류가 발생했습니다.";
      throw new ApiError(code, message, response.status, parsed?.details);
    }

    return body as T;
  }

  function post<T>(path: string, jsonBody?: unknown): Promise<T> {
    const init: RequestInit = { method: "POST" };
    if (jsonBody !== undefined) {
      init.headers = { "Content-Type": "application/json" };
      init.body = JSON.stringify(jsonBody);
    }
    return request<T>(path, init);
  }

  return {
    async createRoom() {
      const { room } = await post<CreateRoomResponse>("/rooms");
      return room;
    },
    async listRooms() {
      const { rooms } = await request<ListRoomsResponse>("/rooms", {
        method: "GET",
      });
      return rooms;
    },
    async listMessages(roomId) {
      const { messages } = await request<ListMessagesResponse>(
        `/rooms/${encodeURIComponent(roomId)}/messages`,
        { method: "GET" },
      );
      return messages;
    },
    async sendMessage(roomId, content) {
      const { message } = await post<SendMessageResponse>(
        `/rooms/${encodeURIComponent(roomId)}/messages`,
        { content },
      );
      return message;
    },
    generateReport(roomId) {
      return post<GenerateReportResponse>(
        `/rooms/${encodeURIComponent(roomId)}/report`,
      );
    },
  };
}

/** Parse a JSON response body, tolerating an empty/invalid body. */
async function parseJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}
