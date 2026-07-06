import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { LoadingIndicator } from "./LoadingIndicator";

describe("LoadingIndicator", () => {
  it("renders a discoverable status region (Req 4.4)", () => {
    render(<LoadingIndicator />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows a default loading label", () => {
    render(<LoadingIndicator />);
    expect(screen.getByRole("status")).toHaveTextContent("주간보고를 생성하고 있습니다");
  });

  it("shows a custom label when provided", () => {
    render(<LoadingIndicator label="불러오는 중" />);
    expect(screen.getByRole("status")).toHaveTextContent("불러오는 중");
  });
});
