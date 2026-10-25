"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import type { EvidenceResponse } from "@/types/api";
import { Shell, PageContainer, PageHeading } from "@/components/layout/shell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { Activity, FileText } from "lucide-react";

const EVIDENCE_TYPES = ["ALL", "MENTION", "USAGE", "APPLIED_ENGINEERING", "DEMONSTRATED_OUTCOME"];

export default function EvidencePage() {
  const { token } = useAuth();
  const [evidence, setEvidence] = useState<EvidenceResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [typeFilter, setTypeFilter] = useState("ALL");

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    const params = typeFilter !== "ALL"
      ? { evidence_type: typeFilter, limit: 50 }
      : { limit: 50 };
    apiClient.getEvidence(params)
      .then((data) => { setEvidence(data.items); setTotal(data.total); })
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Failed to load evidence."))
      .finally(() => setLoading(false));
  }, [token, typeFilter]);

  function polarityLabel(polarity: number): string {
    if (polarity > 0.1) return "Positive";
    if (polarity < -0.1) return "Negative";
    return "Neutral";
  }

  function polarityVariant(polarity: number): "success" | "danger" | "muted" {
    if (polarity > 0.1) return "success";
    if (polarity < -0.1) return "danger";
    return "muted";
  }

  return (
    <Shell pageTitle="Evidence">
      <PageContainer>
        <PageHeading
          title="Evidence"
          description="Raw evidence items extracted from repository analysis. Each item contributes to one or more capability scores."
          actions={total > 0 ? <Badge variant="muted">{total} items</Badge> : undefined}
        />

        {/* Type filter */}
        <div className="flex flex-wrap gap-1 p-1 bg-slate-800/40 rounded-lg w-fit" role="tablist">
          {EVIDENCE_TYPES.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={typeFilter === t}
              onClick={() => { setTypeFilter(t); setLoading(true); setError(null); }}
              className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                typeFilter === t
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/30"
                  : "text-slate-400 hover:text-slate-200"
              }`}
            >
              {t === "ALL" ? "All" : t.replace(/_/g, " ")}
            </button>
          ))}
        </div>

        {!token && <EmptyState description="Sign in to view evidence." />}
        {loading && <CardSkeleton lines={5} />}
        {error && <InlineError message={error} />}

        {!loading && evidence.length === 0 && token && !error && (
          <EmptyState
            variant="no-data"
            description="No evidence found. Run an analysis to generate evidence items."
          />
        )}

        {!loading && evidence.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle as="h3" className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-slate-400" aria-hidden="true" />
                Evidence Items
              </CardTitle>
            </CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-xs" aria-label="Evidence items">
                <thead>
                  <tr className="border-b border-slate-800/50 bg-slate-900/40">
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Type</th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Polarity</th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Strength</th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Directness</th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Skills/Technologies</th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium hidden lg:table-cell">File</th>
                    <th className="text-left px-4 py-2.5 text-slate-500 font-medium hidden xl:table-cell">Date</th>
                  </tr>
                </thead>
                <tbody>
                  {evidence.map((ev) => {
                    const targets = [
                      ...ev.skills.map((s) => s.name),
                      ...ev.technologies.map((t) => t.name),
                    ].slice(0, 3);
                    return (
                      <tr
                        key={ev.id}
                        className="border-b border-slate-800/30 last:border-0 hover:bg-slate-800/20 transition-colors"
                      >
                        <td className="px-4 py-2.5">
                          <Badge variant="muted">{ev.type.replace(/_/g, " ")}</Badge>
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge variant={polarityVariant(ev.polarity)}>
                            {polarityLabel(ev.polarity)}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-slate-300 font-mono tabular-nums">
                          {ev.strength.toFixed(2)}
                        </td>
                        <td className="px-4 py-2.5 text-slate-300 font-mono tabular-nums">
                          {ev.directness.toFixed(2)}
                        </td>
                        <td className="px-4 py-2.5">
                          <div className="flex flex-wrap gap-1">
                            {targets.length > 0 ? (
                              targets.map((name) => (
                                <Badge key={name} variant="accent" className="text-xs">
                                  {name}
                                </Badge>
                              ))
                            ) : (
                              <span className="text-slate-600">—</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 hidden lg:table-cell">
                          {ev.provenance?.file_path ? (
                            <span className="flex items-center gap-1 text-slate-400 font-mono">
                              <FileText className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                              <span className="truncate max-w-[140px]" title={ev.provenance.file_path}>
                                {ev.provenance.file_path}
                                {ev.provenance.line_start != null && (
                                  <span className="text-slate-600">:{ev.provenance.line_start}</span>
                                )}
                              </span>
                            </span>
                          ) : (
                            <span className="text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 hidden xl:table-cell whitespace-nowrap">
                          {formatDate(ev.recency)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
            {total > 50 && (
              <CardBody>
                <p className="text-xs text-slate-500 text-center">
                  Showing 50 of {total} items. Pagination coming soon.
                </p>
              </CardBody>
            )}
          </Card>
        )}
      </PageContainer>
    </Shell>
  );
}
