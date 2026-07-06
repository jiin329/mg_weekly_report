import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { ConnectionErrorBanner } from "./ConnectionErrorBanner";

describe("ConnectionErrorBanner", () => {
  it("renders a default message inside an alert region (Req 10.9)", () => {
    render(<ConnectionErrorBanner />);

    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert).toHaveTextContent("백엔드 연결을 사용할 수 없습니다.");
  });

  it("renders a custom message when provided (Req 11.6)", () => {
    render(<ConnectionErrorBanner message="LLM 서비스를 시작할 수 없습니다." />);

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("LLM 서비스를 시작할 수 없습니다.");
    expect(alert).not.toHaveTextContent("백엔드 연결을 사용할 수 없습니다.");
  });
});
