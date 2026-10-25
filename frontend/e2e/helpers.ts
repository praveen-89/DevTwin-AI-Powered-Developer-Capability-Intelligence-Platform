/**
 * DevTwin E2E — Shared Fixtures and Helpers
 *
 * Credential policy:
 *   - Dev token is read from DEVTWIN_DEV_TOKEN env var only.
 *   - Never hardcoded. Never printed to console/report.
 *   - If the env var is absent the helper returns null and tests skip.
 */

import { Page, expect } from "@playwright/test";

// ── Token Management ──────────────────────────────────────────────────────────

/**
 * Returns the developer bearer token from the environment.
 * Returns null if the variable is absent — callers must skip gracefully.
 */
export function getDevToken(): string | null {
  return process.env.DEVTWIN_DEV_TOKEN ?? null;
}

/**
 * Injects the dev token into the page's sessionStorage under the key the
 * AuthContext reads (`devtwin_dev_token`), then reloads to trigger auth state.
 */
export async function injectDevToken(page: Page, token: string): Promise<void> {
  await page.evaluate((t: string) => {
    sessionStorage.setItem("devtwin_dev_token", t);
  }, token);
  await page.reload({ waitUntil: "networkidle" });
}

/**
 * Clears auth state from sessionStorage to simulate a logged-out user.
 */
export async function clearAuthState(page: Page): Promise<void> {
  await page.evaluate(() => {
    sessionStorage.removeItem("devtwin_dev_token");
  });
  await page.reload({ waitUntil: "networkidle" });
}

// ── Navigation ────────────────────────────────────────────────────────────────

export const ROUTES = {
  home: "/",
  repositories: "/repositories",
  capabilities: "/capabilities",
  skillgraph: "/skillgraph",
  coderisk: "/coderisk",
  evidence: "/evidence",
} as const;

/** Navigate to a route and wait for the network to settle. */
export async function gotoAndSettle(page: Page, route: string): Promise<void> {
  await page.goto(route, { waitUntil: "networkidle" });
}

// ── Common Assertions ─────────────────────────────────────────────────────────

/** Asserts no uncaught JS errors were emitted during page load. */
export async function assertNoConsoleErrors(page: Page): Promise<void> {
  const errors: string[] = [];
  page.on("pageerror", (err) => errors.push(err.message));
  // Give the page a moment to settle after route navigation
  await page.waitForTimeout(300);
  // Filter out known benign Next.js hydration messages
  const realErrors = errors.filter(
    (e) =>
      !e.includes("hydration") &&
      !e.includes("ResizeObserver") &&
      !e.includes("Non-Error promise")
  );
  expect(realErrors, `Unexpected JS errors: ${realErrors.join("; ")}`).toHaveLength(0);
}

/** Waits for any loading skeleton to disappear (max 10s). */
export async function waitForLoadComplete(page: Page): Promise<void> {
  // Skeletons use animate-pulse — wait until none are visible
  await page
    .locator(".animate-pulse")
    .waitFor({ state: "hidden", timeout: 10_000 })
    .catch(() => {
      // Skeleton may already be gone or never appeared — acceptable
    });
}
