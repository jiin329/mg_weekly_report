import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { AppShell } from "./AppShell";
import { createApiClient } from "../api/apiClient";
import { createMockFetch } from "../mock/mockBackend";

// jsdom does not implement scrollIntoView, which MessageList calls on mount.
// Stub it so the composed tree renders without throwing.
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

// Build an AppShell wired to a fresh in-memory mock backend for each test, so
// the tests are deterministic and never touch the network. AppShell accepts an
// injectable apiClient exactly for this reason (integration swaps in the real
// one later).
function renderShell() {
  const apiClient = createApiClient({
    baseUrl: "http://127.0.0.1:8000",
    fetchFn: createMockFetch(),
  });
  return render(<AppShell apiClient={apiClient} />);
}

describe("AppShell", () => {
  it("renders the sidebar and main chat area after initial load (Req 7, 2.6)", async () => {
    renderShell();

    // Sidebar: the room list nav plus the app title.
    expect(
      await screen.findByRole("navigation", { name: "채팅방 목록" }),
    ).toBeInTheDocument();
    // Main area is present and the input field is available on the active room.
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(
      await screen.findByRole("textbox", { name: "메시지 입력" }),
    ).toBeEnabled();

    // The seeded active room is selected by default (Req 7.4).
    const nav = screen.getByRole("navigation", { name: "채팅방 목록" });
    expect(within(nav).getAllByRole("button")).toHaveLength(1);
  });

  it("shows a message after it is sent (Req 3.1)", async () => {
    const user = userEvent.setup();
    renderShell();

    const input = await screen.findByRole("textbox", { name: "메시지 입력" });
    await user.type(input, "이번 주 API 작업 완료");
    await user.click(screen.getByRole("button", { name: "전송" }));

    expect(
      await screen.findByText("이번 주 API 작업 완료"),
    ).toBeInTheDocument();
  });

  it("shows the report card and a new active room after generating (Req 5.4, 6.4)", async () => {
    const user = userEvent.setup();
    renderShell();

    const input = await screen.findByRole("textbox", { name: "메시지 입력" });
    await user.type(input, "주간 업무 내용");
    await user.click(screen.getByRole("button", { name: "전송" }));
    await screen.findByText("주간 업무 내용");

    await user.click(screen.getByRole("button", { name: "주간보고 생성" }));

    // The generated report is displayed (Req 5.4).
    expect(
      await screen.findByRole("heading", { name: "주간보고" }),
    ).toBeInTheDocument();

    // A new active room now appears alongside the closed room (Req 6.4):
    // two rooms in the sidebar.
    const nav = screen.getByRole("navigation", { name: "채팅방 목록" });
    expect(within(nav).getAllByRole("button")).toHaveLength(2);
  });
});
