export interface LoadingIndicatorProps {
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
