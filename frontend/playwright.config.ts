import { defineConfig, devices } from "@playwright/test";

/**
 * DevTwin Playwright E2E Configuration
 *
 * Base URL: Assumes `npm run dev` is running on port 3000.
 * Set PLAYWRIGHT_BASE_URL env var to override.
 *
 * Credentials: Never stored here. Tests that need a dev token read from
 * the DEVTWIN_DEV_TOKEN environment variable only. Never commit .env with secrets.
 */
export default defineConfig({
  testDir: "./e2e",
  outputDir: "./e2e-results",
  fullyParallel: false, // Sequential: avoids port conflicts with a single dev server
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [
    ["list"],
    ["html", { outputFolder: "./e2e-report", open: "never" }],
  ],
  use: {
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "off",
    // Do not store credentials — use env vars in tests
    storageState: undefined,
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  // Dev server is expected to be running separately via `npm run dev`
  // webServer is intentionally NOT configured here to avoid auto-spawning
  // a second dev server that could conflict. Run `npm run dev` manually first.
});
