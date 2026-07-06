import { useState } from "react";
import type { RoomStatus } from "../types";

interface GenerateButtonProps {
  roomStatus: RoomStatus;
  hasMessages: boolean;
  onGenerate: () => void;
}

const NO_MESSAGES_NOTICE =
  "메시지를 입력한 후 주간보고를 생성할 수 있습니다.";

export function GenerateButton({
  roomStatus,
  hasMessages,
  onGenerate,
}: GenerateButtonProps) {
  const [showNotice, setShowNotice] = useState(false);

  if (roomStatus !== "active") {
    return null;
  }

  function handleClick() {
    if (!hasMessages) {
      setShowNotice(true);
      return;
    }
    setShowNotice(false);
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
