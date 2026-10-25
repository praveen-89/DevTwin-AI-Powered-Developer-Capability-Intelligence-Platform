"use client";

import { useMemo } from "react";
import type { CapabilityHistoryItemResponse, CapabilityTargetResponse } from "@/types/api";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, ConfidenceBadge } from "@/components/ui/badge";
import { ScorePill } from "@/components/ui/score-gauge";
import { formatDate, formatScore } from "@/lib/utils";
import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from "recharts";
import { AlertTriangle, Clock, History, TrendingUp } from "lucide-react";

interface CapabilityHistoryChartProps {
  selectedTarget: CapabilityTargetResponse | null;
  historyItems: CapabilityHistoryItemResponse[];
  totalSnapshots: number;
  loading: boolean;
  error: string | null;
  className?: string;
}

export function CapabilityHistoryChart({
  selectedTarget,
  historyItems,
  totalSnapshots,
  loading,
  error,
  className,
}: CapabilityHistoryChartProps) {
  // Sort chronological order for the time series
  const sortedItems = useMemo(() => {
    return [...historyItems].sort((a, b) => {
      const ta = new Date(a.recorded_at).getTime();
      const tb = new Date(b.recorded_at).getTime();
      return ta - tb;
    });
  }, [historyItems]);

  // Chart data points
  const chartData = useMemo(() => {
    return sortedItems.map((item, idx) => {
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
    });
  }, [sortedItems]);

  if (!selectedTarget) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle as="h3" className="flex items-center gap-2">
            <History className="h-4 w-4 text-slate-400" aria-hidden="true" />
            Capability Score History
          </CardTitle>
        </CardHeader>
        <CardBody className="py-12 text-center">
          <Clock className="h-8 w-8 text-slate-600 mx-auto mb-3" aria-hidden="true" />
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Select a capability target from the cards below to visualize its historical scoring snapshots and confidence intervals over time.
          </p>
        </CardBody>
      </Card>
    );
  }

  return (
    <Card className={`border-slate-700/80 ${className || ""}`}>
      <CardHeader>
        <div className="flex flex-wrap items-center justify-between gap-3 w-full">
          <div className="flex items-center gap-2.5 min-w-0">
            <div className="rounded-lg bg-cyan-500/10 p-1.5 border border-cyan-500/20 flex-shrink-0">
              <TrendingUp className="h-4 w-4 text-cyan-400" aria-hidden="true" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <CardTitle as="h3" className="text-sm font-semibold text-slate-100">
                  {selectedTarget.target_name}
                </CardTitle>
                <Badge variant="accent" className="capitalize text-xs">
                  {selectedTarget.target_type}
                </Badge>
              </div>
              <p className="text-xs text-slate-400">
                {selectedTarget.domain_or_category || "General"} · {totalSnapshots} recorded snapshots
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Badge variant="muted" className="text-xs font-mono">
              Scale: 0.0 – 1.0 (0% – 100%)
            </Badge>
          </div>
        </div>
      </CardHeader>

      <CardBody className="space-y-5">
        {/* Run-scoped comparability notice */}
        <div className="flex items-start gap-2.5 rounded-lg border border-amber-500/20 bg-amber-500/8 px-3.5 py-2.5 text-xs text-amber-300">
          <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
          <div className="space-y-0.5">
            <span className="font-semibold">Run-Scoped History:</span> Each snapshot records capability evidence extracted within a specific repository analysis run. While snapshots for this target are plotted sequentially, they reflect discrete run observations rather than a continuous cross-repository aggregate.
          </div>
        </div>

        {error && (
          <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3 font-mono">
            {error}
          </p>
        )}

        {loading ? (
          <div className="h-64 flex items-center justify-center bg-slate-900/30 rounded-lg border border-slate-800/40">
            <div className="text-xs text-slate-400 font-mono animate-pulse">
              Loading capability history...
            </div>
          </div>
        ) : chartData.length === 0 ? (
          <div className="h-56 flex flex-col items-center justify-center text-center p-6 bg-slate-900/20 rounded-lg border border-slate-800/40">
            <History className="h-7 w-7 text-slate-600 mb-2" aria-hidden="true" />
            <p className="text-xs text-slate-300 font-medium">No Historical Snapshots</p>
            <p className="text-xs text-slate-500 max-w-xs mt-1">
              Historical records are created with each analysis run. Run additional repository analyses to track score progression.
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Recharts Temporal Line Chart */}
            <div className="h-64 w-full bg-slate-900/40 rounded-xl p-3 border border-slate-800/60">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={chartData}
                  margin={{ top: 15, right: 25, left: -10, bottom: 5 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" vertical={false} />
                  <XAxis
                    dataKey="timeLabel"
                    stroke="#64748b"
                    fontSize={11}
                    fontFamily="monospace"
                    tickLine={false}
                  />
                  <YAxis
                    domain={[0, 1]}
                    ticks={[0, 0.25, 0.5, 0.75, 1.0]}
                    tickFormatter={(v) => `${Math.round(v * 100)}%`}
                    stroke="#64748b"
                    fontSize={11}
                    fontFamily="monospace"
                    tickLine={false}
                  />
                  <ReferenceLine
                    y={0.5}
                    stroke="#334155"
                    strokeDasharray="2 2"
                    label={{ value: "Baseline", fill: "#475569", fontSize: 10, position: "insideTopRight" }}
                  />
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload || !payload.length) return null;
                      const data = payload[0].payload;
                      return (
                        <div className="rounded-lg bg-[#0b1120] border border-slate-700/80 p-3 shadow-xl text-xs space-y-1.5 min-w-[210px] backdrop-blur-md">
                          <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
                            {data.targetName}
                          </p>
                          <div className="flex justify-between text-slate-400">
                            <span>Score:</span>
                            <span className="font-mono text-cyan-400 font-semibold">
                              {formatScore(data.score)} ({data.score})
                            </span>
                          </div>
                          <div className="flex justify-between text-slate-400">
                            <span>Confidence:</span>
                            <span className="font-mono text-emerald-400">
                              {formatScore(data.confidence)}
                            </span>
                          </div>
                          <div className="flex justify-between text-slate-400">
                            <span>Recorded:</span>
                            <span className="text-slate-300">{formatDate(data.rawTime)}</span>
                          </div>
                          {data.runId && (
                            <div className="flex justify-between text-slate-400 pt-1 border-t border-slate-800/80 font-mono text-[10px]">
                              <span>Run ID:</span>
                              <span className="text-slate-500">{data.runId.slice(0, 8)}…</span>
                            </div>
                          )}
                        </div>
                      );
                    }}
                  />
                  <Line
                    type="monotone"
                    dataKey="score"
                    name="Capability Score"
                    stroke="#06b6d4"
                    strokeWidth={2.5}
                    dot={{ fill: "#06b6d4", r: 4, strokeWidth: 2, stroke: "#090d16" }}
                    activeDot={{ fill: "#38bdf8", r: 6, stroke: "#0891b2", strokeWidth: 2 }}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>

            {/* Snapshot Records Table */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs">
                <h4 className="font-semibold text-slate-300">Historical Snapshot Log</h4>
                {totalSnapshots > historyItems.length && (
                  <span className="text-slate-500 font-mono text-[11px]">
                    Showing latest {historyItems.length} of {totalSnapshots} snapshots
                  </span>
                )}
              </div>
              <div className="overflow-x-auto rounded-lg border border-slate-800/60 bg-slate-900/30">
                <table className="w-full text-xs" aria-label="Capability historical snapshots">
                  <thead>
                    <tr className="border-b border-slate-800/60 bg-slate-900/60 text-slate-400 font-medium">
                      <th className="text-left px-3.5 py-2 font-mono">Recorded At</th>
                      <th className="text-left px-3.5 py-2 font-mono">Analysis Run ID</th>
                      <th className="text-left px-3.5 py-2">Score</th>
                      <th className="text-left px-3.5 py-2">Confidence</th>
                      <th className="text-left px-3.5 py-2 font-mono">Version</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedItems.map((snap) => (
                      <tr
                        key={snap.id}
                        className="border-b border-slate-800/30 last:border-0 hover:bg-slate-800/20 transition-colors"
                      >
                        <td className="px-3.5 py-2 font-mono text-slate-300 whitespace-nowrap">
                          {formatDate(snap.recorded_at)}
                        </td>
                        <td className="px-3.5 py-2 font-mono text-slate-400 whitespace-nowrap">
                          {snap.analysis_run_id ? `${snap.analysis_run_id.slice(0, 8)}…` : "—"}
                        </td>
                        <td className="px-3.5 py-2">
                          <ScorePill score={snap.score} />
                        </td>
                        <td className="px-3.5 py-2">
                          <ConfidenceBadge confidence={snap.confidence} />
                        </td>
                        <td className="px-3.5 py-2 font-mono text-slate-500 text-[11px]">
                          {snap.scoring_version}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
