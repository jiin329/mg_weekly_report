import { describe, expect, it } from "vitest";
import type { ListRoomsResponse } from "../types/api";
import { createMockFetch } from "./mockBackend";

// Direct tests of the mock harness invariants that the apiClient tests do not
// cover on their own (task 3.1).

describe("mock backend invariants", () => {
  it("seeds exactly one active room on creation", async () => {
    const mockFetch = createMockFetch();
    const resp = await mockFetch("http://mock/rooms", { method: "GET" });
    const body = (await resp.json()) as ListRoomsResponse;
    expect(body.rooms.filter((r) => r.status === "active")).toHaveLength(1);
  });

  it("POST /rooms never yields more than one active room", async () => {
    const mockFetch = createMockFetch();
    await mockFetch("http://mock/rooms", { method: "POST" });
    await mockFetch("http://mock/rooms", { method: "POST" });

    const resp = await mockFetch("http://mock/rooms", { method: "GET" });
    const body = (await resp.json()) as ListRoomsResponse;
    expect(body.rooms.filter((r) => r.status === "active")).toHaveLength(1);
  });

  it("returns a structured error body for unknown routes", async () => {
    const mockFetch = createMockFetch();
    const resp = await mockFetch("http://mock/unknown", { method: "GET" });
    expect(resp.ok).toBe(false);
    const body = (await resp.json()) as { error?: { code?: string; message?: string } };
    expect(body.error?.code).toBeTruthy();
    expect(body.error?.message).toBeTruthy();
  });
});
