/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// The React app is served to the pywebview Application_Window.
// `base: "./"` keeps asset paths relative so the built bundle can be loaded
// from the local filesystem / packaged app (Phase 2) as well as the dev server.
export default defineConfig({
  base: "./",
  plugins: [react()],
  build: {
    outDir: "dist",
  },
  server: {
    // Vite dev server port (Phase 1 dev only). The backend loopback port is
    // configured separately via BACKEND_PORT (see project root .env.example).
    port: 5173,
    strictPort: false,
  },
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: "./src/setupTests.ts",
    css: false,
  },
});
