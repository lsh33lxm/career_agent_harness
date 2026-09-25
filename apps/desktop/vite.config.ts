import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    host: "127.0.0.1",
    port: 5173,
    strictPort: true,
  },
  test: {
    exclude: ["**/e2e/**", "**/node_modules/**", "**/dist/**"],
    // Page tests stub the shared browser fetch and API modules; run files
    // sequentially so one jsdom fixture cannot leak into another file.
    fileParallelism: false,
  },
  clearScreen: false,
});
