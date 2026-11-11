"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import type { RiskFindingResponse, RepositoryResponse } from "@/types/api";
import { Shell, PageContainer, PageHeading } from "@/components/layout/shell";
import { Card, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, SeverityBadge } from "@/components/ui/badge";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { formatDate } from "@/lib/utils";
import { Code2, FileText } from "lucide-react";

export default function CodeRiskPage() {
  const { token } = useAuth();
  const [repos, setRepos] = useState<RepositoryResponse[]>([]);
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [risks, setRisks] = useState<RiskFindingResponse[]>([]);
  const [total, setTotal] = useState(0);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingRisks, setLoadingRisks] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [severityFilter, setSeverityFilter] = useState<string>("ALL");

  useEffect(() => {
    if (!token) { setLoadingRepos(false); return; }
    apiClient.getRepositories()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) setSelectedRepoId(data[0].id);
      })
      .catch(() => setError("Could not load repositories."))
      .finally(() => setLoadingRepos(false));
  }, [token]);

  useEffect(() => {
    if (!selectedRepoId) return;
    setLoadingRisks(true);
    setError(null);
    const params = severityFilter !== "ALL" ? { severity: severityFilter, limit: 50 } : { limit: 50 };
    apiClient.getRepositoryRisks(selectedRepoId, params)
      .then((data) => { setRisks(data.items); setTotal(data.total); })
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Failed to load risk findings."))
      .finally(() => setLoadingRisks(false));
  }, [selectedRepoId, severityFilter]);

  // Severity summary
  const counts = (risks ?? []).reduce<Record<string, number>>((acc, r) => {
    acc[r.severity] = (acc[r.severity] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Shell pageTitle="CodeRisk">
      <PageContainer>
        <PageHeading
          title="CodeRisk Analysis"
          description="Static risk findings extracted from repository analysis runs. Findings are scoped to the selected repository."
          actions={total > 0 ? <Badge variant="muted">{total} findings</Badge> : undefined}
        />

        {!token && <EmptyState description="Sign in to view CodeRisk findings." />}
        {loadingRepos && <CardSkeleton lines={3} />}

        {repos.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-4 gap-5">
            {/* Repo selector */}
            <Card className="lg:col-span-1">
              <CardHeader>
                <CardTitle as="h2" className="text-xs">Repositories</CardTitle>
              </CardHeader>
              <ul>
                {repos.map((repo) => (
                  <li key={repo.id}>
                    <button
                      onClick={() => setSelectedRepoId(repo.id)}
                      className={`w-full text-left px-4 py-2.5 text-xs font-mono border-b border-slate-800/40 last:border-0 transition-colors truncate ${
                        selectedRepoId === repo.id ? "text-cyan-300 bg-cyan-500/8" : "text-slate-400 hover:bg-slate-800/30"
                      }`}
                    >
                      {repo.full_name}
                    </button>
                  </li>
                ))}
              </ul>
            </Card>

            {/* Findings */}
            <div className="lg:col-span-3 space-y-5">
              {/* Summary row */}
              {risks.length > 0 && (
                <div className="flex flex-wrap gap-3">
                  {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) => (
                    <button
                      key={sev}
                      onClick={() => setSeverityFilter(severityFilter === sev ? "ALL" : sev)}
                      className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs transition-all ${
                        severityFilter === sev
                          ? "border-cyan-500/40 bg-cyan-500/8"
                          : "border-slate-700/50 hover:border-slate-600"
                      }`}
                    >
                      <SeverityBadge severity={sev} />
                      <span className="font-mono text-slate-300">{counts[sev] ?? 0}</span>
                    </button>
                  ))}
                  {severityFilter !== "ALL" && (
                    <button
                      onClick={() => setSeverityFilter("ALL")}
                      className="text-xs text-slate-500 hover:text-slate-300 underline"
                    >
                      Clear filter
                    </button>
                  )}
                </div>
              )}

              {error && <InlineError message={error} />}
              {loadingRisks && <CardSkeleton lines={5} />}

              {!loadingRisks && risks.length === 0 && !error && (
                <EmptyState
                  variant="no-data"
                  description={
                    severityFilter !== "ALL"
                      ? `No ${severityFilter} findings for this repository.`
                      : "No risk findings for this repository. Run an analysis to generate CodeRisk data."
                  }
                />
              )}

              {!loadingRisks && risks.length > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle as="h3" className="flex items-center gap-2">
                      <Code2 className="h-4 w-4 text-slate-400" aria-hidden="true" />
                      Findings
                    </CardTitle>
                  </CardHeader>
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs" aria-label="Risk findings">
                      <thead>
                        <tr className="border-b border-slate-800/50 bg-slate-900/40">
                          <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Severity</th>
                          <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Category</th>
                          <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Type</th>
                          <th className="text-left px-4 py-2.5 text-slate-500 font-medium">Confidence</th>
                          <th className="text-left px-4 py-2.5 text-slate-500 font-medium hidden md:table-cell">Location</th>
                          <th className="text-left px-4 py-2.5 text-slate-500 font-medium hidden lg:table-cell">Detected</th>
                        </tr>
                      </thead>
                      <tbody>
                        {risks.map((risk) => (
                          <tr key={risk.id} className="border-b border-slate-800/30 last:border-0 hover:bg-slate-800/20 transition-colors">
                            <td className="px-4 py-2.5"><SeverityBadge severity={risk.severity} /></td>
                            <td className="px-4 py-2.5 text-slate-400">{risk.category}</td>
                            <td className="px-4 py-2.5 text-slate-200 font-mono">{risk.risk_type}</td>
                            <td className="px-4 py-2.5 text-slate-300 font-mono">{Math.round(risk.confidence * 100)}%</td>
                            <td className="px-4 py-2.5 hidden md:table-cell">
                              {risk.file_path ? (
                                <span className="flex items-center gap-1 text-slate-400">
                                  <FileText className="h-3 w-3 flex-shrink-0" aria-hidden="true" />
                                  <span className="font-mono truncate max-w-[180px]" title={risk.file_path}>
                                    {risk.file_path}
                                    {risk.line_start != null && <span className="text-slate-600">:{risk.line_start}</span>}
                                  </span>
                                </span>
                              ) : (
                                <span className="text-slate-600">—</span>
                              )}
                            </td>
                            <td className="px-4 py-2.5 text-slate-500 hidden lg:table-cell">{formatDate(risk.detected_at)}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}
            </div>
          </div>
        )}
      </PageContainer>
    </Shell>
  );
}
