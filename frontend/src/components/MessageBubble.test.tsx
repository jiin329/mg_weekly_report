import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../types";

// Example/edge tests for MessageBubble rendering (Requirements 2.1, 2.2, 2.3).
// - user message: right-aligned, distinct background (bubble--user)
// - system message: left-aligned, different background (bubble--system)
// - every rendered message shows a human-readable timestamp

function makeMessage(overrides: Partial<Message> = {}): Message {
  return {
    id: "m1",
    roomId: "r1",
    sender: "user",
    content: "이번 주 업무 보고입니다",
    createdAt: "2024-06-03T09:30:00.000Z",
    ...overrides,
  };
}

describe("MessageBubble", () => {
  it("renders a user message with the user bubble class (Req 2.1)", () => {
    render(<MessageBubble message={makeMessage({ sender: "user" })} />);
    const bubble = screen.getByText("이번 주 업무 보고입니다").closest(".bubble");
    expect(bubble).not.toBeNull();
    expect(bubble).toHaveClass("bubble--user");
    expect(bubble).not.toHaveClass("bubble--system");
  });

  it("renders a system message with the system bubble class (Req 2.2)", () => {
    render(
      <MessageBubble
        message={makeMessage({ sender: "system", content: "생성된 보고서" })}
      />,
    );
    const bubble = screen.getByText("생성된 보고서").closest(".bubble");
    expect(bubble).not.toBeNull();
    expect(bubble).toHaveClass("bubble--system");
    expect(bubble).not.toHaveClass("bubble--user");
  });

  it("gives user and system messages different alignment classes (Req 2.1, 2.2)", () => {
    const { rerender } = render(
      <MessageBubble message={makeMessage({ sender: "user" })} />,
    );
    const userClass = screen
      .getByText("이번 주 업무 보고입니다")
      .closest(".bubble")?.className;

    rerender(
      <MessageBubble
        message={makeMessage({ sender: "system", content: "시스템 메시지" })}
      />,
    );
    const systemClass = screen
      .getByText("시스템 메시지")
      .closest(".bubble")?.className;

    expect(userClass).not.toEqual(systemClass);
  });

  it("renders a human-readable timestamp for each message (Req 2.3)", () => {
    render(<MessageBubble message={makeMessage()} />);
    const time = screen.getByText(
      (_, el) => el?.tagName.toLowerCase() === "time",
    );
    expect(time).toBeInTheDocument();
    // The timestamp text must be non-empty and carry the ISO value.
    expect(time.textContent?.trim().length ?? 0).toBeGreaterThan(0);
    expect(time).toHaveAttribute("dateTime", "2024-06-03T09:30:00.000Z");
  });
});
