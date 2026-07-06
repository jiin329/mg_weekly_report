import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { createApiClient } from "./api/apiClient";
import { createMockFetch } from "./mock/mockBackend";

// jsdom does not implement scrollIntoView (used by MessageList on mount).
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Smoke test: App renders the AppShell, which composes the whole Chat_UI.
// App now defaults to the real loopback backend (task 8.2), so we inject a
// mock-backed client to keep this a standalone, network-free smoke test.
describe("App", () => {
  it("renders the AppShell with the app title and room list", async () => {
    const apiClient = createApiClient({
      baseUrl: "http://mock",
      fetchFn: createMockFetch(),
    });
    render(<App apiClient={apiClient} />);

    expect(
      screen.getByRole("heading", { name: "주간보고 채팅" }),
    ).toBeInTheDocument();
    // The room list appears once the initial (mock) load resolves.
    expect(
      await screen.findByRole("navigation", { name: "채팅방 목록" }),
    ).toBeInTheDocument();
  });
});
