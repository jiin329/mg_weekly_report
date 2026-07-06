import type { Message } from "../types";
import "./MessageBubble.css";

/**
 * MessageBubble renders a single chat message (Requirements 2.1–2.3).
 *
 * - User messages are right-aligned with a distinct background
 *   (`bubble bubble--user`). (Req 2.1)
 * - System messages (generated reports, etc.) are left-aligned with a
 *   different background (`bubble bubble--system`). (Req 2.2)
 * - Every message shows a human-readable local timestamp derived from the
 *   ISO `createdAt`. (Req 2.3)
 */
export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.sender === "user";

  return (
    <div
      className={`bubble-row ${isUser ? "bubble-row--user" : "bubble-row--system"}`}
    >
      <div className={`bubble ${isUser ? "bubble--user" : "bubble--system"}`}>
        <p className="bubble__content">{message.content}</p>
        <time className="bubble__time" dateTime={message.createdAt}>
          {formatTimestamp(message.createdAt)}
        </time>
      </div>
    </div>
  );
}

/**
 * Formats an ISO 8601 timestamp into a readable local time string.
 * Falls back to the raw value if the date cannot be parsed, so the timestamp
 * text is always present in the DOM (Req 2.3).
 */
function formatTimestamp(createdAt: string): string {
  const date = new Date(createdAt);
  if (Number.isNaN(date.getTime())) {
    return createdAt;
  }
  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  }).format(date);
}
