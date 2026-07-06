import { useState, type KeyboardEvent } from "react";
import { isUserMessageContentValid } from "../types";

interface InputAreaProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export function InputArea({ onSend, disabled = false }: InputAreaProps) {
  const [value, setValue] = useState("");

  function handleSend() {
    if (disabled) return;
    if (!isUserMessageContentValid(value)) return;
    onSend(value);
    setValue("");
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
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
        placeholder={disabled ? "완료된 주간보고입니다." : "이번 주 업무를 입력하세요."}
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
