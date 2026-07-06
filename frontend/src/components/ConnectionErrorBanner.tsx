const DEFAULT_MESSAGE = "백엔드 연결을 사용할 수 없습니다.";

interface ConnectionErrorBannerProps {
  message?: string;
}

export function ConnectionErrorBanner({
  message = DEFAULT_MESSAGE,
}: ConnectionErrorBannerProps) {
  return (
    <div role="alert" className="connection-error-banner">
      {message}
    </div>
  );
}
