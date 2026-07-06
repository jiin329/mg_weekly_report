import { AppShell } from "./components/AppShell";

/**
 * App is the root Frontend component rendered inside the pywebview
 * Application_Window (not a browser tab).
 *
 * It renders the AppShell, which composes the whole Chat_UI and wires it to the
 * apiClient. By default AppShell talks to the in-memory mock backend so the UI
 * runs standalone; the desktop integration task swaps in the real loopback
 * backend client.
 */
export function App() {
  return <AppShell />;
}
