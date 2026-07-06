/**
 * ConnectionErrorBanner shows a prominent error banner inside the
 * Application_Window when the Backend is unreachable (Req 10.9).
 *
 * This component is purely presentational: the parent decides when the Backend
 * is unavailable (see apiClient CONNECTION_ERROR / ApiError) and mounts this
 * banner. A custom message can surface which component failed to start
 * (Req 11.6). No polling or timers live here.
 */

const DEFAULT_MESSAGE = "백엔드 연결을 사용할 수 없습니다.";

interface ConnectionErrorBannerProps {
  /** Optional override describing which component failed (Req 11.6). */
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
