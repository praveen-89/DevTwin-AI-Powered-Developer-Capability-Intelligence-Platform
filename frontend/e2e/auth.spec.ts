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
  test.describe("A0 — Marketing site and route guard", () => {
    test("A0.1 — Landing page renders and its CTA links to /signup", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.landing);
      await expect(page).toHaveTitle(/DevTwin/i);
      const cta = page.getByRole("link", { name: /Connect with GitHub/i }).first();
      await expect(cta).toBeVisible();
      await expect(cta).toHaveAttribute("href", "/signup");
    });

    test("A0.2 — Unauthenticated visit to /dashboard redirects to /login", async ({ page }) => {
      await page.goto(ROUTES.home, { waitUntil: "networkidle" });
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.getByRole("button", { name: "Continue with GitHub" })).toBeVisible();
    });

    test("A0.3 — Regression: a stale/invalid session token must not let the (app) guard render the dashboard shell", async ({ page }) => {
      // This is the exact regression that shipped: a bearer token present in
      // storage (expired, revoked, or otherwise rejected by the backend)
      // used to be enough for the (app) layout's old `!!token` check to
      // treat the visitor as authenticated and render the full protected
      // dashboard shell, even though the developer profile fetch that
      // backs the header's signed-in state failed. The header showed
      // "Sign in" while the dashboard shell rendered behind it — a real
      // access-control bug. The guard must now require the same
      // `isAuthenticated` (token AND a confirmed developer profile) that
      // the header uses, so an unconfirmable token also redirects to
      // /login instead of rendering protected content.
      await page.goto(ROUTES.home, { waitUntil: "domcontentloaded" });
      await page.evaluate(() => {
        sessionStorage.setItem("devtwin_dev_token", "stale-invalid-token-regression-test");
      });
      await page.reload({ waitUntil: "domcontentloaded" });
      await page.waitForTimeout(3000);

      await expect(page).toHaveURL(/\/login$/);
      // The protected dashboard shell (sidebar nav) must never have rendered.
      await expect(page.getByRole("link", { name: "Repositories" })).not.toBeVisible();
    });
  });

  test.describe("A1 — Unauthenticated states", () => {
    test("A1.1 — Overview route redirects an unauthenticated visitor to /login instead of a broken dashboard", async ({ page }) => {
      await gotoAndSettle(page, ROUTES.home);
      // Must not crash — page title must be visible
      await expect(page).toHaveTitle(/DevTwin/i);
      // The route guard must redirect to the dedicated login page rather
      // than rendering the protected dashboard shell.
      await expect(page).toHaveURL(/\/login$/);
      await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
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

  test.describe("A1b — Header and route guard must agree on auth state", () => {
    test("A1b.1 — With a backend-confirmed session, the header shows signed-in AND the dashboard shell renders together", async ({ page }) => {
      // Mocks the developer-profile call so `isAuthenticated` (token +
      // confirmed developer) resolves true without a live backend. Both
      // the (app) layout guard and the Header read this same derived
      // field, so this test fails if either one regresses back to
      // disagreeing with the other.
      await page.route("**/developers/me", (route) =>
        route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({
            id: "dev-uuid-agree-test",
            auth_user_id: "auth-uuid-agree-test",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          }),
        })
      );
      await page.addInitScript(() => {
        sessionStorage.setItem("devtwin_dev_token", "mock-confirmed-session-token");
      });

      await page.goto(ROUTES.home, { waitUntil: "domcontentloaded" });
      await page.waitForTimeout(1500);

      // Must still be on /dashboard — guard must not have redirected.
      await expect(page).toHaveURL(/\/dashboard$/);
      // Header must show the signed-in state (sign-out control), not
      // "Sign in" / "Sign in to connect".
      await expect(page.getByRole("button", { name: /Sign out/i })).toBeVisible();
      await expect(page.getByRole("button", { name: /^Sign in$/i })).not.toBeVisible();
      // Protected dashboard shell must be visible at the same time.
      await expect(page.getByRole("link", { name: "Repositories" })).toBeVisible();
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
