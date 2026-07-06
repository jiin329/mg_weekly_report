import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { GenerateButton } from "./GenerateButton";

// Tests for the GenerateButton component (task 3.7).
// Requirements:
// - 4.1: '주간보고 생성' button is shown only while the room is active.
// - 4.2: clicking (with messages) triggers the generation request via onGenerate.
// - 4.5: with no messages, generation is blocked and a notification is shown.
describe("GenerateButton", () => {
  it("renders nothing when the room is closed (Req 4.1)", () => {
    const onGenerate = vi.fn();
    const { container } = render(
      <GenerateButton roomStatus="closed" hasMessages={true} onGenerate={onGenerate} />,
    );

    expect(
      screen.queryByRole("button", { name: "주간보고 생성" }),
    ).not.toBeInTheDocument();
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the button when the room is active (Req 4.1)", () => {
    const onGenerate = vi.fn();
    render(
      <GenerateButton roomStatus="active" hasMessages={true} onGenerate={onGenerate} />,
    );

    expect(
      screen.getByRole("button", { name: "주간보고 생성" }),
    ).toBeInTheDocument();
  });

  it("blocks generation and shows a notification when there are no messages (Req 4.5)", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();
    render(
      <GenerateButton roomStatus="active" hasMessages={false} onGenerate={onGenerate} />,
    );

    await user.click(screen.getByRole("button", { name: "주간보고 생성" }));

    expect(onGenerate).not.toHaveBeenCalled();
    expect(screen.getByRole("alert")).toHaveTextContent(
      "메시지를 입력한 후 주간보고를 생성할 수 있습니다.",
    );
  });

  it("calls onGenerate when active and there are messages (Req 4.2)", async () => {
    const user = userEvent.setup();
    const onGenerate = vi.fn();
    render(
      <GenerateButton roomStatus="active" hasMessages={true} onGenerate={onGenerate} />,
    );

    await user.click(screen.getByRole("button", { name: "주간보고 생성" }));

    expect(onGenerate).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});
