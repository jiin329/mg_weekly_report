import { useState } from "react";
import type { WeeklyReport } from "../types";

/**
 * ReportCard renders a generated Weekly_Report in its four-section format and
 * provides a copy-to-clipboard action.
 *
 * Requirements:
 * - 5.4: display the four sections (작성일, 금주 업무 실적, 차주 업무 계획, 이슈 및 건의사항)
 * - 5.5: provide a copy button
 * - 5.6: copy the report text to the clipboard and show a success notification
 */
export interface ReportCardProps {
  report: WeeklyReport;
}

// The four sections in display order, paired with their Korean labels.
const SECTIONS: { label: string; key: keyof WeeklyReport }[] = [
  { label: "작성일", key: "writtenDate" },
  { label: "금주 업무 실적", key: "achievements" },
  { label: "차주 업무 계획", key: "nextWeekPlan" },
  { label: "이슈 및 건의사항", key: "issues" },
];

/** Builds the plain-text form of the report used for clipboard copy. */
function formatReport(report: WeeklyReport): string {
  return SECTIONS.map(({ label, key }) => `[${label}]\n${report[key]}`).join(
    "\n\n",
  );
}

export function ReportCard({ report }: ReportCardProps) {
  const [copied, setCopied] = useState(false);

  async function handleCopy() {
    try {
      await navigator.clipboard.writeText(formatReport(report));
      setCopied(true);
    } catch {
      // Clipboard access can fail (e.g. denied permission). Keep the UI usable;
      // the user can still read and manually copy the report.
      setCopied(false);
    }
  }

  return (
    <section className="report-card" aria-label="주간보고">
      <header className="report-card__header">
        <h2 className="report-card__title">주간보고</h2>
        <button type="button" className="report-card__copy" onClick={handleCopy}>
          복사
        </button>
      </header>

      <dl className="report-card__sections">
        {SECTIONS.map(({ label, key }) => (
          <div className="report-card__section" key={key}>
            <dt className="report-card__label">{label}</dt>
            <dd className="report-card__value">{report[key]}</dd>
          </div>
        ))}
      </dl>

      {copied && (
        <p className="report-card__notice" role="status" aria-live="polite">
          보고서가 복사되었습니다.
        </p>
      )}
    </section>
  );
}
