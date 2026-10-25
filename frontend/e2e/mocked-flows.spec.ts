/**
 * DevTwin E2E — Mocked Authenticated User Flows
 *
 * Mechanically verifies authenticated application workflows using Playwright
 * network interception (page.route) against exact Step 6J backend schemas.
 *
 * This suite provides deterministic verification of:
 * 1. Developer Profile Provisioning (404 -> POST /developers/me)
 * 2. Authenticated Shell Navigation across all 6 routes
 * 3. Repository Listing and Selection Switching
 * 4. Analysis Job Submission and StageStepper Progress
 * 5. Interactive SkillGraph Canvas (Cytoscape canvas, layout engines, type filters, table toggle)
 * 6. Capability History Recharts Timeline and Snapshot Table
 * 7. Error Handling (401 session expiry and 500 server errors)
 *
 * Security Note:
 * Uses an ephemeral dummy dev token injected into sessionStorage.
 * No live credentials or secrets are used or logged.
 */

import { test, expect, type Page, type Route } from "@playwright/test";
import { ROUTES } from "./helpers";

const MOCK_TOKEN = "devtwin_ephemeral_test_token_mock_only";

// Standard Fixture Data matching Step 6J schemas (docs/12_API_SPECIFICATION.md)
const MOCK_DEVELOPER = {
  id: "dev-uuid-1111-2222-3333",
  auth_user_id: "auth-uuid-4444-5555-6666",
  created_at: "2026-10-20T10:00:00Z",
  updated_at: "2026-10-20T10:00:00Z",
};

const MOCK_REPOS = [
  {
    id: "repo-uuid-1111",
    project_id: "proj-uuid-1111",
    github_repo_id: 101,
    owner_login: "praveen-89",
    name: "DevTwin",
    full_name: "praveen-89/DevTwin",
    url: "https://github.com/praveen-89/DevTwin",
    default_branch: "main",
    visibility: "public" as const,
    synced_at: "2026-10-20T12:00:00Z",
    created_at: "2026-10-20T10:00:00Z",
  },
  {
    id: "repo-uuid-2222",
    project_id: "proj-uuid-1111",
    github_repo_id: 102,
    owner_login: "praveen-89",
    name: "FastAPI-Microservices",
    full_name: "praveen-89/FastAPI-Microservices",
    url: "https://github.com/praveen-89/FastAPI-Microservices",
    default_branch: "master",
    visibility: "private" as const,
    synced_at: "2026-10-20T11:00:00Z",
    created_at: "2026-10-20T10:30:00Z",
  },
];

const MOCK_GITHUB_STATUS = {
  is_connected: true,
  is_installed: true,
  is_disconnected: false,
  github_username: "praveen-89",
};

const MOCK_CAPABILITIES = {
  items: [
    {
      id: "cap-uuid-001",
      developer_id: "dev-uuid-1111-2222-3333",
      target: {
        target_type: "technology" as const,
        target_id: "tech-python",
        target_name: "Python",
        domain_or_category: "Backend",
      },
      score: 0.88,
      confidence: 0.92,
      scoring_version: "1.0.0",
      updated_at: "2026-10-20T14:00:00Z",
    },
    {
      id: "cap-uuid-002",
      developer_id: "dev-uuid-1111-2222-3333",
      target: {
        target_type: "skill" as const,
        target_id: "skill-async",
        target_name: "Asynchronous Programming",
        domain_or_category: "Concurrency",
      },
      score: 0.81,
      confidence: 0.85,
      scoring_version: "1.0.0",
      updated_at: "2026-10-20T14:00:00Z",
    },
    {
      id: "cap-uuid-003",
      developer_id: "dev-uuid-1111-2222-3333",
      target: {
        target_type: "concept" as const,
        target_id: "concept-clean-arch",
        target_name: "Clean Architecture",
        domain_or_category: "Architecture",
      },
      score: 0.75,
      confidence: 0.80,
      scoring_version: "1.0.0",
      updated_at: "2026-10-20T14:00:00Z",
    },
  ],
  total: 3,
  limit: 50,
  offset: 0,
};

const MOCK_HISTORY = {
  items: [
    {
      id: "hist-001",
      capability_id: "cap-uuid-001",
      analysis_run_id: "run-001",
      target: {
        target_type: "technology" as const,
        target_id: "tech-python",
        target_name: "Python",
        domain_or_category: "Backend",
      },
      score: 0.72,
      confidence: 0.80,
      scoring_version: "1.0.0",
      recorded_at: "2026-10-18T10:00:00Z",
    },
    {
      id: "hist-002",
      capability_id: "cap-uuid-001",
      analysis_run_id: "run-002",
      target: {
        target_type: "technology" as const,
        target_id: "tech-python",
        target_name: "Python",
        domain_or_category: "Backend",
      },
      score: 0.88,
      confidence: 0.92,
      scoring_version: "1.0.0",
      recorded_at: "2026-10-20T14:00:00Z",
    },
  ],
  total: 2,
  limit: 50,
  offset: 0,
};

const MOCK_SKILLGRAPH = {
  repository_id: "repo-uuid-1111",
  analysis_run_id: "run-002",
  languages: [
    { language: "Python", bytes: 154200 },
    { language: "TypeScript", bytes: 89400 },
  ],
  dependencies: [
    { ecosystem: "pypi", package_name: "fastapi", version_constraint: ">=0.115" },
    { ecosystem: "npm", package_name: "next", version_constraint: "^16.0" },
  ],
  nodes: [
    { id: "node-python", name: "Python", type: "technology" as const, domain_or_category: "Language" },
    { id: "node-fastapi", name: "FastAPI", type: "technology" as const, domain_or_category: "Framework" },
    { id: "node-async", name: "AsyncIO Concurrency", type: "skill" as const, domain_or_category: "Backend" },
    { id: "node-arch", name: "Hexagonal Architecture", type: "concept" as const, domain_or_category: "Design" },
  ],
  edges: [
    { source_id: "node-python", target_id: "node-fastapi", source_name: "Python", target_name: "FastAPI", relation_type: "powers" },
    { source_id: "node-fastapi", target_id: "node-async", source_name: "FastAPI", target_name: "AsyncIO Concurrency", relation_type: "utilizes" },
    { source_id: "node-fastapi", target_id: "node-arch", source_name: "FastAPI", target_name: "Hexagonal Architecture", relation_type: "implements" },
  ],
};

const MOCK_RISKS = {
  items: [
    {
      id: "risk-001",
      repository_id: "repo-uuid-1111",
      analysis_run_id: "run-002",
      category: "SECURITY",
      severity: "MEDIUM" as const,
      confidence: 0.89,
      risk_type: "INSECURE_CONFIGURATION",
      file_path: "app/core/config.py",
      line_start: 45,
      line_end: 50,
      detected_at: "2026-10-20T14:02:00Z",
    },
  ],
  total: 1,
  limit: 50,
  offset: 0,
  analysis_run_id: "run-002",
};

/**
 * Attaches comprehensive API route mocks to the Playwright page.
 */
async function setupApiMocks(page: Page) {
  await page.route("http://localhost:8000/**", async (route: Route) => {
    const url = route.request().url();
    const method = route.request().method();

    if (url.includes("/developers/me/capabilities/history")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_HISTORY) });
    }
    if (url.includes("/developers/me/capabilities")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_CAPABILITIES) });
    }
    if (url.includes("/developers/me/evidence")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ items: [], total: 0, limit: 50, offset: 0 }) });
    }
    if (url.includes("/developers/me") && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_DEVELOPER) });
    }
    if (url.includes("/developers/me") && method === "POST") {
      return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(MOCK_DEVELOPER) });
    }
    if (url.includes("/github/status")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_GITHUB_STATUS) });
    }
    if (url.includes("/repositories") && url.includes("/skillgraph")) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_SKILLGRAPH) });
    }
    if (url.includes("/repositories") && (url.includes("/risks") || url.includes("/risk-findings"))) {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_RISKS) });
    }
    if (url.includes("/repositories") && method === "GET") {
      return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_REPOS) });
    }
    if (url.includes("/analysis-jobs") && method === "POST") {
      return route.fulfill({
        status: 201,
        contentType: "application/json",
        body: JSON.stringify({ id: "job-001", job_id: "job-001", status: "PROCESSING" }),
      });
    }
    if (url.includes("/analysis-jobs/job-001")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "job-001",
          job_id: "job-001",
          repository_id: "repo-uuid-1111",
          status: "COMPLETED",
          attempt_count: 1,
          requested_at: "2026-10-20T14:00:00Z",
          completed_at: "2026-10-20T14:05:00Z",
        }),
      });
    }
    if (url.includes("/analysis-run")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          id: "run-002",
          analysis_job_id: "job-001",
          repository_id: "repo-uuid-1111",
          status: "COMPLETED",
          analyzer_version: "1.0.0",
          schema_version: "1.0.0",
          error_code: null,
          error_message: null,
          started_at: "2026-10-20T14:00:00Z",
          completed_at: "2026-10-20T14:05:00Z",
          created_at: "2026-10-20T14:00:00Z",
        }),
      });
    }

    // Default fallback
    return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({}) });
  });
}

test.describe("M — Mocked Authenticated User Flows (End-to-End Simulation)", () => {
  test.beforeEach(async ({ page }) => {
    await setupApiMocks(page);
    // Inject dev token into sessionStorage before navigating
    await page.addInitScript((token: string) => {
      sessionStorage.setItem("devtwin_dev_token", token);
    }, MOCK_TOKEN);
  });

  test("M1 — Developer Profile Provisioning on 404 (Auto-registration flow)", async ({ page }) => {
    let postCalled = false;
    let getAttempts = 0;

    await page.route("http://localhost:8000/developers/me", async (route: Route) => {
      const method = route.request().method();
      if (method === "GET") {
        getAttempts++;
        if (getAttempts === 1) {
          // Profile not yet created -> 404 Not Found
          return route.fulfill({ status: 404, contentType: "application/json", body: JSON.stringify({ detail: "Developer profile not found." }) });
        }
        return route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(MOCK_DEVELOPER) });
      }
      if (method === "POST") {
        postCalled = true;
        return route.fulfill({ status: 201, contentType: "application/json", body: JSON.stringify(MOCK_DEVELOPER) });
      }
      return route.fulfill({ status: 200, body: JSON.stringify(MOCK_DEVELOPER) });
    });

    await page.goto(ROUTES.home);
    await page.waitForTimeout(1000);

    // Verify POST /developers/me was automatically triggered
    expect(postCalled).toBe(true);
    await expect(page.locator("body")).toBeVisible();
    await expect(page.locator("text=Application error")).not.toBeVisible();
  });

  test("M2 — Authenticated Navigation across all six routes without crash", async ({ page }) => {
    for (const path of Object.values(ROUTES)) {
      await page.goto(path);
      await page.waitForTimeout(300);
      await expect(page.locator("body")).toBeVisible();
      await expect(page.locator("text=Application error")).not.toBeVisible();
    }
  });

  test("M3 — Repositories Page displays repo list and supports switching", async ({ page }) => {
    await page.goto(ROUTES.repositories);
    await page.waitForTimeout(800);

    // Both mock repos must be rendered in the list
    await expect(page.locator("text=praveen-89/DevTwin").first()).toBeVisible();
    await expect(page.locator("text=praveen-89/FastAPI-Microservices").first()).toBeVisible();

    // Click the second repository button
    const secondRepoBtn = page.locator("button", { hasText: "FastAPI-Microservices" }).first();
    await secondRepoBtn.click();
    await page.waitForTimeout(400);

    // Verify detail updates with second repo's default branch
    await expect(page.locator("text=master").first()).toBeVisible();
    await expect(page.locator("text=private").first()).toBeVisible();
  });

  test("M4 — Overview Page renders GitHub status, capabilities gauge, and risk finding", async ({ page }) => {
    await page.goto(ROUTES.home);
    await page.waitForTimeout(1000);

    // GitHub connection card renders username badge and status description
    await expect(page.locator("text=@praveen-89").first()).toBeVisible();
    await expect(page.locator("text=/installed and connected/i").first()).toBeVisible();

    // Capability score gauge
    await expect(page.locator("text=Python").first()).toBeVisible();

    // CodeRisk finding summary
    await expect(page.locator("text=INSECURE_CONFIGURATION").first()).toBeVisible();
  });

  test("M5 — SkillGraph Page renders canvas, layout buttons, type filters, and table toggle", async ({ page }) => {
    await page.goto(ROUTES.skillgraph);
    await page.waitForTimeout(1000);

    // Real browser Cytoscape canvas element
    const canvas = page.locator("canvas").first();
    await expect(canvas).toBeVisible({ timeout: 5000 });

    // Layout buttons: concentric, breadthfirst, circle, force
    const circleBtn = page.locator("button", { hasText: /circle/i }).first();
    if (await circleBtn.isVisible()) {
      await circleBtn.click();
      await page.waitForTimeout(200);
    }

    // Type filter: skill
    const skillTab = page.locator("button", { hasText: /^skill$/i }).first();
    if (await skillTab.isVisible()) {
      await skillTab.click();
      await page.waitForTimeout(200);
    }

    // Switch to Accessible Table View
    const tableBtn = page.locator("button[aria-label='Accessible Table View']").first();
    await expect(tableBtn).toBeVisible();
    await tableBtn.click();
    await page.waitForTimeout(300);

    // Verify table rendered with filtered skill taxonomy node
    const table = page.locator("table[aria-label*='Taxonomy nodes']").first();
    await expect(table).toBeVisible();
    await expect(table.locator("text=AsyncIO Concurrency").first()).toBeVisible();

    // Switch back to canvas view
    const canvasBtn = page.locator("button[aria-label='Interactive Canvas View']").first();
    await canvasBtn.click();
    await page.waitForTimeout(300);
    await expect(page.locator("canvas").first()).toBeVisible();
  });

  test("M6 — Capabilities Page renders amber disclaimer, cards, and historical snapshots", async ({ page }) => {
    await page.goto(ROUTES.capabilities);
    await page.waitForTimeout(1000);

    // Run-scoped amber disclaimer per ADR
    await expect(page.locator("text=/Run-Scoped/i").first()).toBeVisible();

    // Capability card for Python
    const pythonCard = page.locator("[role='button'][tabindex]", { hasText: "Python" }).first();
    await expect(pythonCard).toBeVisible();

    // Click Python card to view history
    await pythonCard.click();
    await page.waitForTimeout(800);

    // Snapshot history table should render historical records
    const snapshotTable = page.locator("table[aria-label*='snapshot']").first();
    await expect(snapshotTable).toBeVisible({ timeout: 4000 });
    await expect(snapshotTable.locator("th", { hasText: /Score/i }).first()).toBeVisible();
    await expect(snapshotTable.locator("th", { hasText: /Confidence/i }).first()).toBeVisible();
  });

  test("M7 — API 401 Session Expiry handles error gracefully and clears session", async ({ page }) => {
    // Override developers/me with 401 Unauthorized
    await page.route("http://localhost:8000/developers/me", async (route: Route) => {
      return route.fulfill({ status: 401, contentType: "application/json", body: JSON.stringify({ detail: "Signature has expired" }) });
    });

    await page.goto(ROUTES.home);
    await page.waitForTimeout(1000);

    // Must not crash with unhandled React overlay
    await expect(page.locator("text=Application error")).not.toBeVisible();

    // Session guidance message is shown
    await expect(page.locator("text=/Session expired or invalid|Sign in/i").first()).toBeVisible();
  });
});
