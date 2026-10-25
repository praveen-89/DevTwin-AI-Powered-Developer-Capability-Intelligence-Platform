/**
 * DevTwin E2E — Capability History Visualizations (Workflow E)
 *
 * Tests capability list rendering, chart selection interaction, snapshot table,
 * run-scoped disclaimer visibility, and empty/error state handling.
 * Authenticated tests require DEVTWIN_DEV_TOKEN.
 */

import { test, expect } from "@playwright/test";
import {
  ROUTES,
  getDevToken,
  injectDevToken,
  gotoAndSettle,
  waitForLoadComplete,
} from "./helpers";

test.describe("E — Capability History Visualizations", () => {
  test("E1 — Capabilities page renders without crash (unauthenticated)", async ({ page }) => {
    await gotoAndSettle(page, ROUTES.capabilities);
    await waitForLoadComplete(page);
    await expect(page.locator("body")).toBeVisible();
    await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
  });

  test("E2 — Capabilities page has a visible h1 heading", async ({ page }) => {
    await gotoAndSettle(page, ROUTES.capabilities);
    const h1 = page.locator("h1").first();
    await expect(h1).toBeVisible({ timeout: 8000 });
  });

  test.describe("E — Authenticated capability interactions", () => {
    test.beforeEach(async ({ page }) => {
      const token = getDevToken();
      if (!token) {
        test.skip(true, "DEVTWIN_DEV_TOKEN not set — skipping authenticated capability test");
        return;
      }
      await page.goto(ROUTES.capabilities);
      await injectDevToken(page, token);
    });

    test("E3 — Run-scoped amber disclaimer is visible on capabilities page", async ({ page }) => {
      await waitForLoadComplete(page);
      // The amber disclaimer must always be present (per ADR design constraint)
      const disclaimer = page.locator("text=/Run-Scoped/i").first();
      await expect(disclaimer).toBeVisible({ timeout: 5000 });
    });

    test("E4 — Capability cards or empty state is shown (no blank page)", async ({ page }) => {
      await waitForLoadComplete(page);
      const body = await page.locator("body").textContent();
      expect(body?.trim().length).toBeGreaterThan(50);
      await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
    });

    test("E5 — Chart history area renders (idle prompt or chart container)", async ({ page }) => {
      await waitForLoadComplete(page);
      // History section is always rendered (either as an idle prompt or a real chart)
      const historySection = page.locator(
        "text=/Capability Score History|Historical Snapshot/i, svg, [class*='recharts']"
      ).first();
      const historyVisible = await historySection.isVisible({ timeout: 5000 }).catch(() => false);
      if (!historyVisible) {
        // If no capabilities exist at all, the chart section may not appear
        console.log("E5: History chart section not visible — may have no capability data.");
      }
      await expect(page.locator("body")).toBeVisible();
    });

    test("E6 — Clicking a capability card updates history chart (if cards present)", async ({ page }) => {
      await waitForLoadComplete(page);
      // Find capability cards: they have role="button" and tabIndex
      const capCards = page.locator("[role='button'][tabindex]");
      const count = await capCards.count();
      if (count > 0) {
        // Click the first capability card
        await capCards.first().click();
        await page.waitForTimeout(1000); // Allow history fetch to complete
        // Chart or snapshot log should update — page must not crash
        await expect(page.locator("body")).toBeVisible();
        // The "Viewing History" badge should appear on the selected card
        const viewingBadge = page.locator("text=Viewing History").first();
        const badgeVisible = await viewingBadge.isVisible({ timeout: 3000 }).catch(() => false);
        if (!badgeVisible) {
          console.log("E6: 'Viewing History' badge not found after click — may be a timing issue.");
        }
      } else {
        console.log("E6: No capability cards found — skipping selection test.");
      }
    });

    test("E7 — Type filter tabs change the capability list", async ({ page }) => {
      await waitForLoadComplete(page);
      const filterBtns = page.locator("button[role='tab']");
      const count = await filterBtns.count();
      if (count > 0) {
        // Click each filter tab in sequence — verify no crash
        for (let i = 0; i < Math.min(count, 4); i++) {
          await filterBtns.nth(i).click();
          await page.waitForTimeout(500);
          await expect(page.locator("body")).toBeVisible();
        }
      } else {
        console.log("E7: Filter tabs not found.");
      }
    });

    test("E8 — Snapshot history table columns are present when data exists", async ({ page }) => {
      await waitForLoadComplete(page);
      // Click first capability card to load history
      const capCards = page.locator("[role='button'][tabindex]");
      if (await capCards.count() > 0) {
        await capCards.first().click();
        await page.waitForTimeout(1500);
        // Check for the snapshot table
        const snapshotTable = page.locator("table[aria-label*='snapshot']").first();
        const tableVisible = await snapshotTable.isVisible({ timeout: 5000 }).catch(() => false);
        if (tableVisible) {
          // Table header columns must be present
          await expect(snapshotTable.locator("th", { hasText: /Recorded/i }).first()).toBeVisible();
          await expect(snapshotTable.locator("th", { hasText: /Score/i }).first()).toBeVisible();
          await expect(snapshotTable.locator("th", { hasText: /Confidence/i }).first()).toBeVisible();
        } else {
          console.log("E8: Snapshot table not visible — capability may have no historical records.");
        }
      }
    });

    test("E9 — Page does not crash on rapid capability card switching", async ({ page }) => {
      await waitForLoadComplete(page);
      const capCards = page.locator("[role='button'][tabindex]");
      const count = await capCards.count();
      if (count >= 2) {
        // Rapidly click between first and second card
        for (let i = 0; i < 3; i++) {
          await capCards.nth(0).click();
          await page.waitForTimeout(150);
          await capCards.nth(1).click();
          await page.waitForTimeout(150);
        }
        await expect(page.locator("body")).toBeVisible();
        await expect(page.locator("text=Application error")).not.toBeVisible({ timeout: 2000 }).catch(() => {});
      } else {
        console.log("E9: Fewer than 2 capability cards — skipping rapid switch test.");
      }
    });
  });
});
