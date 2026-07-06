import { useState } from "react";
import type { WeeklyReport } from "../types";

export interface ReportCardProps {
  report: WeeklyReport;
}

const SECTIONS: { label: string; key: keyof WeeklyReport }[] = [
  { label: "작성일", key: "writtenDate" },
  { label: "금주 업무 실적", key: "achievements" },
  { label: "차주 업무 계획", key: "nextWeekPlan" },
  { label: "이슈 및 건의사항", key: "issues" },
];

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
      setCopied(false);
    }
  }

  return (
    <section className="report-card" aria-label="주간보고">
      <header className="report-card__header">
        <div>
          <p className="report-card__eyebrow">생성된 결과</p>
          <h2 className="report-card__title">주간보고</h2>
        </div>
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
