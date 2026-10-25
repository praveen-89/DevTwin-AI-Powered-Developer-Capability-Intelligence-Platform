"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import cytoscape, { Core, EventObject } from "cytoscape";
import type { SkillGraphNodeResponse, SkillGraphEdgeResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { Maximize2, Minus, Plus, RotateCcw } from "lucide-react";

export interface SkillGraphCanvasProps {
  nodes: SkillGraphNodeResponse[];
  edges: SkillGraphEdgeResponse[];
  selectedNode: SkillGraphNodeResponse | null;
  selectedEdge: SkillGraphEdgeResponse | null;
  onSelectNode: (node: SkillGraphNodeResponse | null) => void;
  onSelectEdge: (edge: SkillGraphEdgeResponse | null) => void;
  filterType?: "ALL" | "skill" | "technology" | "concept";
  searchQuery?: string;
  className?: string;
}

export function SkillGraphCanvas({
  nodes,
  edges,
  selectedNode,
  selectedEdge,
  onSelectNode,
  onSelectEdge,
  filterType = "ALL",
  searchQuery = "",
  className,
}: SkillGraphCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const [layoutName, setLayoutName] = useState<"cose" | "concentric" | "breadthfirst" | "circle">("cose");

  // Filter elements based on type filter and search query
  const filteredNodes = nodes.filter((n) => {
    if (filterType !== "ALL" && n.type !== filterType) return false;
    if (searchQuery.trim() && !n.name.toLowerCase().includes(searchQuery.toLowerCase().trim())) {
      return false;
    }
    return true;
  });

  const visibleNodeIds = new Set(filteredNodes.map((n) => n.id));

  // Edges are visible only if both source and target nodes are visible
  const filteredEdges = edges.filter(
    (e) => visibleNodeIds.has(e.source_id) && visibleNodeIds.has(e.target_id)
  );

  // Initialize Cytoscape instance
  useEffect(() => {
    if (!containerRef.current) return;

    const cy = cytoscape({
      container: containerRef.current,
      boxSelectionEnabled: false,
      autounselectify: false,
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "font-size": "11px",
            "font-family": "monospace",
            color: "#e2e8f0",
            "text-valign": "bottom",
            "text-margin-y": 6,
            "text-background-color": "#090d16",
            "text-background-opacity": 0.8,
            "text-background-padding": "2px",
            "text-background-shape": "roundrectangle",
            width: 32,
            height: 32,
            "border-width": 2,
            "transition-property": "background-color, border-color, border-width, width, height",
            "transition-duration": 0.2,
          },
        },
        {
          selector: 'node[type = "skill"]',
          style: {
            "background-color": "#06b6d4",
            "border-color": "#0891b2",
            shape: "ellipse",
          },
        },
        {
          selector: 'node[type = "technology"]',
          style: {
            "background-color": "#10b981",
            "border-color": "#059669",
            shape: "roundrectangle",
          },
        },
        {
          selector: 'node[type = "concept"]',
          style: {
            "background-color": "#a855f7",
            "border-color": "#7e22ce",
            shape: "diamond",
          },
        },
        {
          selector: "node:selected",
          style: {
            "border-width": 4,
            "border-color": "#38bdf8",
            width: 40,
            height: 40,
          },
        },
        {
          selector: "edge",
          style: {
            width: 1.5,
            "line-color": "#475569",
            "target-arrow-color": "#475569",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            "arrow-scale": 0.9,
            label: "data(label)",
            "font-size": "8px",
            "font-family": "monospace",
            color: "#94a3b8",
            "text-rotation": "autorotate",
            "text-background-color": "#090d16",
            "text-background-opacity": 0.75,
            "text-background-padding": "1px",
            "transition-property": "line-color, target-arrow-color, width",
            "transition-duration": 0.2,
          },
        },
        {
          selector: "edge:selected",
          style: {
            width: 3,
            "line-color": "#38bdf8",
            "target-arrow-color": "#38bdf8",
            "arrow-scale": 1.2,
            color: "#38bdf8",
          },
        },
      ],
      elements: [],
      layout: { name: "preset" },
    });

    cy.on("tap", "node", (evt: EventObject) => {
      const nodeData = evt.target.data();
      const matched = nodes.find((n) => n.id === nodeData.id);
      if (matched) {
        onSelectNode(matched);
        onSelectEdge(null);
      }
    });

    cy.on("tap", "edge", (evt: EventObject) => {
      const edgeData = evt.target.data();
      const matched = edges.find(
        (e) => e.source_id === edgeData.source && e.target_id === edgeData.target
      );
      if (matched) {
        onSelectEdge(matched);
        onSelectNode(null);
      }
    });

    cy.on("tap", (evt: EventObject) => {
      if (evt.target === cy) {
        onSelectNode(null);
        onSelectEdge(null);
      }
    });

    cyRef.current = cy;

    return () => {
      cy.destroy();
      cyRef.current = null;
    };
  }, [nodes, edges, onSelectNode, onSelectEdge]);

  // Update elements and re-run layout when filtered data changes
  const runLayout = useCallback(
    (name: typeof layoutName) => {
      const cy = cyRef.current;
      if (!cy) return;

      const layoutOptions =
        name === "cose"
          ? {
              name: "cose",
              animate: true,
              animationDuration: 500,
              nodeRepulsion: () => 400000,
              idealEdgeLength: () => 80,
              padding: 40,
            }
          : name === "concentric"
          ? {
              name: "concentric",
              animate: true,
              concentric: (node: { data: (key: string) => string }) => {
                const type = node.data("type");
                return type === "skill" ? 3 : type === "technology" ? 2 : 1;
              },
              levelWidth: () => 1,
              padding: 40,
            }
          : name === "breadthfirst"
          ? {
              name: "breadthfirst",
              animate: true,
              directed: true,
              padding: 40,
              spacingFactor: 1.2,
            }
          : {
              name: "circle",
              animate: true,
              padding: 40,
            };

      cy.layout(layoutOptions).run();
    },
    []
  );

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const cytoscapeElements = [
      ...filteredNodes.map((n) => ({
        group: "nodes" as const,
        data: {
          id: n.id,
          label: n.name,
          type: n.type,
          category: n.domain_or_category || "",
        },
      })),
      ...filteredEdges.map((e) => ({
        group: "edges" as const,
        data: {
          id: `e-${e.source_id}-${e.target_id}-${e.relation_type}`,
          source: e.source_id,
          target: e.target_id,
          label: e.relation_type,
        },
      })),
    ];

    cy.elements().remove();
    cy.add(cytoscapeElements);

    if (cytoscapeElements.length > 0) {
      runLayout(layoutName);
    }
  }, [filteredNodes, filteredEdges, layoutName, runLayout]);

  // Synchronize external selection with Cytoscape visual selection
  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    cy.elements().unselect();
    if (selectedNode) {
      const el = cy.getElementById(selectedNode.id);
      if (el.nonempty()) el.select();
    } else if (selectedEdge) {
      const edgeId = `e-${selectedEdge.source_id}-${selectedEdge.target_id}-${selectedEdge.relation_type}`;
      const el = cy.getElementById(edgeId);
      if (el.nonempty()) el.select();
    }
  }, [selectedNode, selectedEdge]);

  // Zoom / Pan helper handlers
  const handleZoomIn = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  const handleZoomOut = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({ level: cy.zoom() * 0.77, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } });
  };

  const handleFit = () => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.fit(undefined, 35);
  };

  const handleReset = () => {
    runLayout(layoutName);
  };

  return (
    <div className={`relative flex flex-col rounded-xl border border-slate-800/80 bg-[#090d16] overflow-hidden ${className || ""}`}>
      {/* Canvas top control toolbar */}
      <div className="flex flex-wrap items-center justify-between gap-2 px-4 py-2.5 border-b border-slate-800/60 bg-slate-900/60">
        <div className="flex items-center gap-3">
          <span className="text-xs font-medium text-slate-300">Layout:</span>
          {(["cose", "concentric", "breadthfirst", "circle"] as const).map((l) => (
            <button
              key={l}
              onClick={() => {
                setLayoutName(l);
                runLayout(l);
              }}
              className={`px-2.5 py-1 text-xs font-mono rounded capitalize transition-all ${
                layoutName === l
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {l === "cose" ? "Force (CoSE)" : l}
            </button>
          ))}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-full bg-[#06b6d4]" aria-hidden="true" />
            <span className="text-slate-400 font-mono text-[11px]">Skill</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rounded-sm bg-[#10b981]" aria-hidden="true" />
            <span className="text-slate-400 font-mono text-[11px]">Technology</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="h-2.5 w-2.5 rotate-45 rounded-xs bg-[#a855f7]" aria-hidden="true" />
            <span className="text-slate-400 font-mono text-[11px]">Concept</span>
          </div>
        </div>
      </div>

      {/* Main Cytoscape canvas container */}
      <div
        ref={containerRef}
        className="w-full h-[450px] md:h-[520px] bg-[#090d16] cursor-grab active:cursor-grabbing focus:outline-none"
        tabIndex={0}
        aria-label="Interactive SkillGraph Canvas. Use mouse or touch to pan and zoom. Click nodes or edges to view details."
      />

      {/* Floating Canvas Controls */}
      <div className="absolute bottom-4 right-4 flex items-center gap-1 bg-slate-900/90 border border-slate-700/60 rounded-lg p-1 backdrop-blur-md shadow-lg">
        <Button
          variant="ghost"
          size="sm"
          onClick={handleZoomIn}
          aria-label="Zoom in"
          className="h-8 w-8 p-0"
        >
          <Plus className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleZoomOut}
          aria-label="Zoom out"
          className="h-8 w-8 p-0"
        >
          <Minus className="h-4 w-4" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleFit}
          aria-label="Fit to view"
          className="h-8 w-8 p-0"
        >
          <Maximize2 className="h-3.5 w-3.5" />
        </Button>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleReset}
          aria-label="Reset layout"
          className="h-8 w-8 p-0"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Bottom status line */}
      <div className="flex items-center justify-between px-4 py-2 border-t border-slate-800/60 bg-slate-900/40 text-xs text-slate-500 font-mono">
        <span>
          Showing {filteredNodes.length} nodes · {filteredEdges.length} edges
        </span>
        <span className="text-[11px] text-slate-500 hidden sm:inline">
          Click node or edge to inspect details · Drag canvas to pan · Scroll to zoom
        </span>
      </div>
    </div>
  );
}
