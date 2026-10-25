"use client";

import type { SkillGraphNodeResponse, SkillGraphEdgeResponse } from "@/types/api";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { GitBranch, Network, X, ArrowRight, ExternalLink } from "lucide-react";
import Link from "next/link";

interface SkillGraphDetailProps {
  selectedNode: SkillGraphNodeResponse | null;
  selectedEdge: SkillGraphEdgeResponse | null;
  allEdges: SkillGraphEdgeResponse[];
  onClear: () => void;
  onSelectNodeById: (nodeId: string) => void;
}

export function SkillGraphDetail({
  selectedNode,
  selectedEdge,
  allEdges,
  onClear,
  onSelectNodeById,
}: SkillGraphDetailProps) {
  if (!selectedNode && !selectedEdge) {
    return (
      <Card className="h-full">
        <CardHeader>
          <CardTitle as="h4" className="text-xs uppercase tracking-wider text-slate-400">
            Inspector
          </CardTitle>
        </CardHeader>
        <CardBody className="text-center py-10 px-4">
          <Network className="h-8 w-8 text-slate-600 mx-auto mb-3" aria-hidden="true" />
          <p className="text-xs text-slate-400 max-w-xs mx-auto">
            Click on any taxonomy node or relationship edge in the canvas to inspect its metadata and provenance.
          </p>
        </CardBody>
      </Card>
    );
  }

  if (selectedNode) {
    const connectedEdges = allEdges.filter(
      (e) => e.source_id === selectedNode.id || e.target_id === selectedNode.id
    );

    return (
      <Card className="h-full border-cyan-500/30">
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2 min-w-0">
              <Badge
                variant={
                  selectedNode.type === "skill"
                    ? "accent"
                    : selectedNode.type === "technology"
                    ? "success"
                    : "info"
                }
              >
                {selectedNode.type}
              </Badge>
              <CardTitle as="h4" className="text-sm font-semibold text-slate-100 truncate">
                {selectedNode.name}
              </CardTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              aria-label="Close inspector"
              className="h-6 w-6 p-0 text-slate-400 hover:text-slate-200"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardBody className="space-y-4 text-xs">
          {/* Metadata dl */}
          <dl className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-xs bg-slate-900/60 p-3 rounded-lg border border-slate-800/60">
            <dt className="text-slate-500">Domain / Category</dt>
            <dd className="text-slate-200 font-medium">
              {selectedNode.domain_or_category || "General"}
            </dd>
            <dt className="text-slate-500">Node ID</dt>
            <dd className="font-mono text-slate-400 truncate" title={selectedNode.id}>
              {selectedNode.id}
            </dd>
            <dt className="text-slate-500">Connections</dt>
            <dd className="text-slate-200 font-mono">{connectedEdges.length}</dd>
          </dl>

          {/* Connected Relationships */}
          <div>
            <h5 className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Connected Relationships ({connectedEdges.length})
            </h5>
            {connectedEdges.length === 0 ? (
              <p className="text-xs text-slate-500 italic">No direct relationships in this run.</p>
            ) : (
              <ul className="space-y-1.5 max-h-48 overflow-y-auto pr-1">
                {connectedEdges.map((e, idx) => {
                  const isSource = e.source_id === selectedNode.id;
                  const otherId = isSource ? e.target_id : e.source_id;
                  const otherName = isSource ? e.target_name : e.source_name;
                  return (
                    <li
                      key={idx}
                      className="flex items-center justify-between p-2 rounded bg-slate-900/40 border border-slate-800/40 text-xs"
                    >
                      <div className="flex items-center gap-1.5 min-w-0">
                        <span className="text-slate-400 font-mono text-[11px]">
                          {isSource ? "Outgoing" : "Incoming"}
                        </span>
                        <span className="text-cyan-400 font-mono text-[10px] px-1 py-0.5 rounded bg-cyan-950/40 border border-cyan-800/40">
                          {e.relation_type}
                        </span>
                        <ArrowRight className="h-3 w-3 text-slate-600 flex-shrink-0" />
                        <button
                          onClick={() => onSelectNodeById(otherId)}
                          className="text-slate-200 hover:text-cyan-300 font-medium truncate text-left underline underline-offset-2 decoration-slate-700 hover:decoration-cyan-400"
                        >
                          {otherName}
                        </button>
                      </div>
                    </li>
                  );
                })}
              </ul>
            )}
          </div>

          {/* Cross-view Link to Evidence */}
          <div className="pt-2 border-t border-slate-800/60">
            <Link
              href={`/evidence?target_id=${encodeURIComponent(selectedNode.id)}`}
              className="inline-flex items-center gap-1.5 text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              <ExternalLink className="h-3.5 w-3.5" />
              <span>Explore Supporting Evidence ↗</span>
            </Link>
          </div>
        </CardBody>
      </Card>
    );
  }

  if (selectedEdge) {
    return (
      <Card className="h-full border-cyan-500/30">
        <CardHeader>
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-2 min-w-0">
              <GitBranch className="h-4 w-4 text-cyan-400 flex-shrink-0" />
              <CardTitle as="h4" className="text-sm font-semibold text-slate-100 truncate">
                Relationship
              </CardTitle>
            </div>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClear}
              aria-label="Close inspector"
              className="h-6 w-6 p-0 text-slate-400 hover:text-slate-200"
            >
              <X className="h-3.5 w-3.5" />
            </Button>
          </div>
        </CardHeader>
        <CardBody className="space-y-4 text-xs">
          <div className="bg-slate-900/60 p-3 rounded-lg border border-slate-800/60 space-y-3">
            <div className="text-center">
              <Badge variant="accent" className="font-mono text-xs">
                {selectedEdge.relation_type}
              </Badge>
            </div>
            <div className="flex items-center justify-between gap-2 pt-2 border-t border-slate-800/60 text-xs">
              <button
                onClick={() => onSelectNodeById(selectedEdge.source_id)}
                className="text-slate-200 hover:text-cyan-300 font-mono font-medium truncate max-w-[45%] underline underline-offset-2 decoration-slate-700 hover:decoration-cyan-400"
                title={selectedEdge.source_name}
              >
                {selectedEdge.source_name}
              </button>
              <ArrowRight className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
              <button
                onClick={() => onSelectNodeById(selectedEdge.target_id)}
                className="text-slate-200 hover:text-cyan-300 font-mono font-medium truncate max-w-[45%] text-right underline underline-offset-2 decoration-slate-700 hover:decoration-cyan-400"
                title={selectedEdge.target_name}
              >
                {selectedEdge.target_name}
              </button>
            </div>
          </div>

          <p className="text-xs text-slate-400 leading-relaxed">
            This directed relationship was mapped deterministically from mined AST imports, package manifests, or taxonomy hierarchies in the repository analysis.
          </p>
        </CardBody>
      </Card>
    );
  }

  return null;
}
