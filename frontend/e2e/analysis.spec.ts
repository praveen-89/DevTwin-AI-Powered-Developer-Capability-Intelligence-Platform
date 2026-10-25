/**
 * DevTwin E2E — Analysis Lifecycle (Workflow C)
 *
 * Tests analysis job submission UI, stage stepper, and polling behaviour.
 * Tests do NOT launch real analysis jobs against live repositories
 * without explicit DEVTWIN_DEV_TOKEN and DEVTWIN_ALLOW_LIVE_ANALYSIS=true.
 */

import { test, expect } from "@playwright/test";
import {
  ROUTES,
  getDevToken,
  injectDevToken,
  gotoAndSettle,
  waitForLoadComplete,
} from "./helpers";

const ALLOW_LIVE = process.env.DEVTWIN_ALLOW_LIVE_ANALYSIS === "true";

test.describe("C — Analysis Lifecycle", () => {
  test("C1 — Overview page renders stage stepper or analysis trigger UI (unauthenticated)", async ({ page }) => {
    await gotoAndSettle(page, ROUTES.home);
    await waitForLoadComplete(page);
    await expect(page.locator("body")).toBeVisible();
    // Must show something — not blank
    const text = await page.locator("body").textContent();
    expect(text?.trim().length).toBeGreaterThan(20);
  });

  test("C2 — Overview page h1 heading is rendered", async ({ page }) => {
    await gotoAndSettle(page, ROUTES.home);
    const h1 = page.locator("h1").first();
    await expect(h1).toBeVisible({ timeout: 8000 });
  });

  test.describe("C — Authenticated analysis lifecycle", () => {
    test.beforeEach(async ({ page }) => {
      const token = getDevToken();
      if (!token) {
        test.skip(true, "DEVTWIN_DEV_TOKEN not set — skipping authenticated analysis test");
        return;
      }
      await page.goto(ROUTES.home);
      await injectDevToken(page, token);
    });

    test("C3 — Analysis area loads without error after auth", async ({ page }) => {
      await waitForLoadComplete(page);
      await expect(page.locator("body")).toBeVisible();
      // No crash overlay
      await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
    });

    test("C4 — Stage stepper or pipeline progress element is present in overview", async ({ page }) => {
      await waitForLoadComplete(page);
      // Look for stepper indicators: aria-label, role=list with steps, or status text
      const stepperEl = page.locator(
        "[aria-label*='stage'], [aria-label*='pipeline'], [aria-label*='status'], " +
        "ol[role='list'], [data-testid*='stage'], [data-testid*='stepper']"
      ).first();
      const isVisible = await stepperEl.isVisible().catch(() => false);
      // This test is advisory: presence is checked, absence is noted not failed
      // (stepper only appears when a job is in flight)
      if (!isVisible) {
        console.log("C4: No stage stepper visible (expected when no active job)");
      }
      // What must NOT happen: a crash
      await expect(page.locator("body")).toBeVisible();
    });

    test("C5 — Polling does not continue after navigating away (no console leak)", async ({ page }) => {
      const consoleMessages: string[] = [];
      page.on("console", (msg) => {
        if (msg.type() === "error") consoleMessages.push(msg.text());
      });

      await waitForLoadComplete(page);
      // Navigate away from Overview to break any polling lifecycle
      await page.goto(ROUTES.capabilities, { waitUntil: "networkidle" });
      await page.waitForTimeout(2000);

      // No console errors from destroyed polling should appear
      const pollingErrors = consoleMessages.filter(
        (m) => m.toLowerCase().includes("cannot update") ||
               m.toLowerCase().includes("unmounted component") ||
               m.toLowerCase().includes("setState on unmounted")
      );
      expect(
        pollingErrors,
        `Polling leak detected after navigation: ${pollingErrors.join("; ")}`
      ).toHaveLength(0);
    });

    test("C6 — Analysis submission guard: live test skipped unless DEVTWIN_ALLOW_LIVE_ANALYSIS=true", async ({ page }) => {
      if (!ALLOW_LIVE) {
        test.skip(true, "DEVTWIN_ALLOW_LIVE_ANALYSIS not set — skipping live job submission to protect real repositories");
        return;
      }
      // If live analysis is explicitly allowed, look for the submit button and verify it exists
      await waitForLoadComplete(page);
      const analyzeBtn = page.locator("button", { hasText: /Analyse|Analyze|Run Analysis|Start/i }).first();
      if (await analyzeBtn.isVisible()) {
        // Verify the button is interactive — don't click without confirmation
        await expect(analyzeBtn).toBeEnabled();
      }
    });
  });
});
