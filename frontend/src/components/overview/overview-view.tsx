"use client";

/**
 * DevTwin — Overview Dashboard
 * Displays a real-data summary from the Step 6J APIs.
 * All displayed values come from actual backend responses.
 * Missing or unsupported metrics are omitted rather than fabricated.
 */

import { useCallback, useEffect, useRef, useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";
import { useAuth } from "@/lib/auth-context";
import type {
  AnalysisJobResponse,
  AnalysisRunResponse,
  DeveloperCapabilityResponse,
  GitHubStatusResponse,
  RepositoryResponse,
  RiskFindingResponse,
} from "@/types/api";

import { Card, CardBody, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, SeverityBadge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { StageStepper } from "@/components/ui/stage-stepper";
import { ScoreGauge } from "@/components/ui/score-gauge";
import { formatDate } from "@/lib/utils";
import {
  AlertTriangle,
  ExternalLink,
  GitBranch,
  Lock,
  Play,
  Plus,
  RefreshCw,
  Server,
  Globe,
} from "lucide-react";
import { AddRepositoryDialog } from "@/components/repositories/add-repository-dialog";

// ─── Types ───────────────────────────────────────────────────────────────────

interface OverviewState {
  githubStatus: GitHubStatusResponse | null;
  repositories: RepositoryResponse[];
  selectedRepoId: string | null;
  capabilities: DeveloperCapabilityResponse[];
  risks: RiskFindingResponse[];
  activeJob: AnalysisJobResponse | null;
  activeRun: AnalysisRunResponse | null;
  /** True for initial full-page load */
  initialLoading: boolean;
  /** True when switching repositories */
  repoLoading: boolean;
  /** True when fetching capabilities/risks for selected repo */
  dataLoading: boolean;
  /** True while submitting or polling an analysis job */
  analysisLoading: boolean;
  /** True during bounded polling */
  polling: boolean;
  githubError: string | null;
  repoError: string | null;
  dataError: string | null;
  analysisError: string | null;
  capabilitiesTotal: number;
  risksTotal: number;
}

// ─── Analysis Polling ────────────────────────────────────────────────────────

const TERMINAL_STATUSES = new Set(["COMPLETED", "FAILED"]);
const POLL_INTERVAL_MS = 4000;
const MAX_POLL_ATTEMPTS = 75; // ~5 minutes

// ─── Sub-components ──────────────────────────────────────────────────────────

function GitHubStatusCard({
  status,
  loading,
  error,
}: {
  status: GitHubStatusResponse | null;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <CardSkeleton lines={2} />;
  if (error) {
    return (
      <Card>
        <CardBody>
          <InlineError message={error} />
        </CardBody>
      </Card>
    );
  }

  const connected = status?.is_connected && status?.is_installed;

  return (
    <Card accentBorder={connected}>
      <CardHeader>
        <CardTitle as="h3" className="flex items-center gap-2">
          <GitBranch className="h-4 w-4 text-slate-400" aria-hidden="true" />
          GitHub
        </CardTitle>
        {status && (
          <Badge variant={connected ? "success" : "warning"} dot>
            {connected
              ? `@${status.github_username ?? "connected"}`
              : status.is_disconnected
              ? "Disconnected"
              : "Not installed"}
          </Badge>
        )}
      </CardHeader>
      <CardBody>
        {!status || !connected ? (
          <div className="text-sm text-slate-400 space-y-3">
            <p>
              Connect your GitHub account so DevTwin can access your repositories.
            </p>
            <Button
              variant="primary"
              size="sm"
              leftIcon={<GitBranch className="h-3.5 w-3.5" />}
              onClick={async () => {
                try {
                  const { install_url } = await apiClient.getGitHubInstallUrl();
                  window.location.href = install_url;
                } catch {
                  // Handled by caller — show inline message
                }
              }}
            >
              Connect GitHub
            </Button>
          </div>
        ) : (
          <p className="text-sm text-slate-400">
            GitHub App is installed and connected. Your repositories are accessible.
          </p>
        )}
      </CardBody>
    </Card>
  );
}

function RepoSelector({
  repos,
  selectedId,
  loading,
  error,
  onSelect,
  onOpenAddRepo,
}: {
  repos: RepositoryResponse[];
  selectedId: string | null;
  loading: boolean;
  error: string | null;
  onSelect: (id: string) => void;
  onOpenAddRepo: () => void;
}) {
  if (loading) return <CardSkeleton lines={3} />;

  return (
    <Card>
      <CardHeader className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CardTitle as="h3" className="flex items-center gap-2">
            <Server className="h-4 w-4 text-slate-400" aria-hidden="true" />
            Repositories
          </CardTitle>
          <Badge variant="muted">{repos.length}</Badge>
        </div>
        <Button
          variant="outline"
          size="sm"
          leftIcon={<Plus className="h-3 w-3" />}
          onClick={onOpenAddRepo}
        >
          Add
        </Button>
      </CardHeader>
      {error && (
        <CardBody className="pt-0">
          <InlineError message={error} />
        </CardBody>
      )}
      {repos.length === 0 && !error && (
        <CardBody className="text-center py-5 space-y-3">
          <EmptyState
            variant="no-repos"
            description="Register a repository and run an analysis to see data here."
          />
          <Button
            variant="primary"
            size="sm"
            leftIcon={<Plus className="h-3.5 w-3.5" />}
            onClick={onOpenAddRepo}
          >
            Add Repository
          </Button>
        </CardBody>
      )}
      {repos.length > 0 && (
        <ul role="listbox" aria-label="Select a repository">
          {repos.map((repo) => (
            <li key={repo.id}>
              <button
                role="option"
                aria-selected={selectedId === repo.id}
                onClick={() => onSelect(repo.id)}
                className={`w-full text-left px-5 py-3 flex items-center gap-3 transition-colors border-b border-slate-800/40 last:border-0 ${
                  selectedId === repo.id
                    ? "bg-cyan-500/8 text-cyan-300"
                    : "text-slate-300 hover:bg-slate-800/40"
                }`}
              >
                <GitBranch className="h-3.5 w-3.5 flex-shrink-0 text-slate-500" aria-hidden="true" />
                <div className="min-w-0 flex-1">
                  <p className="text-xs font-medium font-mono truncate">{repo.full_name}</p>
                  <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                    {repo.visibility === "private" ? (
                      <Lock className="h-2.5 w-2.5" aria-hidden="true" />
                    ) : (
                      <Globe className="h-2.5 w-2.5" aria-hidden="true" />
                    )}
                    {repo.visibility} · {repo.default_branch}
                  </p>
                </div>
                {selectedId === repo.id && (
                  <span className="flex-shrink-0 h-1.5 w-1.5 rounded-full bg-cyan-400" aria-hidden="true" />
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function AnalysisCard({
  job,
  run,
  loading,
  error,
  onRunAnalysis,
  onRefresh,
}: {
  job: AnalysisJobResponse | null;
  run: AnalysisRunResponse | null;
  loading: boolean;
  error: string | null;
  onRunAnalysis: () => void;
  onRefresh: () => void;
}) {
  if (loading && !job) return <CardSkeleton lines={4} />;

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h3" className="flex items-center gap-2">
          <Play className="h-4 w-4 text-slate-400" aria-hidden="true" />
          Analysis Pipeline
        </CardTitle>
        {job && <StatusBadge status={job.status} />}
      </CardHeader>

      {error && (
        <CardBody>
          <InlineError message={error} />
        </CardBody>
      )}

      {!job && !error && (
        <CardBody>
          <p className="text-sm text-slate-400 mb-4">
            No analysis job has been run for this repository. Start one to generate
            capability scores and risk findings.
          </p>
          <Button
            variant="primary"
            size="sm"
            loading={loading}
            onClick={onRunAnalysis}
            leftIcon={<Play className="h-3.5 w-3.5" />}
          >
            Run Analysis
          </Button>
        </CardBody>
      )}

      {job && (
        <>
          <CardBody className="space-y-4">
            <StageStepper currentStatus={run ? run.status : "QUEUED"} />

            <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-xs">
              <dt className="text-slate-500">Job status</dt>
              <dd className="text-slate-200 font-mono">{job.status}</dd>
              <dt className="text-slate-500">Attempts</dt>
              <dd className="text-slate-200 font-mono">{job.attempt_count}</dd>
              <dt className="text-slate-500">Requested</dt>
              <dd className="text-slate-200">{formatDate(job.requested_at)}</dd>
              {job.completed_at && (
                <>
                  <dt className="text-slate-500">Completed</dt>
                  <dd className="text-slate-200">{formatDate(job.completed_at)}</dd>
                </>
              )}
              {run?.error_message && (
                <>
                  <dt className="text-slate-500">Error</dt>
                  <dd className="text-red-400 font-mono col-span-2 truncate" title={run.error_message}>
                    {run.error_message}
                  </dd>
                </>
              )}
            </dl>
          </CardBody>

          <CardFooter className="flex items-center gap-2">
            {(job.status === "COMPLETED" || job.status === "FAILED") && (
              <Button
                variant="primary"
                size="sm"
                loading={loading}
                onClick={onRunAnalysis}
                leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              >
                Re-run
              </Button>
            )}
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              leftIcon={<RefreshCw className="h-3.5 w-3.5" />}
              aria-label="Refresh analysis status"
            >
              Refresh
            </Button>
          </CardFooter>
        </>
      )}
    </Card>
  );
}

function CapabilitiesCard({
  capabilities,
  total,
  loading,
  error,
}: {
  capabilities: DeveloperCapabilityResponse[];
  total: number;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <CardSkeleton lines={5} />;

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h3">Top Capabilities</CardTitle>
        {total > 0 && (
          <Badge variant="muted">
            {total} total
          </Badge>
        )}
      </CardHeader>
      {error && (
        <CardBody>
          <InlineError message={error} />
        </CardBody>
      )}
      {capabilities.length === 0 && !error && (
        <EmptyState
          variant="no-data"
          description="Run an analysis to generate capability scores for this repository."
        />
      )}
      {capabilities.length > 0 && (
        <CardBody className="space-y-4">
          <p className="text-xs text-slate-500 bg-amber-500/8 border border-amber-500/20 rounded-md px-3 py-2">
            <AlertTriangle className="inline h-3 w-3 mr-1.5 text-amber-400" aria-hidden="true" />
            Scores are scoped to the selected repository and analysis run.
            They do not represent cumulative totals across all repositories.
          </p>
          {capabilities.slice(0, 8).map((cap) => (
            <ScoreGauge
              key={cap.id}
              score={cap.score}
              confidence={cap.confidence}
              label={cap.target.target_name}
              sublabel={`${cap.target.target_type}${cap.target.domain_or_category ? ` · ${cap.target.domain_or_category}` : ""}`}
            />
          ))}
          {total > 8 && (
            <p className="text-xs text-slate-500 text-center pt-1">
              +{total - 8} more — view the Capabilities page for the full list.
            </p>
          )}
        </CardBody>
      )}
    </Card>
  );
}

function RisksCard({
  risks,
  total,
  loading,
  error,
}: {
  risks: RiskFindingResponse[];
  total: number;
  loading: boolean;
  error: string | null;
}) {
  if (loading) return <CardSkeleton lines={4} />;

  // Count by severity
  const counts = (risks ?? []).reduce<Record<string, number>>((acc, r) => {
    acc[r.severity] = (acc[r.severity] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <Card>
      <CardHeader>
        <CardTitle as="h3" className="flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-slate-400" aria-hidden="true" />
          CodeRisk Summary
        </CardTitle>
        {total > 0 && <Badge variant="muted">{total} findings</Badge>}
      </CardHeader>
      {error && (
        <CardBody>
          <InlineError message={error} />
        </CardBody>
      )}
      {risks.length === 0 && !error && (
        <EmptyState
          variant="no-data"
          description="No risk findings for this repository. Run an analysis to generate CodeRisk data."
        />
      )}
      {risks.length > 0 && (
        <CardBody className="space-y-4">
          {/* Summary counts */}
          <div className="flex flex-wrap gap-2">
            {["CRITICAL", "HIGH", "MEDIUM", "LOW"].map((sev) =>
              counts[sev] != null ? (
                <div
                  key={sev}
                  className="flex items-center gap-1.5"
                  aria-label={`${sev}: ${counts[sev]}`}
                >
                  <SeverityBadge severity={sev} />
                  <span className="text-sm font-mono text-slate-200">{counts[sev]}</span>
                </div>
              ) : null
            )}
          </div>

          {/* Top findings table */}
          <div className="rounded-lg border border-slate-800/50 overflow-hidden">
            <table className="w-full text-xs" aria-label="Top risk findings">
              <thead>
                <tr className="border-b border-slate-800/50 bg-slate-900/40">
                  <th className="text-left px-3 py-2 text-slate-500 font-medium">Severity</th>
                  <th className="text-left px-3 py-2 text-slate-500 font-medium">Type</th>
                  <th className="text-left px-3 py-2 text-slate-500 font-medium hidden sm:table-cell">File</th>
                </tr>
              </thead>
              <tbody>
                {risks.slice(0, 5).map((risk) => (
                  <tr key={risk.id} className="border-b border-slate-800/30 last:border-0">
                    <td className="px-3 py-2">
                      <SeverityBadge severity={risk.severity} />
                    </td>
                    <td className="px-3 py-2 text-slate-300 font-mono">{risk.risk_type}</td>
                    <td className="px-3 py-2 text-slate-500 hidden sm:table-cell truncate max-w-[160px]">
                      {risk.file_path ?? "—"}
                      {risk.line_start != null && (
                        <span className="text-slate-600">:{risk.line_start}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {total > 5 && (
            <p className="text-xs text-slate-500 text-center">
              +{total - 5} more — view the CodeRisk page for full findings.
            </p>
          )}
        </CardBody>
      )}
    </Card>
  );
}

// ─── Overview Component ───────────────────────────────────────────────────────

export function OverviewView() {
  const { token, developer } = useAuth();

  const [state, setState] = useState<OverviewState>({
    githubStatus: null,
    repositories: [],
    selectedRepoId: null,
    capabilities: [],
    risks: [],
    activeJob: null,
    activeRun: null,
    initialLoading: true,
    repoLoading: false,
    dataLoading: false,
    analysisLoading: false,
    polling: false,
    githubError: null,
    repoError: null,
    dataError: null,
    analysisError: null,
    capabilitiesTotal: 0,
    risksTotal: 0,
  });

  const [isAddRepoOpen, setIsAddRepoOpen] = useState(false);

  const pollRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollAttemptsRef = useRef(0);

  const handleRepoAdded = (newRepo: RepositoryResponse) => {
    setState((s) => ({
      ...s,
      repositories: [...s.repositories, newRepo],
      selectedRepoId: newRepo.id,
      repoError: null,
    }));
  };

  // ── Initial load: GitHub status + repositories ──────────────────────────
  useEffect(() => {
    if (!token) {
      setState((s) => ({ ...s, initialLoading: false }));
      return;
    }

    let cancelled = false;

    async function init() {
      setState((s) => ({ ...s, initialLoading: true }));
      try {
        const [ghStatus, repos] = await Promise.allSettled([
          apiClient.getGitHubStatus(),
          apiClient.getRepositories(),
        ]);

        if (cancelled) return;

        setState((s) => ({
          ...s,
          initialLoading: false,
          githubStatus: ghStatus.status === "fulfilled" ? ghStatus.value : null,
          githubError:
            ghStatus.status === "rejected"
              ? (ghStatus.reason instanceof ApiError
                  ? ghStatus.reason.detail
                  : "Could not load GitHub status.")
              : null,
          repositories: repos.status === "fulfilled" ? repos.value : [],
          repoError:
            repos.status === "rejected"
              ? (repos.reason instanceof ApiError
                  ? repos.reason.detail
                  : "Could not load repositories.")
              : null,
          selectedRepoId:
            repos.status === "fulfilled" && repos.value.length > 0
              ? repos.value[0].id
              : null,
        }));
      } catch {
        if (!cancelled) {
          setState((s) => ({
            ...s,
            initialLoading: false,
            githubError: "Initialisation failed. Check backend connectivity.",
          }));
        }
      }
    }

    init();
    return () => {
      cancelled = true;
    };
  }, [token]);

  // ── Load capability and risk data when repo changes ──────────────────────
  const loadRepoData = useCallback(async (repoId: string) => {
    setState((s) => ({ ...s, dataLoading: true, dataError: null }));
    try {
      const [caps, risks] = await Promise.allSettled([
        apiClient.getCapabilities({ limit: 20 }),
        apiClient.getRepositoryRisks(repoId, { limit: 20 }),
      ]);

      setState((s) => ({
        ...s,
        dataLoading: false,
        capabilities: caps.status === "fulfilled" ? caps.value.items : [],
        capabilitiesTotal: caps.status === "fulfilled" ? caps.value.total : 0,
        risks: risks.status === "fulfilled" ? risks.value.items : [],
        risksTotal: risks.status === "fulfilled" ? risks.value.total : 0,
        dataError:
          caps.status === "rejected" && risks.status === "rejected"
            ? "Could not load analysis data for this repository."
            : null,
      }));
    } catch {
      setState((s) => ({
        ...s,
        dataLoading: false,
        dataError: "Failed to load repository data.",
      }));
    }
  }, []);

  useEffect(() => {
    const repoId = state.selectedRepoId;
    if (!repoId || !token) return;
    loadRepoData(repoId);
  }, [state.selectedRepoId, token, loadRepoData]);

  // ── Bounded analysis polling ─────────────────────────────────────────────
  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearTimeout(pollRef.current);
      pollRef.current = null;
    }
    pollAttemptsRef.current = 0;
    setState((s) => ({ ...s, polling: false }));
  }, []);

  const pollJob = useCallback(
    async (jobId: string) => {
      if (pollAttemptsRef.current >= MAX_POLL_ATTEMPTS) {
        stopPolling();
        setState((s) => ({
          ...s,
          analysisError: "Analysis is taking longer than expected. Please refresh manually.",
        }));
        return;
      }
      pollAttemptsRef.current += 1;

      try {
        const [job, runs] = await Promise.all([
          apiClient.getAnalysisJob(jobId),
          apiClient.getAnalysisJobRuns(jobId),
        ]);

        const latestRun = runs.length > 0 ? runs[runs.length - 1] : null;

        setState((s) => ({
          ...s,
          activeJob: job,
          activeRun: latestRun,
          analysisLoading: false,
        }));

        if (!TERMINAL_STATUSES.has(job.status)) {
          pollRef.current = setTimeout(() => pollJob(jobId), POLL_INTERVAL_MS);
        } else {
          stopPolling();
          if (job.status === "COMPLETED" && state.selectedRepoId) {
            loadRepoData(state.selectedRepoId);
          }
        }
      } catch (err) {
        stopPolling();
        setState((s) => ({
          ...s,
          analysisLoading: false,
          analysisError:
            err instanceof ApiError
              ? err.detail
              : "Failed to poll analysis status.",
        }));
      }
    },
    [stopPolling, loadRepoData, state.selectedRepoId]
  );

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearTimeout(pollRef.current);
    };
  }, []);

  const handleRunAnalysis = useCallback(async () => {
    const repoId = state.selectedRepoId;
    if (!repoId) return;

    setState((s) => ({
      ...s,
      analysisLoading: true,
      analysisError: null,
      activeJob: null,
      activeRun: null,
      polling: true,
    }));
    pollAttemptsRef.current = 0;

    try {
      const created = await apiClient.submitAnalysisJob(repoId);
      try {
        const fullJob = await apiClient.getAnalysisJob(created.id);
        setState((s) => ({ ...s, activeJob: fullJob }));
      } catch {
        setState((s) => ({
          ...s,
          activeJob: {
            id: created.id,
            job_id: created.job_id,
            repository_id: repoId,
            status: created.status,
            attempt_count: 0,
            requested_at: new Date().toISOString(),
            completed_at: null,
          },
        }));
      }
      pollJob(created.id);
    } catch (err) {
      setState((s) => ({
        ...s,
        analysisLoading: false,
        polling: false,
        analysisError:
          err instanceof ApiError
            ? err.detail
            : "Failed to submit analysis job.",
      }));
    }
  }, [state.selectedRepoId, pollJob]);

  const handleRefreshJob = useCallback(async () => {
    const job = state.activeJob;
    if (!job) return;
    setState((s) => ({ ...s, analysisLoading: true }));
    try {
      const [updated, runs] = await Promise.all([
        apiClient.getAnalysisJob(job.id),
        apiClient.getAnalysisJobRuns(job.id),
      ]);
      setState((s) => ({
        ...s,
        activeJob: updated,
        activeRun: runs.length > 0 ? runs[runs.length - 1] : null,
        analysisLoading: false,
      }));
    } catch {
      setState((s) => ({ ...s, analysisLoading: false }));
    }
  }, [state.activeJob]);

  // ── Unauthenticated state ────────────────────────────────────────────────
  if (!token) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-6">
        <div className="rounded-full bg-cyan-500/10 border border-cyan-500/20 p-5 mb-6">
          <GitBranch className="h-8 w-8 text-cyan-400" aria-hidden="true" />
        </div>
        <h2 className="text-xl font-bold text-slate-100 mb-2">Welcome to DevTwin</h2>
        <p className="text-sm text-slate-400 max-w-sm leading-relaxed mb-6">
          Sign in with your DevTwin backend token to view your developer capability
          intelligence dashboard.
        </p>
        <p className="text-xs text-slate-500 bg-slate-800/50 border border-slate-700/50 rounded-lg px-4 py-3 max-w-xs">
          Use the <strong className="text-slate-300">Sign in</strong> button in the top-right
          corner to enter your backend JWT.
        </p>
      </div>
    );
  }

  if (state.initialLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <CardSkeleton lines={2} />
        <CardSkeleton lines={3} />
        <CardSkeleton lines={5} />
        <CardSkeleton lines={4} />
      </div>
    );
  }

  const selectedRepo = state.repositories.find((r) => r.id === state.selectedRepoId);

  return (
    <div className="space-y-6">
      {/* Developer context bar */}
      {developer && (
        <div className="flex items-center gap-3 text-xs text-slate-400 bg-slate-800/30 border border-slate-800/60 rounded-lg px-4 py-2.5">
          <div className="h-2 w-2 rounded-full bg-emerald-400 flex-shrink-0" aria-hidden="true" />
          <span>Developer ID: <code className="font-mono text-slate-300">{developer.id.slice(0, 12)}…</code></span>
          {selectedRepo && (
            <>
              <span className="text-slate-600">·</span>
              <span>
                Repository:{" "}
                <code className="font-mono text-slate-300">{selectedRepo.full_name}</code>
              </span>
              <a
                href={selectedRepo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="ml-auto text-slate-500 hover:text-slate-300 transition-colors"
                aria-label="Open repository on GitHub"
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </>
          )}
        </div>
      )}

      {/* Main grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Left column */}
        <div className="lg:col-span-1 space-y-5">
          <GitHubStatusCard
            status={state.githubStatus}
            loading={state.initialLoading}
            error={state.githubError}
          />
          <RepoSelector
            repos={state.repositories}
            selectedId={state.selectedRepoId}
            loading={state.repoLoading}
            error={state.repoError}
            onOpenAddRepo={() => setIsAddRepoOpen(true)}
            onSelect={(id) => {
              stopPolling();
              setState((s) => ({
                ...s,
                selectedRepoId: id,
                activeJob: null,
                activeRun: null,
                analysisError: null,
              }));
            }}
          />
        </div>

        {/* Center + Right */}
        <div className="lg:col-span-2 space-y-5">
          {/* Analysis card — only when a repo is selected */}
          {state.selectedRepoId ? (
            <AnalysisCard
              job={state.activeJob}
              run={state.activeRun}
              loading={state.analysisLoading}
              error={state.analysisError}
              onRunAnalysis={handleRunAnalysis}
              onRefresh={handleRefreshJob}
            />
          ) : (
            <Card>
              <CardBody>
                <EmptyState
                  variant="no-repos"
                  description="Select a repository to trigger an analysis."
                />
              </CardBody>
            </Card>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-5">
            <CapabilitiesCard
              capabilities={state.capabilities}
              total={state.capabilitiesTotal}
              loading={state.dataLoading}
              error={state.dataError}
            />
            <RisksCard
              risks={state.risks}
              total={state.risksTotal}
              loading={state.dataLoading}
              error={state.dataError}
            />
          </div>
        </div>
      </div>

      <AddRepositoryDialog
        isOpen={isAddRepoOpen}
        onClose={() => setIsAddRepoOpen(false)}
        onSuccess={handleRepoAdded}
      />
    </div>
  );
}
