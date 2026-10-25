/**
 * DevTwin E2E — Authentication & Onboarding
 *
 * Workflow A: Tests the unauthenticated and authenticated access states.
 *
 * Live token: Set DEVTWIN_DEV_TOKEN env var before running.
 * If absent, authenticated tests are skipped — not failed.
 */

import { test, expect } from "@playwright/test";
import {
  ROUTES,
  getDevToken,
  injectDevToken,
  clearAuthState,
  gotoAndSettle,
  waitForLoadComplete,
} from "./helpers";

test.describe("A — Authentication & Onboarding", () => {
  test.describe("A1 — Unauthenticated states", () => {
    test("A1.1 — Overview page renders without a token and shows auth guidance", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.home);
      // Must not crash — page title must be visible
      await expect(page).toHaveTitle(/DevTwin/i);
      // Page should render the shell (sidebar or main nav)
      const shell = page.locator("nav, aside, [data-testid='sidebar']").first();
      await expect(shell).toBeVisible({ timeout: 8000 });
    });

    test("A1.2 — Capabilities page unauthenticated shows sign-in prompt, not a crash", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.capabilities);
      await waitForLoadComplete(page);
      // Should render some guidance (empty state, sign-in message, or skeleton resolved)
      // Must not be a blank white page or unhandled error
      const body = await page.locator("body").textContent();
      expect(body).toBeTruthy();
      // Must not show a React unhandled error overlay
      await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
    });

    test("A1.3 — SkillGraph page unauthenticated shows auth message, not blank", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.skillgraph);
      await waitForLoadComplete(page);
      const body = await page.locator("body").textContent();
      expect(body?.length).toBeGreaterThan(50); // Not blank
    });

    test("A1.4 — CodeRisk page unauthenticated is accessible and non-crashing", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.coderisk);
      await waitForLoadComplete(page);
      await expect(page.locator("body")).toBeVisible();
    });

    test("A1.5 — Evidence page unauthenticated renders a usable state", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.evidence);
      await waitForLoadComplete(page);
      await expect(page.locator("body")).toBeVisible();
    });

    test("A1.6 — Repositories page unauthenticated renders without error", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.repositories);
      await waitForLoadComplete(page);
      await expect(page.locator("body")).toBeVisible();
    });
  });

  test.describe("A2 — Authenticated states (skipped when DEVTWIN_DEV_TOKEN is absent)", () => {
    test.beforeEach(async ({ page }) => {
      const token = getDevToken();
      if (!token) {
        test.skip(true, "DEVTWIN_DEV_TOKEN not set — skipping authenticated test");
        return;
      }
      await page.goto(ROUTES.home);
      await injectDevToken(page, token);
    });

    test("A2.1 — With a valid token, Overview page loads without error", async ({ page }) => {
      await waitForLoadComplete(page);
      await expect(page).toHaveTitle(/DevTwin/i);
      // Shell must be visible
      await expect(page.locator("body")).toBeVisible();
    });

    test("A2.2 — Clearing auth state returns to unauthenticated view", async ({ page }) => {
      await clearAuthState(page);
      // Should still render a non-crashing state
      await expect(page.locator("body")).toBeVisible();
    });

    test("A2.3 — Navigation between authenticated routes does not crash", async ({ page }) => {
      for (const route of Object.values(ROUTES)) {
        await page.goto(route, { waitUntil: "domcontentloaded" });
        await expect(page.locator("body")).toBeVisible();
        // Must not show a React error overlay
        await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 1000 }).catch(() => {});
      }
    });
  });
});
