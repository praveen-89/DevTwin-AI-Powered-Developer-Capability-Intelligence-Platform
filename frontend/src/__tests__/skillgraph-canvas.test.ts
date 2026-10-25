/**
 * Tests for SkillGraph data-transformation and filtering logic.
 *
 * We test the pure filtering/matching functions used by SkillGraphCanvas
 * and the selection-matching helpers used by SkillGraphDetail, using
 * realistic API-shaped fixtures.  Cytoscape DOM rendering is not tested
 * here because it requires a canvas beyond jsdom.
 */

import { describe, it, expect } from "vitest";
import type {
  SkillGraphNodeResponse,
  SkillGraphEdgeResponse,
} from "@/types/api";

// ── Types & Helpers replicated from skillgraph-canvas.tsx ────────────────────

type NodeFilter = "ALL" | "skill" | "technology" | "concept";

function filterNodes(
  nodes: SkillGraphNodeResponse[],
  filterType: NodeFilter,
  searchQuery: string
): SkillGraphNodeResponse[] {
  return nodes.filter((n) => {
    if (filterType !== "ALL" && n.type !== filterType) return false;
    if (
      searchQuery.trim() &&
      !n.name.toLowerCase().includes(searchQuery.toLowerCase().trim())
    ) {
      return false;
    }
    return true;
  });
}

function filterEdges(
  edges: SkillGraphEdgeResponse[],
  visibleNodeIds: Set<string>
): SkillGraphEdgeResponse[] {
  return edges.filter(
    (e) => visibleNodeIds.has(e.source_id) && visibleNodeIds.has(e.target_id)
  );
}

function getConnectedEdges(
  nodeId: string,
  edges: SkillGraphEdgeResponse[]
): SkillGraphEdgeResponse[] {
  return edges.filter((e) => e.source_id === nodeId || e.target_id === nodeId);
}

// ── Fixtures ──────────────────────────────────────────────────────────────────

const NODES: SkillGraphNodeResponse[] = [
  { id: "n-python", name: "Python", type: "skill", domain_or_category: "Language" },
  { id: "n-fastapi", name: "FastAPI", type: "technology", domain_or_category: "Web" },
  { id: "n-rest", name: "REST API", type: "concept", domain_or_category: "Web" },
  { id: "n-ts", name: "TypeScript", type: "skill", domain_or_category: "Language" },
];

const EDGES: SkillGraphEdgeResponse[] = [
  {
    source_id: "n-fastapi",
    target_id: "n-python",
    source_name: "FastAPI",
    target_name: "Python",
    relation_type: "REQUIRES",
  },
  {
    source_id: "n-fastapi",
    target_id: "n-rest",
    source_name: "FastAPI",
    target_name: "REST API",
    relation_type: "IMPLEMENTS",
  },
  {
    source_id: "n-ts",
    target_id: "n-rest",
    source_name: "TypeScript",
    target_name: "REST API",
    relation_type: "RELATED_TO",
  },
];

// ── filterNodes tests ─────────────────────────────────────────────────────────

describe("filterNodes", () => {
  it('returns all nodes when filterType is "ALL" and query is empty', () => {
    expect(filterNodes(NODES, "ALL", "")).toHaveLength(4);
  });

  it('filters to only skill nodes when filterType is "skill"', () => {
    const result = filterNodes(NODES, "skill", "");
    expect(result).toHaveLength(2);
    expect(result.every((n) => n.type === "skill")).toBe(true);
  });

  it('filters to only technology nodes when filterType is "technology"', () => {
    const result = filterNodes(NODES, "technology", "");
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("FastAPI");
  });

  it('filters to only concept nodes when filterType is "concept"', () => {
    const result = filterNodes(NODES, "concept", "");
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("REST API");
  });

  it("filters by search query case-insensitively", () => {
    const result = filterNodes(NODES, "ALL", "FAST");
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("FastAPI");
  });

  it("combines type filter and search query", () => {
    // Only skills, name contains "python"
    const result = filterNodes(NODES, "skill", "python");
    expect(result).toHaveLength(1);
    expect(result[0].name).toBe("Python");
  });

  it("returns empty when search matches no nodes", () => {
    const result = filterNodes(NODES, "ALL", "nonexistent-xyz");
    expect(result).toHaveLength(0);
  });

  it("ignores leading/trailing whitespace in search query", () => {
    const result = filterNodes(NODES, "ALL", "  Python  ");
    expect(result).toHaveLength(1);
    expect(result[0].id).toBe("n-python");
  });

  it("returns empty array from empty input", () => {
    expect(filterNodes([], "ALL", "")).toHaveLength(0);
  });
});

// ── filterEdges tests ─────────────────────────────────────────────────────────

describe("filterEdges", () => {
  it("includes edges where both endpoints are visible", () => {
    const visible = new Set(["n-fastapi", "n-python", "n-rest", "n-ts"]);
    expect(filterEdges(EDGES, visible)).toHaveLength(3);
  });

  it("excludes edges whose source is hidden", () => {
    // Hide n-ts → the RELATED_TO edge should be excluded
    const visible = new Set(["n-fastapi", "n-python", "n-rest"]);
    const result = filterEdges(EDGES, visible);
    expect(result).toHaveLength(2);
    expect(result.every((e) => e.source_id !== "n-ts")).toBe(true);
  });

  it("excludes edges whose target is hidden", () => {
    // Hide n-rest → edges pointing to n-rest should be excluded
    const visible = new Set(["n-fastapi", "n-python", "n-ts"]);
    const result = filterEdges(EDGES, visible);
    expect(result).toHaveLength(1);
    expect(result[0].relation_type).toBe("REQUIRES");
  });

  it("returns empty array when no nodes are visible", () => {
    expect(filterEdges(EDGES, new Set())).toHaveLength(0);
  });

  it("returns empty array from empty edge input", () => {
    const visible = new Set(["n-fastapi", "n-python"]);
    expect(filterEdges([], visible)).toHaveLength(0);
  });
});

// ── getConnectedEdges tests ───────────────────────────────────────────────────

describe("getConnectedEdges", () => {
  it("returns all edges incident on a given node (as source or target)", () => {
    // n-fastapi is source in 2 edges
    const result = getConnectedEdges("n-fastapi", EDGES);
    expect(result).toHaveLength(2);
  });

  it("returns incoming edges where node is target", () => {
    // n-rest is target of 2 edges
    const result = getConnectedEdges("n-rest", EDGES);
    expect(result).toHaveLength(2);
  });

  it("returns empty for an isolated node (no incident edges)", () => {
    expect(getConnectedEdges("n-isolated", EDGES)).toHaveLength(0);
  });

  it("returns empty when edge list is empty", () => {
    expect(getConnectedEdges("n-fastapi", [])).toHaveLength(0);
  });
});

// ── Edge ID determinism tests ─────────────────────────────────────────────────

describe("edge ID construction", () => {
  it("produces a consistent deterministic ID from source/target/relation fields", () => {
    const e = EDGES[0];
    const id = `e-${e.source_id}-${e.target_id}-${e.relation_type}`;
    expect(id).toBe("e-n-fastapi-n-python-REQUIRES");
    // Same inputs always produce the same ID
    expect(id).toBe(`e-${e.source_id}-${e.target_id}-${e.relation_type}`);
  });
});

// ── Selection matching tests ──────────────────────────────────────────────────

describe("node selection", () => {
  it("finds a node by ID from the node list", () => {
    const target = NODES.find((n) => n.id === "n-fastapi");
    expect(target).toBeDefined();
    expect(target?.name).toBe("FastAPI");
  });

  it("returns undefined for an unknown node ID", () => {
    const target = NODES.find((n) => n.id === "unknown-id");
    expect(target).toBeUndefined();
  });
});

// ── Empty graph state ─────────────────────────────────────────────────────────

describe("empty graph handling", () => {
  it("filterNodes on empty input returns empty (no fabrication)", () => {
    expect(filterNodes([], "ALL", "")).toHaveLength(0);
  });

  it("filterEdges on empty input returns empty (no fabrication)", () => {
    expect(filterEdges([], new Set())).toHaveLength(0);
  });

  it("getConnectedEdges on empty input returns empty (no fabrication)", () => {
    expect(getConnectedEdges("any", [])).toHaveLength(0);
  });
});
