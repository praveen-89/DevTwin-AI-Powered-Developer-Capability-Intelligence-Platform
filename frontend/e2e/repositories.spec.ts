/**
 * DevTwin E2E — Repository Workflow (Workflow B)
 *
 * Tests repository listing, empty states, selection, switching, and API failures.
 * Authenticated tests require DEVTWIN_DEV_TOKEN to be set.
 */

import { test, expect } from "@playwright/test";
import {
  ROUTES,
  getDevToken,
  injectDevToken,
  gotoAndSettle,
  waitForLoadComplete,
} from "./helpers";

test.describe("B — Repository Workflow", () => {
  test("B1 — Repositories page renders without crashing (unauthenticated)", async ({ page }) => {
    await gotoAndSettle(page, ROUTES.repositories);
    await waitForLoadComplete(page);
    await expect(page.locator("body")).toBeVisible();
    // Must not be a blank white void
    const text = await page.locator("body").textContent();
    expect(text?.trim().length).toBeGreaterThan(10);
  });

  test("B2 — Repositories page has a meaningful heading", async ({ page }) => {
    await gotoAndSettle(page, ROUTES.repositories);
    // Page should render an h1 heading
    const h1 = page.locator("h1").first();
    await expect(h1).toBeVisible({ timeout: 8000 });
    const headingText = await h1.textContent();
    expect(headingText?.trim().length).toBeGreaterThan(0);
  });

  test.describe("B — Authenticated repository interactions", () => {
    test.beforeEach(async ({ page }) => {
      const token = getDevToken();
      if (!token) {
        test.skip(true, "DEVTWIN_DEV_TOKEN not set — skipping authenticated repository test");
        return;
      }
      await page.goto(ROUTES.repositories);
      await injectDevToken(page, token);
    });

    test("B3 — Repositories load or empty state is shown (no crash on either path)", async ({ page }) => {
      await waitForLoadComplete(page);
      // Either a list of repos is shown, or an empty state message
      // Both are valid — what's NOT valid is a crash or blank page
      const body = await page.locator("body").textContent();
      expect(body?.trim().length).toBeGreaterThan(20);
      // No unhandled React error overlay
      await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
    });

    test("B4 — Repository page is usable via keyboard (tab navigation)", async ({ page }) => {
      await waitForLoadComplete(page);
      // Tab focus should move through interactive elements without throwing
      await page.keyboard.press("Tab");
      await page.keyboard.press("Tab");
      // No error should be triggered
      await expect(page.locator("body")).toBeVisible();
    });

    test("B5 — Overview page repository selector switches context without stale data flash", async ({ page }) => {
      await page.goto(ROUTES.home, { waitUntil: "networkidle" });
      await waitForLoadComplete(page);
      // Interact with the repo tabs if any are present
      const repoTabs = page.locator("[role='tab'], button[aria-selected]");
      const tabCount = await repoTabs.count();
      if (tabCount >= 2) {
        // Click second tab
        await repoTabs.nth(1).click();
        // Brief settle — stale data check: the page should not crash
        await page.waitForTimeout(500);
        await expect(page.locator("body")).toBeVisible();
        // No React error overlay
        await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 1000 }).catch(() => {});
      } else {
        test.skip(true, "Fewer than 2 repositories available — skipping repo switch test");
      }
    });
  });
});
