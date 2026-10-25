"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import type { RepositoryResponse, AnalysisJobResponse, AnalysisRunResponse } from "@/types/api";
import { Shell, PageContainer, PageHeading } from "@/components/layout/shell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge, StatusBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/ui/skeleton";
import { EmptyState, InlineError } from "@/components/ui/empty-state";
import { StageStepper } from "@/components/ui/stage-stepper";
import { formatDate } from "@/lib/utils";
import { GitBranch, Globe, Lock, Play, Plus, Server } from "lucide-react";
import { AddRepositoryDialog } from "@/components/repositories/add-repository-dialog";

export default function RepositoriesPage() {
  const { token } = useAuth();
  const [repos, setRepos] = useState<RepositoryResponse[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [jobs, setJobs] = useState<Record<string, AnalysisJobResponse>>({});
  const [runs, setRuns] = useState<Record<string, AnalysisRunResponse | null>>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isAddOpen, setIsAddOpen] = useState(false);

  useEffect(() => {
    if (!token) { setLoading(false); return; }
    apiClient.getRepositories()
      .then((data) => {
        setRepos(data);
        if (data.length > 0) setSelectedId(data[0].id);
      })
      .catch((err) => setError(err instanceof ApiError ? err.detail : "Failed to load repositories."))
      .finally(() => setLoading(false));
  }, [token]);

  const selectedRepo = repos.find((r) => r.id === selectedId);

  return (
    <Shell pageTitle="Repositories">
      <PageContainer>
        <PageHeading
          title="Repositories"
          description="Registered repositories and their analysis state. Select a repository to view its analysis pipeline."
          actions={
            token && (
              <Button
                variant="primary"
                size="sm"
                leftIcon={<Plus className="h-3.5 w-3.5" />}
                onClick={() => setIsAddOpen(true)}
              >
                Add Repository
              </Button>
            )
          }
        />

        {!token && (
          <EmptyState variant="no-github" description="Sign in to view your repositories." />
        )}

        {loading && <CardSkeleton lines={4} />}
        {error && <InlineError message={error} />}

        {!loading && repos.length === 0 && token && (
          <div className="rounded-xl border border-slate-800 bg-[#0f172a] p-8 text-center space-y-4">
            <EmptyState
              variant="no-repos"
              description="No repositories registered yet. Add an accessible GitHub repository to start."
            />
            <Button
              variant="primary"
              size="sm"
              leftIcon={<Plus className="h-3.5 w-3.5" />}
              onClick={() => setIsAddOpen(true)}
            >
              Add Repository
            </Button>
          </div>
        )}

        {repos.length > 0 && (
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
            {/* Repository list */}
            <Card className="lg:col-span-1">
              <CardHeader className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CardTitle as="h2" className="flex items-center gap-2">
                    <Server className="h-4 w-4 text-slate-400" aria-hidden="true" />
                    All Repositories
                  </CardTitle>
                  <Badge variant="muted">{repos.length}</Badge>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  leftIcon={<Plus className="h-3 w-3" />}
                  onClick={() => setIsAddOpen(true)}
                >
                  Add
                </Button>
              </CardHeader>
              <ul>
                {repos.map((repo) => (
                  <li key={repo.id}>
                    <button
                      onClick={() => setSelectedId(repo.id)}
                      className={`w-full text-left px-4 py-3 flex items-start gap-3 border-b border-slate-800/40 last:border-0 transition-colors ${
                        selectedId === repo.id ? "bg-cyan-500/8" : "hover:bg-slate-800/30"
                      }`}
                    >
                      <GitBranch className="h-4 w-4 text-slate-500 mt-0.5 flex-shrink-0" aria-hidden="true" />
                      <div className="min-w-0">
                        <p className="text-sm font-mono font-medium text-slate-200 truncate">{repo.full_name}</p>
                        <p className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
                          {repo.visibility === "private" ? <Lock className="h-2.5 w-2.5" /> : <Globe className="h-2.5 w-2.5" />}
                          {repo.visibility} · {repo.default_branch}
                        </p>
                        <p className="text-xs text-slate-600 mt-0.5">Added {formatDate(repo.created_at)}</p>
                      </div>
                    </button>
                  </li>
                ))}
              </ul>
            </Card>

            {/* Repository detail */}
            <div className="lg:col-span-2 space-y-5">
              {selectedRepo ? (
                <>
                  <Card>
                    <CardHeader>
                      <CardTitle as="h2">{selectedRepo.full_name}</CardTitle>
                      <a
                        href={selectedRepo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-xs text-cyan-400 hover:text-cyan-300"
                      >
                        View on GitHub ↗
                      </a>
                    </CardHeader>
                    <CardBody>
                      <dl className="grid grid-cols-2 gap-3 text-xs">
                        <dt className="text-slate-500">Repository ID</dt>
                        <dd className="font-mono text-slate-300">{selectedRepo.id}</dd>
                        <dt className="text-slate-500">GitHub Repo ID</dt>
                        <dd className="font-mono text-slate-300">{selectedRepo.github_repo_id}</dd>
                        <dt className="text-slate-500">Default branch</dt>
                        <dd className="font-mono text-slate-300">{selectedRepo.default_branch}</dd>
                        <dt className="text-slate-500">Visibility</dt>
                        <dd className="text-slate-300">{selectedRepo.visibility}</dd>
                        {selectedRepo.synced_at && (
                          <>
                            <dt className="text-slate-500">Last synced</dt>
                            <dd className="text-slate-300">{formatDate(selectedRepo.synced_at)}</dd>
                          </>
                        )}
                      </dl>
                    </CardBody>
                  </Card>

                  {/* Analysis state */}
                  {jobs[selectedRepo.id] ? (
                    <Card>
                      <CardHeader>
                        <CardTitle as="h3">Latest Analysis</CardTitle>
                        <StatusBadge status={jobs[selectedRepo.id].status} />
                      </CardHeader>
                      <CardBody className="space-y-4">
                        {runs[selectedRepo.id] && (
                          <StageStepper currentStatus={runs[selectedRepo.id]!.status} />
                        )}
                      </CardBody>
                    </Card>
                  ) : (
                    <Card>
                      <CardBody>
                        <p className="text-sm text-slate-400 mb-3">
                          No analysis has been run for this repository.
                        </p>
                        <Button
                          variant="primary"
                          size="sm"
                          leftIcon={<Play className="h-3.5 w-3.5" />}
                          onClick={async () => {
                            try {
                              const created = await apiClient.submitAnalysisJob(selectedRepo.id);
                              const fullJob = await apiClient.getAnalysisJob(created.id);
                              setJobs((j) => ({ ...j, [selectedRepo.id]: fullJob }));
                              setRuns((r) => ({ ...r, [selectedRepo.id]: null }));
                            } catch { /* handled by error state */ }
                          }}
                        >
                          Run Analysis
                        </Button>
                      </CardBody>
                    </Card>
                  )}
                </>
              ) : (
                <EmptyState description="Select a repository from the list to view details." />
              )}
            </div>
          </div>
        )}

        <AddRepositoryDialog
          isOpen={isAddOpen}
          onClose={() => setIsAddOpen(false)}
          onSuccess={(newRepo) => {
            setRepos((prev) => [...prev, newRepo]);
            setSelectedId(newRepo.id);
          }}
        />
      </PageContainer>
    </Shell>
  );
}
