import { render } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import fc from "fast-check";
import { MessageBubble } from "./MessageBubble";
import type { Message } from "../types";

// Feature: weekly-report-chat, Property 5: 렌더된 메시지는 항상 타임스탬프를 포함한다
//
// Property 5: For any valid message, the Chat_UI rendered output must include
// that message's timestamp.
// Validates: Requirements 2.3 (THE Chat_UI SHALL display a timestamp next to
// each Message).

/**
 * Generates arbitrary valid messages matching the Message data model:
 * { id, roomId, sender: 'user' | 'system', content, createdAt (ISO 8601) }.
 * `createdAt` is derived from an arbitrary Date so it is always a valid ISO
 * 8601 string.
 */
const messageArb: fc.Arbitrary<Message> = fc.record({
  id: fc.uuid(),
  roomId: fc.uuid(),
  sender: fc.constantFrom<"user" | "system">("user", "system"),
  content: fc.string(),
  createdAt: fc
    .date({
      min: new Date("2000-01-01T00:00:00.000Z"),
      max: new Date("2100-01-01T00:00:00.000Z"),
    })
    .map((d) => d.toISOString()),
});

describe("MessageBubble timestamp property", () => {
  it("always renders the message's timestamp (Req 2.3)", () => {
    fc.assert(
      fc.property(messageArb, (message) => {
        const { container, unmount } = render(
          <MessageBubble message={message} />,
        );
        try {
          const time = container.querySelector("time");
          // The rendered output must include a timestamp for the message.
          expect(time).not.toBeNull();
          // The timestamp carries the message's ISO createdAt value...
          expect(time?.getAttribute("datetime")).toBe(message.createdAt);
          // ...and shows a non-empty human-readable representation.
          expect((time?.textContent ?? "").trim().length).toBeGreaterThan(0);
        } finally {
          unmount();
        }
      }),
    );
  });
});
