import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { ReportCard } from "./ReportCard";
import type { WeeklyReport } from "../types";

const sampleReport: WeeklyReport = {
  writtenDate: "2025-06-13",
  achievements: "결제 모듈 리팩터링 완료",
  nextWeekPlan: "알림 서비스 설계 착수",
  issues: "테스트 환경 리소스 부족",
};

describe("ReportCard", () => {
  let writeText: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    writeText = vi.fn().mockResolvedValue(undefined);
    // jsdom's navigator.clipboard is a getter-only property, so define it
    // explicitly rather than assigning. fireEvent (not userEvent) is used for
    // clicks so this mock is not replaced by userEvent's clipboard stub.
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: { writeText },
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders all four report sections with labels and values", () => {
    render(<ReportCard report={sampleReport} />);

    // Section labels (Req 5.4)
    expect(screen.getByText("작성일")).toBeInTheDocument();
    expect(screen.getByText("금주 업무 실적")).toBeInTheDocument();
    expect(screen.getByText("차주 업무 계획")).toBeInTheDocument();
    expect(screen.getByText("이슈 및 건의사항")).toBeInTheDocument();

    // Section values
    expect(screen.getByText("2025-06-13")).toBeInTheDocument();
    expect(screen.getByText("결제 모듈 리팩터링 완료")).toBeInTheDocument();
    expect(screen.getByText("알림 서비스 설계 착수")).toBeInTheDocument();
    expect(screen.getByText("테스트 환경 리소스 부족")).toBeInTheDocument();
  });

  it("copies the formatted report text to the clipboard when copy is clicked (Req 5.5, 5.6)", async () => {
    render(<ReportCard report={sampleReport} />);

    fireEvent.click(screen.getByRole("button", { name: /복사/ }));

    await waitFor(() => expect(writeText).toHaveBeenCalledTimes(1));
    const copiedText = writeText.mock.calls[0][0] as string;
    // Formatted text should include every section value.
    expect(copiedText).toContain("2025-06-13");
    expect(copiedText).toContain("결제 모듈 리팩터링 완료");
    expect(copiedText).toContain("알림 서비스 설계 착수");
    expect(copiedText).toContain("테스트 환경 리소스 부족");
  });

  it("shows a success notification after copying (Req 5.6)", async () => {
    render(<ReportCard report={sampleReport} />);

    fireEvent.click(screen.getByRole("button", { name: /복사/ }));

    await waitFor(() => {
      expect(screen.getByRole("status")).toHaveTextContent(/복사/);
    });
  });
});
