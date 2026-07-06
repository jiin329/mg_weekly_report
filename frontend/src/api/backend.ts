/**
 * Real loopback backend wiring (task 8.2 — [INTEGRATION] FE를 실제 BE에 연결).
 *
 * During FE-only development the UI runs against the in-memory mock backend
 * harness (mock/mockBackend.ts). For the packaged Desktop_App the very same
 * apiClient talks to the REAL FastAPI backend over the local loopback interface
 * (Req 10.3) — no external network other than the LLM API.
 *
 * This module resolves the base URL for that real backend and builds a client
 * pointed at it. Because the built React assets can reach the pywebview window
 * in two ways (design.md "데스크톱 셸"), the resolver handles both:
 *   1. served by FastAPI over http  -> talk to the SAME origin (127.0.0.1:PORT),
 *      so whatever port the backend actually bound is used automatically.
 *   2. loaded from the local filesystem (file://) -> fall back to the known
 *      loopback default `http://127.0.0.1:{PORT}`.
 *
 * The client itself is unchanged: it already parses structured error bodies and
 * raises CONNECTION_ERROR when the backend is unreachable, which the AppShell
 * turns into the ConnectionErrorBanner (Req 10.9).
 */

import { createApiClient, type ApiClient, type FetchFn } from "./apiClient";

/**
 * Default local loopback port. Mirrors the backend's DEFAULT_BACKEND_PORT
 * (backend/app/config.py) and BACKEND_PORT in .env.example.
 */
export const DEFAULT_BACKEND_PORT = 8756;

/** Minimal shape of `window.location` this resolver depends on. */
export interface LocationLike {
  protocol: string;
  origin: string;
}

/**
 * Resolve the base URL of the real loopback backend.
 *
 * When the page is served over http(s) (FastAPI serving the built assets), the
 * backend lives at the same origin, so we reuse it verbatim — this makes the
 * frontend agnostic to whichever port the backend bound. When the page is
 * loaded from the filesystem (file://, packaged app), there is no useful
 * origin, so we fall back to the known loopback host/port.
 */
export function resolveBackendBaseUrl(
  location: LocationLike = window.location,
  fallbackPort: number = DEFAULT_BACKEND_PORT,
): string {
  if (location.protocol === "http:" || location.protocol === "https:") {
    return location.origin;
  }
  return `http://127.0.0.1:${fallbackPort}`;
}

export interface BackendApiClientOptions {
  /** Override the resolved base URL (defaults to resolveBackendBaseUrl()). */
  baseUrl?: string;
  /** Override the fetch implementation (defaults to the global `fetch`). */
  fetchFn?: FetchFn;
}

/**
 * Build an apiClient pointed at the real loopback backend. Uses the global
 * `fetch` so requests go over the local HTTP interface; failures surface as
 * ApiError / CONNECTION_ERROR exactly as with the mock harness.
 */
export function createBackendApiClient(
  options: BackendApiClientOptions = {},
): ApiClient {
  const { baseUrl = resolveBackendBaseUrl(), fetchFn } = options;
  return createApiClient({ baseUrl, fetchFn });
}
