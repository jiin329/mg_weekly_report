import type { ApiClient } from "./api/apiClient";
import { AppShell } from "./components/AppShell";

/**
 * App is the root Frontend component rendered inside the pywebview
 * Application_Window (not a browser tab).
 *
 * It renders the AppShell, which composes the whole Chat_UI and wires it to the
 * apiClient. By default AppShell talks to the real loopback backend over local
 * HTTP (task 8.2, Req 10.3). An apiClient can be injected for tests or FE-only
 * development, in which case a mock-backed client is passed through.
 */
export interface AppProps {
  apiClient?: ApiClient;
}

export function App({ apiClient }: AppProps = {}) {
  return <AppShell apiClient={apiClient} />;
}
