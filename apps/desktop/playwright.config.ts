import { defineConfig } from "@playwright/test";

const port = process.env.ACH_VERIFY_WEB_PORT ?? "5174";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.spec.ts",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 12_000 },
  outputDir: process.env.ACH_VERIFY_PLAYWRIGHT_OUTPUT_DIR ?? "../../artifacts/verification/playwright-output",
  reporter: "list",
  use: {
    baseURL: `http://127.0.0.1:${port}`,
    browserName: "chromium",
    headless: true,
    launchOptions: process.env.ACH_VERIFY_CHROMIUM_PATH
      ? { executablePath: process.env.ACH_VERIFY_CHROMIUM_PATH }
      : {},
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
});
