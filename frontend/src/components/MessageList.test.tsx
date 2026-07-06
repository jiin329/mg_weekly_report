import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Message } from "../types";
import { MessageList } from "./MessageList";

// jsdom does not implement layout or scrollIntoView, so we spy on it and assert
// the auto-scroll behavior (Requirement 2.5) invokes it when messages change.
function makeMessage(id: string, content: string): Message {
  return {
    id,
    roomId: "room-1",
    sender: "user",
    content,
    createdAt: new Date().toISOString(),
  };
}

describe("MessageList", () => {
  beforeEach(() => {
    Element.prototype.scrollIntoView = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders each message by content with a data-message-id", () => {
    const messages = [makeMessage("m1", "첫 번째"), makeMessage("m2", "두 번째")];
    const { container } = render(<MessageList messages={messages} />);

    expect(screen.getByText("첫 번째")).toBeInTheDocument();
    expect(screen.getByText("두 번째")).toBeInTheDocument();
    expect(container.querySelectorAll("[data-message-id]").length).toBe(2);
  });

  it("uses renderMessage when provided", () => {
    const messages = [makeMessage("m1", "hi")];
    render(
      <MessageList
        messages={messages}
        renderMessage={(m) => <div key={m.id}>custom:{m.content}</div>}
      />,
    );

    expect(screen.getByText("custom:hi")).toBeInTheDocument();
  });

  it("auto-scrolls to the latest message on initial render", () => {
    const messages = [makeMessage("m1", "hello")];
    render(<MessageList messages={messages} />);

    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });

  it("auto-scrolls to the latest message when a new message is added", () => {
    const messages = [makeMessage("m1", "hello")];
    const { rerender } = render(<MessageList messages={messages} />);

    (Element.prototype.scrollIntoView as ReturnType<typeof vi.fn>).mockClear();

    const updated = [...messages, makeMessage("m2", "world")];
    rerender(<MessageList messages={updated} />);

    expect(Element.prototype.scrollIntoView).toHaveBeenCalled();
  });
});
