"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import type {
  DeveloperCapabilityResponse,
  CapabilityTargetResponse,
  CapabilityHistoryItemResponse,
} from "@/types/api";
import Link from "next/link";
import { Shell, PageContainer } from "@/components/layout/shell";
import { PageHeroBanner } from "@/components/layout/page-hero-banner";
import { PageExplainer } from "@/components/dashboard/page-explainer";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, ConfidenceBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { ScoreGauge } from "@/components/ui/score-gauge";
import { CapabilityHistoryChart } from "@/components/capabilities/capability-history-chart";
import { formatDate } from "@/lib/utils";
import { BarChart3, AlertTriangle, ChevronRight } from "lucide-react";
import { motion, useReducedMotion } from "motion/react";

type TargetTypeFilter = "all" | "skill" | "technology" | "concept";

export function CapabilitiesView() {
  const { token } = useAuth();
  const reduceMotion = useReducedMotion();
  const [capabilities, setCapabilities] = useState<DeveloperCapabilityResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<TargetTypeFilter>("all");

  // History visualization state
  const [selectedTarget, setSelectedTarget] = useState<CapabilityTargetResponse | null>(null);
  const [historyItems, setHistoryItems] = useState<CapabilityHistoryItemResponse[]>([]);
  const [totalHistory, setTotalHistory] = useState(0);
  const [loadingHistory, setLoadingHistory] = useState(false);
  const [historyError, setHistoryError] = useState<string | null>(null);

  // Fetch capabilities list
  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }
    const params =
      filter !== "all"
        ? { target_type: filter as "skill" | "technology" | "concept", limit: 50 }
        : { limit: 50 };

    apiClient
      .getCapabilities(params)
      .then((data) => {
        setCapabilities(data.items);
        setTotal(data.total);
        if (data.items.length > 0 && !selectedTarget) {
          setSelectedTarget(data.items[0].target);
        }
      })
      .catch((err) =>
        setError(err instanceof ApiError ? err.detail : "Failed to load capabilities.")
      )
      .finally(() => setLoading(false));
  }, [token, filter]); // eslint-disable-line react-hooks/exhaustive-deps

  // Fetch history when selectedTarget changes
  useEffect(() => {
    if (!token || !selectedTarget) return;
    setLoadingHistory(true);
    setHistoryError(null);

    apiClient
      .getCapabilityHistory({ target_id: selectedTarget.target_id, limit: 50 })
      .then((data) => {
        setHistoryItems(data.items);
        setTotalHistory(data.total);
      })
      .catch((err) =>
        setHistoryError(
          err instanceof ApiError ? err.detail : "Failed to load capability history."
        )
      )
      .finally(() => setLoadingHistory(false));
  }, [token, selectedTarget]);

  const grouped = capabilities.reduce<Record<string, DeveloperCapabilityResponse[]>>(
    (acc, cap) => {
      const g = cap.target.domain_or_category ?? "Uncategorised";
      if (!acc[g]) acc[g] = [];
      acc[g].push(cap);
      return acc;
    },
    {}
  );

  return (
    <Shell pageTitle="Capabilities">
      <PageContainer>
        <PageHeroBanner
          badge="Scoring Engine"
          title="Developer Capabilities & History"
          description="Evolving capability scores and temporal history derived from grounded repository evidence, sigmoid aggregation, and half-life temporal decay."
          visualType="capabilities"
          actions={
            <div className="flex items-center gap-2">
              <Link href="/evidence">
                <Button variant="primary" size="sm">
                  View Evidence
                </Button>
              </Link>
              <Link href="/skillgraph">
                <Button variant="outline" size="sm">
                  SkillGraph
                </Button>
              </Link>
            </div>
          }
          stats={[
            { label: "Capabilities", value: total, variant: "accent" },
            { label: "Scoring Model", value: "Sigmoid v1", variant: "purple" },
            { label: "Half-Life Decay", value: "365 Days", variant: "success" },
          ]}
        />

        <PageExplainer
          pageKey="capabilities"
          description="Your evidence-backed capability scores — one per skill, technology, or concept DevTwin detected. Click any card below to see that score's history in the chart above it."
          terms={[
            { term: "Score", definition: "0–1: an aggregate of all evidence found for this skill/technology/concept, weighted by strength, directness, and recency. Higher means stronger demonstrated capability." },
            { term: "Confidence", definition: "0–1: how much evidence backs the score — independent of the score itself. A high score with low confidence means strong but sparse evidence." },
            { term: "Target type", definition: "Skill, Technology, or Concept — the three kinds of capability DevTwin tracks." },
            { term: "Half-life decay", definition: "Evidence loses half its weight every 365 days, so recent activity matters more than old commits." },
            { term: "Scoring version", definition: "Which version of DevTwin's scoring formula produced this snapshot — lets you compare scores fairly across algorithm updates." },
          ]}
        />

        {/* Scoping notice */}
        <div className="flex items-start gap-3 rounded-lg border border-amber-500/20 bg-amber-500/8 px-4 py-3 text-xs text-amber-800 dark:text-amber-200">
          <AlertTriangle className="h-4 w-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div>
            <strong>Run-Scoped Scoring:</strong> Each capability score represents evidence from a
            single repository analysis run. Scores are plotted sequentially across historical runs
            for the same target, but do not assert an unproven cross-repository aggregate.
          </div>
        </div>

        {!token && <EmptyState description="Sign in to view your capability scores." />}

        {loading && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <CardSkeleton lines={5} />
            <CardSkeleton lines={5} />
          </div>
        )}

        {error && <InlineError message={error} />}

        {!loading && capabilities.length === 0 && token && !error && (
          <EmptyState
            variant="no-data"
            description="No capability scores found. Run an analysis on a repository to generate scores."
          />
        )}

        {!loading && capabilities.length > 0 && (
          <div className="space-y-6">
            {/* Interactive Capability History Chart Component */}
            <CapabilityHistoryChart
              selectedTarget={selectedTarget}
              historyItems={historyItems}
              totalSnapshots={totalHistory}
              loading={loadingHistory}
              error={historyError}
            />

            {/* Target Category Filter Tabs */}
            <div className="flex items-center justify-between gap-3 pt-2">
              <div
                className="flex gap-1 p-1 bg-slate-100 dark:bg-slate-800/40 rounded-lg w-fit"
                role="tablist"
                aria-label="Filter by capability type"
              >
                {(["all", "skill", "technology", "concept"] as TargetTypeFilter[]).map((t) => (
                  <button
                    key={t}
                    role="tab"
                    aria-selected={filter === t}
                    onClick={() => {
                      setFilter(t);
                      setLoading(true);
                      setError(null);
                    }}
                    className={`px-3 py-1.5 rounded-md text-xs font-medium transition-all capitalize ${
                      filter === t
                        ? "bg-cyan-500/20 text-cyan-700 dark:text-cyan-300 border border-cyan-500/30"
                        : "text-slate-500 hover:text-slate-800 dark:text-slate-400 dark:hover:text-slate-200"
                    }`}
                  >
                    {t === "all" ? "All Targets" : t}
                  </button>
                ))}
              </div>

              <span className="text-xs text-slate-500 font-mono hidden sm:inline">
                Click any capability below to view its score history above
              </span>
            </div>

            {/* Grouped Capabilities Cards */}
            <div className="space-y-6">
              {Object.entries(grouped).map(([group, caps]) => (
                <Card key={group}>
                  <CardHeader>
                    <CardTitle as="h3" className="flex items-center gap-2">
                      <BarChart3 className="h-4 w-4 text-slate-500 dark:text-slate-400" aria-hidden="true" />
                      {group}
                    </CardTitle>
                    <Badge variant="muted">{caps.length}</Badge>
                  </CardHeader>
                  <CardBody className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {caps.map((cap, idx) => {
                      const isSelected = selectedTarget?.target_id === cap.target.target_id;
                      const motionProps = reduceMotion
                        ? {}
                        : {
                            initial: { opacity: 0, y: 12 },
                            animate: { opacity: 1, y: 0 },
                            transition: {
                              duration: 0.3,
                              delay: Math.min(idx, 10) * 0.04,
                              ease: "easeOut" as const,
                            },
                            whileHover: { scale: 1.015, y: -2 },
                            whileTap: { scale: 0.985 },
                          };
                      return (
                        <motion.div
                          key={cap.id}
                          {...motionProps}
                          onClick={() => setSelectedTarget(cap.target)}
                          className={`p-3.5 rounded-xl border transition-colors cursor-pointer ${
                            isSelected
                              ? "bg-cyan-500/10 border-cyan-500/50 shadow-md shadow-cyan-950/40"
                              : "bg-slate-50 border-slate-200 hover:border-slate-300 hover:bg-slate-100 dark:bg-slate-900/40 dark:border-slate-800/60 dark:hover:border-slate-700 dark:hover:bg-slate-800/30"
                          }`}
                          role="button"
                          tabIndex={0}
                          aria-label={`Select ${cap.target.target_name} to view capability history`}
                          onKeyDown={(e) => {
                            if (e.key === "Enter" || e.key === " ") {
                              e.preventDefault();
                              setSelectedTarget(cap.target);
                            }
                          }}
                        >
                          <div className="flex items-start justify-between gap-2 mb-2">
                            <div className="min-w-0">
                              <span className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate block">
                                {cap.target.target_name}
                              </span>
                              <span className="text-xs text-slate-500 dark:text-slate-400 capitalize">
                                {cap.target.target_type}
                              </span>
                            </div>
                            <div className="flex items-center gap-1.5 flex-shrink-0">
                              {isSelected ? (
                                <Badge variant="accent" className="text-[10px] font-mono">
                                  Viewing History
                                </Badge>
                              ) : (
                                <ChevronRight className="h-4 w-4 text-slate-400 dark:text-slate-600" />
                              )}
                            </div>
                          </div>

                          <ScoreGauge
                            score={cap.score}
                            confidence={cap.confidence}
                            label={cap.target.target_name}
                            className="mb-2"
                          />

                          <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-200 dark:border-slate-800/40">
                            <ConfidenceBadge confidence={cap.confidence} />
                            <span className="text-slate-500 font-mono text-[11px]">
                              {formatDate(cap.updated_at)}
                            </span>
                          </div>
                        </motion.div>
                      );
                    })}
                  </CardBody>
                </Card>
              ))}
            </div>
          </div>
        )}
      </PageContainer>
    </Shell>
  );
}
