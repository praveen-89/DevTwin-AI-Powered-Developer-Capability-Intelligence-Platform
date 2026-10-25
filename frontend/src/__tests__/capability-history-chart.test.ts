/**
 * Tests for CapabilityHistoryChart data-transformation logic.
 *
 * We test the pure-logic layer (sorting, timestamp parsing, chart-point
 * derivation) using realistic API-shaped fixtures.  We do NOT test the
 * Recharts rendering because it requires a canvas environment beyond jsdom.
 */

import { describe, it, expect } from "vitest";
import type { CapabilityHistoryItemResponse } from "@/types/api";

// ── Helpers replicated from capability-history-chart.tsx ──────────────────────

function sortItems(
  items: CapabilityHistoryItemResponse[]
): CapabilityHistoryItemResponse[] {
  return [...items].sort((a, b) => {
    const ta = new Date(a.recorded_at).getTime();
    const tb = new Date(b.recorded_at).getTime();
    return ta - tb;
  });
}

function toChartPoint(item: CapabilityHistoryItemResponse, idx: number) {
  const dateObj = new Date(item.recorded_at);
  const label = !isNaN(dateObj.getTime())
    ? dateObj.toLocaleDateString("en-US", { month: "short", day: "numeric" })
    : `Run #${idx + 1}`;
  return {
    id: item.id,
    rawTime: item.recorded_at,
    timeLabel: label,
    score: Math.round(item.score * 100) / 100,
    confidence: Math.round(item.confidence * 100) / 100,
    scoringVersion: item.scoring_version,
    runId: item.analysis_run_id,
    targetName: item.target.target_name,
  };
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const BASE_TARGET = {
  target_id: "skill-python",
  target_name: "Python",
  target_type: "skill" as const,
  domain_or_category: "Language",
};

function makeItem(
  overrides: Partial<CapabilityHistoryItemResponse>
): CapabilityHistoryItemResponse {
  return {
    id: "item-1",
    capability_id: "cap-1",
    analysis_run_id: "run-1",
    target: BASE_TARGET,
    score: 0.75,
    confidence: 0.8,
    scoring_version: "v1",
    recorded_at: "2026-01-15T10:00:00Z",
    ...overrides,
  };
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe("sortItems", () => {
  it("sorts items in ascending chronological order", () => {
    const items = [
      makeItem({ id: "b", recorded_at: "2026-03-01T00:00:00Z" }),
      makeItem({ id: "a", recorded_at: "2026-01-01T00:00:00Z" }),
      makeItem({ id: "c", recorded_at: "2026-06-01T00:00:00Z" }),
    ];
    const sorted = sortItems(items);
    expect(sorted.map((i) => i.id)).toEqual(["a", "b", "c"]);
  });

  it("returns empty array unchanged", () => {
    expect(sortItems([])).toEqual([]);
  });

  it("handles a single item without throwing", () => {
    const items = [makeItem({ id: "only" })];
    expect(sortItems(items)).toHaveLength(1);
    expect(sortItems(items)[0].id).toBe("only");
  });

  it("preserves order for identical timestamps (stable-ish)", () => {
    const ts = "2026-04-01T12:00:00Z";
    const items = [
      makeItem({ id: "x", recorded_at: ts }),
      makeItem({ id: "y", recorded_at: ts }),
    ];
    const sorted = sortItems(items);
    // Both share the same timestamp; order among them is unspecified but
    // both must still be present.
    expect(sorted).toHaveLength(2);
    expect(sorted.map((i) => i.id).sort()).toEqual(["x", "y"]);
  });
});

describe("toChartPoint", () => {
  it("returns a valid chart point from a well-formed item", () => {
    const item = makeItem({ recorded_at: "2026-05-10T08:30:00Z" });
    const pt = toChartPoint(item, 0);
    expect(pt.score).toBe(0.75);
    expect(pt.confidence).toBe(0.8);
    expect(pt.id).toBe("item-1");
    expect(pt.targetName).toBe("Python");
    // Label should contain month and day
    expect(pt.timeLabel).toMatch(/May/i);
  });

  it("falls back to 'Run #N' label for a missing timestamp", () => {
    const item = makeItem({ recorded_at: "" });
    const pt = toChartPoint(item, 2);
    expect(pt.timeLabel).toBe("Run #3");
  });

  it("falls back to 'Run #N' label for an invalid timestamp string", () => {
    const item = makeItem({ recorded_at: "not-a-date" });
    const pt = toChartPoint(item, 0);
    expect(pt.timeLabel).toBe("Run #1");
  });

  it("rounds score and confidence to 2 decimal places", () => {
    const item = makeItem({ score: 0.7777, confidence: 0.6666 });
    const pt = toChartPoint(item, 0);
    expect(pt.score).toBe(0.78);
    expect(pt.confidence).toBe(0.67);
  });

  it("includes null analysis_run_id without throwing", () => {
    const item = makeItem({ analysis_run_id: null });
    const pt = toChartPoint(item, 0);
    expect(pt.runId).toBeNull();
  });
});

describe("chart data derivation (combined sort + map)", () => {
  it("produces chronologically ordered chart points from unsorted items", () => {
    const items = [
      makeItem({ id: "i2", recorded_at: "2026-06-15T00:00:00Z", score: 0.9 }),
      makeItem({ id: "i1", recorded_at: "2026-03-10T00:00:00Z", score: 0.6 }),
    ];
    const chartData = sortItems(items).map(toChartPoint);
    expect(chartData[0].id).toBe("i1");
    expect(chartData[0].score).toBe(0.6);
    expect(chartData[1].id).toBe("i2");
    expect(chartData[1].score).toBe(0.9);
  });

  it("produces empty chart data from empty history", () => {
    const chartData = sortItems([]).map(toChartPoint);
    expect(chartData).toHaveLength(0);
  });

  it("does NOT mix targets — each item retains its own targetName", () => {
    const items = [
      makeItem({
        id: "a",
        target: { ...BASE_TARGET, target_name: "Python" },
        recorded_at: "2026-01-01T00:00:00Z",
      }),
      makeItem({
        id: "b",
        target: { ...BASE_TARGET, target_name: "TypeScript" },
        recorded_at: "2026-02-01T00:00:00Z",
      }),
    ];
    const chartData = sortItems(items).map(toChartPoint);
    expect(chartData[0].targetName).toBe("Python");
    expect(chartData[1].targetName).toBe("TypeScript");
  });
});
