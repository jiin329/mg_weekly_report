import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import type { ChatRoom, Message, WeeklyReport } from "../types";
import { AppShell } from "./AppShell";
import { ConnectionErrorBanner } from "./ConnectionErrorBanner";
import { InputArea } from "./InputArea";
import { LoadingIndicator } from "./LoadingIndicator";
import { MessageBubble } from "./MessageBubble";
import { MessageList } from "./MessageList";
import { ReportCard } from "./ReportCard";
import { RoomList } from "./RoomList";
import { createApiClient } from "../api/apiClient";
import { createMockFetch } from "../mock/mockBackend";

/**
 * Task 3.11 — consolidated UI example/snapshot suite.
 *
 * The individual component test files already assert behavior (clicks, sends,
 * disabled states, etc.). This suite complements them with:
 *
 * 1. Snapshot baselines that lock the rendered structure of each Chat_UI
 *    surface referenced by the task, so unintended markup/alignment/color
 *    changes are caught: message bubbles (2.1, 2.2), input area (2.4),
 *    message list / auto-scroll sentinel (2.5), room list (7.1–7.4),
 *    loading indicator (4.4), report card + copy (5.4–5.6),
 *    connection error banner (10.9).
 *
 * 2. An AppShell-level example for the read-only closed-room view (6.5) and
 *    the new active room appearing alongside it (6.4) / disabled input (6.2),
 *    which is the one flow not pinned by an existing test.
 *
 * jsdom does not implement scrollIntoView (MessageList calls it on mount), so
 * it is stubbed for every test here.
 */
beforeEach(() => {
  Element.prototype.scrollIntoView = vi.fn();
});

const FIXED_TS = "2024-06-03T09:30:00.000Z";

function userMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "m-user",
    roomId: "r1",
    sender: "user",
    content: "이번 주 결제 모듈 리팩터링을 완료했습니다.",
    createdAt: FIXED_TS,
    ...overrides,
  };
}

function systemMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "m-system",
    roomId: "r1",
    sender: "system",
    content: "생성된 주간보고입니다.",
    createdAt: FIXED_TS,
    ...overrides,
  };
}

const sampleReport: WeeklyReport = {
  writtenDate: "2025-06-13",
  achievements: "결제 모듈 리팩터링 완료",
  nextWeekPlan: "알림 서비스 설계 착수",
  issues: "테스트 환경 리소스 부족",
};

function activeRoom(id: string, createdAt: string): ChatRoom {
  return { id, status: "active", createdAt, closedAt: null, report: null };
}

function closedRoom(id: string, createdAt: string): ChatRoom {
  return {
    id,
    status: "closed",
    createdAt,
    closedAt: createdAt,
    report: sampleReport,
  };
}

describe("Chat_UI snapshots", () => {
  it("MessageBubble — user vs system alignment/color (Req 2.1, 2.2)", () => {
    const { container } = render(
      <>
        <MessageBubble message={userMessage()} />
        <MessageBubble message={systemMessage()} />
      </>,
    );
    expect(container).toMatchSnapshot();
  });

  it("MessageList — messages with the auto-scroll sentinel (Req 2.5)", () => {
    const { container } = render(
      <MessageList
        messages={[
          userMessage({ id: "m1", content: "첫 번째" }),
          userMessage({ id: "m2", content: "두 번째" }),
        ]}
        renderMessage={(m) => <MessageBubble key={m.id} message={m} />}
      />,
    );
    expect(container).toMatchSnapshot();
  });

  it("InputArea — active vs closed/disabled (Req 2.4, 6.2)", () => {
    const active = render(<InputArea onSend={() => {}} />);
    expect(active.container).toMatchSnapshot("active");

    const closed = render(<InputArea onSend={() => {}} disabled />);
    expect(closed.container).toMatchSnapshot("disabled");
  });

  it("RoomList — active/closed distinction and selection (Req 7.1–7.4)", () => {
    const rooms = [
      activeRoom("r-active", "2024-03-11T09:00:00Z"),
      closedRoom("r-closed", "2024-03-04T09:00:00Z"),
    ];
    const { container } = render(
      <RoomList
        rooms={rooms}
        selectedRoomId="r-active"
        onSelectRoom={() => {}}
      />,
    );
    expect(container).toMatchSnapshot();
  });

  it("LoadingIndicator — report generation wait (Req 4.4)", () => {
    const { container } = render(<LoadingIndicator />);
    expect(container).toMatchSnapshot();
  });

  it("ReportCard — four sections and copy button (Req 5.4, 5.5)", () => {
    const { container } = render(<ReportCard report={sampleReport} />);
    expect(container).toMatchSnapshot();
  });

  it("ConnectionErrorBanner — backend unreachable (Req 10.9)", () => {
    const { container } = render(<ConnectionErrorBanner />);
    expect(container).toMatchSnapshot();
  });
});

// Renders AppShell wired to a fresh in-memory mock backend (same pattern as
// AppShell.test.tsx) so the closed-room flow is exercised end-to-end.
function renderShell() {
  const apiClient = createApiClient({
    baseUrl: "http://127.0.0.1:8000",
    fetchFn: createMockFetch(),
  });
  return render(<AppShell apiClient={apiClient} />);
}

describe("Closed room is read-only (Req 6.5)", () => {
  it("shows the generated report and disables input for the closed room, with a new active room in the list (Req 6.2, 6.4, 6.5)", async () => {
    const user = userEvent.setup();
    renderShell();

    const input = await screen.findByRole("textbox", { name: "메시지 입력" });
    await user.type(input, "주간 업무 내용");
    await user.click(screen.getByRole("button", { name: "전송" }));
    await screen.findByText("주간 업무 내용");

    await user.click(screen.getByRole("button", { name: "주간보고 생성" }));

    // After generation AppShell selects the now-closed room: its report is
    // displayed (read-only view, Req 6.5).
    expect(
      await screen.findByRole("heading", { name: "주간보고" }),
    ).toBeInTheDocument();

    // The closed room's input and send button are disabled (Req 6.2 / read-only 6.5).
    expect(screen.getByRole("textbox", { name: "메시지 입력" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "전송" })).toBeDisabled();

    // The '주간보고 생성' button is not offered for the closed room.
    expect(
      screen.queryByRole("button", { name: "주간보고 생성" }),
    ).not.toBeInTheDocument();

    // A new active room now appears alongside the closed one (Req 6.4).
    const nav = screen.getByRole("navigation", { name: "채팅방 목록" });
    expect(within(nav).getAllByRole("button")).toHaveLength(2);
  });
});
