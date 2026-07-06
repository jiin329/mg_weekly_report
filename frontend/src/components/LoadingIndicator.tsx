/**
 * LoadingIndicator shows a loading state while a Weekly_Report is being
 * generated (Requirement 4.4).
 *
 * Kept intentionally minimal: a status region with an accessible live message
 * so screen readers announce that generation is in progress.
 */
export interface LoadingIndicatorProps {
  /** Optional message to display. Defaults to the report-generation message. */
  label?: string;
}

export function LoadingIndicator({
  label = "주간보고를 생성하고 있습니다...",
}: LoadingIndicatorProps) {
  return (
    <div className="loading-indicator" role="status" aria-live="polite">
      <span className="loading-indicator__spinner" aria-hidden="true" />
      <span className="loading-indicator__label">{label}</span>
    </div>
  );
}
