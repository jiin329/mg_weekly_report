import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { InputArea } from "./InputArea";

// Tests for the InputArea component (task 3.6).
// Covers Requirements 2.4 (input + send at bottom), 3.1 (send via button/Enter),
// 3.2 (unlimited input while active), 3.3 (block blank sends, no error),
// 6.2/6.6 (disabled when the room is closed).
describe("InputArea", () => {
  it("sends typed content when the send button is clicked (Req 3.1)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} />);

    await user.type(screen.getByRole("textbox"), "이번 주 실적입니다");
    await user.click(screen.getByRole("button", { name: "전송" }));

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("이번 주 실적입니다");
  });

  it("sends when Enter is pressed without Shift (Req 3.1)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} />);

    await user.type(screen.getByRole("textbox"), "엔터로 전송{Enter}");

    expect(onSend).toHaveBeenCalledTimes(1);
    expect(onSend).toHaveBeenCalledWith("엔터로 전송");
  });

  it("does not send on Shift+Enter, allowing a newline (Req 3.2)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} />);

    const input = screen.getByRole("textbox");
    await user.type(input, "첫 줄{Shift>}{Enter}{/Shift}둘째 줄");

    expect(onSend).not.toHaveBeenCalled();
  });

  it("clears the input after a successful send", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} />);

    const input = screen.getByRole("textbox") as HTMLTextAreaElement;
    await user.type(input, "지워질 내용");
    await user.click(screen.getByRole("button", { name: "전송" }));

    expect(input.value).toBe("");
  });

  it("does not send blank/whitespace content and shows no error (Req 3.3)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} />);

    // whitespace only
    await user.type(screen.getByRole("textbox"), "   ");
    await user.click(screen.getByRole("button", { name: "전송" }));
    // Enter on blank
    await user.type(screen.getByRole("textbox"), "{Enter}");

    expect(onSend).not.toHaveBeenCalled();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });

  it("disables the input and send button when disabled (Req 6.2/6.6)", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();
    render(<InputArea onSend={onSend} disabled />);

    const input = screen.getByRole("textbox");
    const button = screen.getByRole("button", { name: "전송" });

    expect(input).toBeDisabled();
    expect(button).toBeDisabled();

    await user.type(input, "닫힌 방");
    await user.click(button);
    expect(onSend).not.toHaveBeenCalled();
  });
});
