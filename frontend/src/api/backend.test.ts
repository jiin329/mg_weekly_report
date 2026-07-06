import { describe, expect, it } from "vitest";
import { ApiError, CONNECTION_ERROR } from "./apiClient";
import {
    DEFAULT_BACKEND_PORT,
    createBackendApiClient,
    resolveBackendBaseUrl,
} from "./backend";

// Task 8.2: the Frontend talks to the REAL loopback backend at
// http://127.0.0.1:{PORT} (Req 10.3). These tests pin down how the base URL is
// resolved for the two ways the built assets are loaded into the pywebview
// window (design.md "데스크톱 셸"):
//   1. served by FastAPI over http  -> same-origin (127.0.0.1:PORT)
//   2. loaded from the local filesystem (file://) -> fall back to 127.0.0.1:PORT

describe("resolveBackendBaseUrl", () => {
  it("uses the same origin when the page is served over http (loopback)", () => {
    const location = {
      protocol: "http:",
      origin: "http://127.0.0.1:8756",
    };
    expect(resolveBackendBaseUrl(location)).toBe("http://127.0.0.1:8756");
  });

  it("uses the same origin when served over https", () => {
    const location = {
      protocol: "https:",
      origin: "https://127.0.0.1:9000",
    };
    expect(resolveBackendBaseUrl(location)).toBe("https://127.0.0.1:9000");
  });

  it("falls back to the loopback default port when loaded from file://", () => {
    const location = { protocol: "file:", origin: "null" };
    expect(resolveBackendBaseUrl(location)).toBe(
      `http://127.0.0.1:${DEFAULT_BACKEND_PORT}`,
    );
  });

  it("honors an explicit fallback port for the file:// case", () => {
    const location = { protocol: "file:", origin: "null" };
    expect(resolveBackendBaseUrl(location, 9123)).toBe(
      "http://127.0.0.1:9123",
    );
  });

  it("defaults the loopback port to 8756", () => {
    expect(DEFAULT_BACKEND_PORT).toBe(8756);
  });
});

describe("createBackendApiClient", () => {
  it("builds a client that surfaces a connection error when the backend is down", async () => {
    // Inject a failing fetch to prove the real-backend client still funnels
    // failures through ApiError / CONNECTION_ERROR so the ConnectionErrorBanner
    // path works (Req 10.9), without touching the real network.
    const client = createBackendApiClient({
      baseUrl: "http://127.0.0.1:8756",
      fetchFn: () => Promise.reject(new TypeError("Failed to fetch")),
    });
    const err = await client.listRooms().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe(CONNECTION_ERROR);
    expect(err.httpStatus).toBeNull();
  });
});
