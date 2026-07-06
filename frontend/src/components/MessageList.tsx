import { useEffect, useRef } from "react";
import type { Message } from "../types";

interface MessageListProps {
  messages: Message[];
  /**
   * Optional custom renderer for a single message. When omitted, a minimal
   * default (the message content in a div) is rendered. The MessageBubble
   * component is wired in by its owning task via this prop.
   */
  renderMessage?: (message: Message) => React.ReactNode;
}

/**
 * MessageList is the scrollable message area of the Chat_UI.
 *
 * Requirement 2.5: when a new message is added, the list auto-scrolls to the
 * latest message. We keep a ref to a bottom sentinel element and scroll it into
 * view whenever the number of messages changes.
 */
export function MessageList({ messages, renderMessage }: MessageListProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  return (
    <div className="message-list">
      {messages.map((message) =>
        renderMessage ? (
          renderMessage(message)
        ) : (
          <div key={message.id} data-message-id={message.id}>
            {message.content}
          </div>
        ),
      )}
      <div ref={bottomRef} data-testid="message-list-bottom" />
    </div>
  );
}
