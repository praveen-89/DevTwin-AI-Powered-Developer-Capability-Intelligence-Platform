"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import type { EvidenceResponse } from "@/types/api";
import { Shell, PageContainer } from "@/components/layout/shell";
import { PageHeroBanner } from "@/components/layout/page-hero-banner";
import { PageExplainer } from "@/components/dashboard/page-explainer";
import { BreakdownChart, type BreakdownDatum } from "@/components/dashboard/breakdown-chart";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { Activity, FileText } from "lucide-react";
import { StaggerItem } from "@/components/ui/stagger-item";

const EVIDENCE_TYPES = ["ALL", "MENTION", "USAGE", "APPLIED_ENGINEERING", "DEMONSTRATED_OUTCOME"];

export function EvidenceView() {
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

  const typeChartData: BreakdownDatum[] = useMemo(() => {
    const counts: Record<string, number> = {
      MENTION: 0,
      USAGE: 0,
      APPLIED_ENGINEERING: 0,
      DEMONSTRATED_OUTCOME: 0,
    };
    for (const ev of evidence) {
      if (counts[ev.type] != null) counts[ev.type] += 1;
    }
    return [
      { label: "Mention", value: counts.MENTION, color: "#60a5fa" },
      { label: "Usage", value: counts.USAGE, color: "#06b6d4" },
      { label: "Applied Engineering", value: counts.APPLIED_ENGINEERING, color: "#34d399" },
      { label: "Demonstrated Outcome", value: counts.DEMONSTRATED_OUTCOME, color: "#a78bfa" },
    ];
  }, [evidence]);

  return (
    <Shell pageTitle="Evidence">
      <PageContainer>
        <PageHeroBanner
          badge="Verifiable Ground Truth"
          title="Evidence Explorer & Provenance"
          description="Contextualized evidence items extracted from repository analysis runs. Every capability score traces directly to source code observations with strength, directness, and polarity weights."
          visualType="evidence"
          actions={
            <div className="flex items-center gap-2">
              <Link href="/capabilities">
                <Button variant="primary" size="sm">
                  Capabilities
                </Button>
              </Link>
              <Link href="/repositories">
                <Button variant="outline" size="sm">
                  Repositories
                </Button>
              </Link>
            </div>
          }
          stats={[
            { label: "Evidence Items", value: total, variant: "accent" },
            { label: "Provenance", value: "100% Traceable", variant: "success" },
            { label: "Polarity", value: "Weighted (+ / -)", variant: "purple" },
          ]}
        />

        <PageExplainer
          pageKey="evidence"
          description="Every individual observation DevTwin extracted from your code that supports (or counts against) a skill, technology, or concept. Each capability score on the Capabilities page is built by aggregating rows like these."
          terms={[
            { term: "Type", definition: "MENTION (referenced in passing) → USAGE (actually imported/used) → APPLIED_ENGINEERING (used with tests/rigor) → DEMONSTRATED_OUTCOME (highest tier) — how strong a signal this observation is." },
            { term: "Polarity", definition: "Positive evidence supports the skill; negative evidence (e.g. a risk finding) counts against it." },
            { term: "Strength", definition: "How substantial this one piece of evidence is on its own (0–1)." },
            { term: "Directness", definition: "How directly this observation demonstrates the skill, versus being incidental (0–1)." },
            { term: "Date / Recency", definition: "When this evidence was observed. Older evidence counts for less — its weight decays with a 365-day half-life." },
          ]}
        />

        <BreakdownChart
          title="Evidence by Type"
          data={typeChartData}
          valueLabel="items"
          emptyMessage="No evidence yet. Run an analysis to populate this chart."
        />

        {/* Type filter */}
        <div className="flex flex-wrap gap-1 p-1 bg-slate-100 dark:bg-slate-800/40 rounded-lg w-fit" role="tablist">
          {EVIDENCE_TYPES.map((t) => (
            <button
              key={t}
              role="tab"
              aria-selected={typeFilter === t}
              onClick={() => { setTypeFilter(t); setLoading(true); setError(null); }}
              className={`px-2.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                typeFilter === t
                  ? "bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30"
                  : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
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
                <Activity className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden="true" />
                Evidence Items
              </CardTitle>
            </CardHeader>
            <div className="overflow-x-auto">
              <table className="w-full text-xs" aria-label="Evidence items">
                <thead>
                  <tr className="border-b border-slate-200 dark:border-slate-800/50 bg-slate-50 dark:bg-slate-900/40">
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
                  {evidence.map((ev, idx) => {
                    const targets = [
                      ...ev.skills.map((s) => s.name),
                      ...ev.technologies.map((t) => t.name),
                    ].slice(0, 3);
                    return (
                      <StaggerItem
                        as="tr"
                        key={ev.id}
                        index={idx}
                        className="border-b border-slate-100 dark:border-slate-800/30 last:border-0 hover:bg-slate-100 dark:hover:bg-slate-800/20 transition-colors"
                      >
                        <td className="px-4 py-2.5">
                          <Badge variant="muted">{ev.type.replace(/_/g, " ")}</Badge>
                        </td>
                        <td className="px-4 py-2.5">
                          <Badge variant={polarityVariant(ev.polarity)}>
                            {polarityLabel(ev.polarity)}
                          </Badge>
                        </td>
                        <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 font-mono tabular-nums">
                          {ev.strength.toFixed(2)}
                        </td>
                        <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 font-mono tabular-nums">
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
                              <span className="text-slate-400 dark:text-slate-600">—</span>
                            )}
                          </div>
                        </td>
                        <td className="px-4 py-2.5 hidden lg:table-cell">
                          {ev.provenance?.file_path ? (
                            <span className="flex items-center gap-1 text-slate-500 dark:text-slate-400 font-mono">
                              <FileText className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                              <span className="truncate max-w-[140px]" title={ev.provenance.file_path}>
                                {ev.provenance.file_path}
                                {ev.provenance.line_start != null && (
                                  <span className="text-slate-400 dark:text-slate-600">:{ev.provenance.line_start}</span>
                                )}
                              </span>
                            </span>
                          ) : (
                            <span className="text-slate-400 dark:text-slate-600">—</span>
                          )}
                        </td>
                        <td className="px-4 py-2.5 text-slate-500 hidden xl:table-cell whitespace-nowrap">
                          {formatDate(ev.recency)}
                        </td>
                      </StaggerItem>
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
