import { useState } from "react";
import type { RoomStatus } from "../types";

interface GenerateButtonProps {
  /** Status of the current room. The button only appears while 'active'. */
  roomStatus: RoomStatus;
  /** Whether the room has at least one message. Generation is blocked if false. */
  hasMessages: boolean;
  /** Called when generation is requested (active room with messages). */
  onGenerate: () => void;
}

const NO_MESSAGES_NOTICE = "메시지를 입력한 후 주간보고를 생성할 수 있습니다.";

/**
 * GenerateButton renders the '주간보고 생성' action (task 3.7).
 *
 * - Requirement 4.1: only rendered while the room is active. A closed room
 *   renders nothing.
 * - Requirement 4.5: if the room has no messages, clicking does NOT trigger
 *   generation. Instead an inline notification tells the user messages are
 *   required.
 * - Requirement 4.2: when active and there are messages, clicking calls
 *   onGenerate so the parent can send the report generation request.
 */
export function GenerateButton({
  roomStatus,
  hasMessages,
  onGenerate,
}: GenerateButtonProps) {
  const [showNotice, setShowNotice] = useState(false);

  // Requirement 4.1: no button for a closed room.
  if (roomStatus !== "active") {
    return null;
  }

  function handleClick() {
    if (!hasMessages) {
      // Requirement 4.5: block generation and notify the user.
      setShowNotice(true);
      return;
    }
    setShowNotice(false);
    // Requirement 4.2: request report generation (wired by the parent).
    onGenerate();
  }

  return (
    <div className="generate-button">
      <button type="button" onClick={handleClick}>
        주간보고 생성
      </button>
      {showNotice && <p role="alert">{NO_MESSAGES_NOTICE}</p>}
    </div>
  );
}
