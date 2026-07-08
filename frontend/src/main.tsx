import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import type { ApiClient } from "./api/apiClient";
import { createBackendApiClient } from "./api/backend";
import { App } from "./App";
import "./index.css";
import { createMockFetch } from "./mock/mockBackend";

/**
 * Choose the apiClient for this run.
 *
 * - Production build (packaged Desktop_App, FastAPI serves the assets):
 *   no client is injected, so AppShell defaults to the real loopback backend.
 * - Local dev (`npm run dev`, import.meta.env.DEV): there is no real backend,
 *   so wire the client to the in-memory mock harness. This seeds one active
 *   room and lets the whole UI render with mock data instead of failing with
 *   the connection error.
 */
function resolveApiClient(): ApiClient | undefined {
  if (import.meta.env.DEV) {
    const fetchFn = createMockFetch({
      seedMessages: [
        "이번 주 결제 모듈 리팩터링 완료했습니다.",
        "신규 회원가입 플로우 QA 이슈 3건 수정.",
        "차주에는 알림 센터 API 연동 예정입니다.",
      ],
    });
    return createBackendApiClient({ fetchFn });
  }
  return undefined;
}

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Root element #root not found");
}

createRoot(rootElement).render(
  <StrictMode>
    <App apiClient={resolveApiClient()} />
  </StrictMode>,
);
