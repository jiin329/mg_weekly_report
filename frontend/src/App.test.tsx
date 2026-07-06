import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

// jsdom does not implement scrollIntoView (used by MessageList on mount).
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Smoke test: App renders the AppShell, which composes the whole Chat_UI.
// AppShell uses the in-memory mock backend by default, so this runs standalone.
describe("App", () => {
  it("renders the AppShell with the app title and room list", async () => {
    render(<App />);

    expect(
      screen.getByRole("heading", { name: "주간보고 채팅" }),
    ).toBeInTheDocument();
    // The room list appears once the initial (mock) load resolves.
    expect(
      await screen.findByRole("navigation", { name: "채팅방 목록" }),
    ).toBeInTheDocument();
  });
});
