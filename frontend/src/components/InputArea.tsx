import { useState, type KeyboardEvent } from "react";
import { isUserMessageContentValid } from "../types";

/**
 * InputArea renders the message input field + send button pinned at the bottom
 * of the Application_Window (Requirement 2.4).
 *
 * Behavior:
 * - Type and click "전송" or press Enter (without Shift) to send (Req 3.1).
 * - Shift+Enter inserts a newline instead of sending, and there is no length
 *   limit while the room is active (Req 3.2).
 * - Blank / whitespace-only content is never sent, and no error is shown
 *   (Req 3.3) — the send is silently ignored via isUserMessageContentValid.
 * - When `disabled` (the room is closed), both the input and the send button
 *   are disabled (Req 6.2 / 6.6).
 */
interface InputAreaProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSend, disabled = false }: InputAreaProps) {
  const [value, setValue] = useState("");

  function handleSend() {
    if (disabled) return;
    // Silently ignore blank/whitespace-only content (Req 3.3): no error shown.
    if (!isUserMessageContentValid(value)) return;
    onSend(value);
    setValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    // Enter sends; Shift+Enter inserts a newline (Req 3.1 / 3.2).
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSend();
    }
  }

  return (
    <div className="input-area">
      <textarea
        className="input-area__field"
        aria-label="메시지 입력"
        rows={2}
        value={value}
        disabled={disabled}
        onChange={(event) => setValue(event.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button
        type="button"
        className="input-area__send"
        onClick={handleSend}
        disabled={disabled}
      >
        전송
      </button>
    </div>
  );
}
