"use client";

import { useEffect, useState, useId } from "react";
import { apiClient, ApiError } from "@/lib/api-client";
import type { GitHubRepositoryOption, ProjectResponse, RepositoryResponse } from "@/types/api";
import { Button } from "@/components/ui/button";
import { InlineError } from "@/components/ui/empty-state";
import { Badge } from "@/components/ui/badge";
import { CardSkeleton } from "@/components/ui/skeleton";
import { FolderPlus, GitBranch, Globe, Lock, Plus, X } from "lucide-react";

interface AddRepositoryDialogProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (newRepo: RepositoryResponse) => void;
}

export function AddRepositoryDialog({ isOpen, onClose, onSuccess }: AddRepositoryDialogProps) {
  const titleId = useId();
  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [repoError, setRepoError] = useState<string | null>(null);

  const [projects, setProjects] = useState<ProjectResponse[]>([]);
  const [githubRepos, setGithubRepos] = useState<GitHubRepositoryOption[]>([]);

  // Project state
  const [isCreatingProject, setIsCreatingProject] = useState(false);
  const [selectedProjectId, setSelectedProjectId] = useState<string>("");
  const [newProjectName, setNewProjectName] = useState<string>("");

  // Repository state
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null);
  const [searchFilter, setSearchFilter] = useState<string>("");

  // Load projects and accessible GitHub repositories whenever dialog opens
  useEffect(() => {
    if (!isOpen) {
      setError(null);
      setRepoError(null);
      setSearchFilter("");
      return;
    }

    let active = true;
    async function loadData() {
      setLoading(true);
      setError(null);
      setRepoError(null);

      try {
        const [projResult, repoResult] = await Promise.allSettled([
          apiClient.getProjects(),
          apiClient.getGitHubRepositories(),
        ]);

        if (!active) return;

        let hadError = false;
        let errMsg = "";

        if (projResult.status === "fulfilled") {
          const projs = projResult.value;
          setProjects(projs);
          if (projs.length > 0) {
            setSelectedProjectId(projs[0].id);
            setIsCreatingProject(false);
          } else {
            setIsCreatingProject(true);
            setNewProjectName("Default Project");
          }
        } else {
          hadError = true;
          errMsg = projResult.reason instanceof ApiError ? projResult.reason.detail : "Failed to load projects.";
        }

        if (repoResult.status === "fulfilled") {
          const repos = repoResult.value;
          setGithubRepos(repos);
          setRepoError(null);
          if (repos.length > 0) {
            setSelectedRepoId(repos[0].github_repo_id);
          } else {
            setSelectedRepoId(null);
          }
        } else {
          hadError = true;
          let detail = "Failed to load GitHub repositories.";
          if (repoResult.reason instanceof ApiError) {
            if (repoResult.reason.status === 404) {
              detail = "GitHub repository service endpoint not found (HTTP 404). Please ensure the backend server is running.";
            } else if (repoResult.reason.status === 401) {
              detail = "Session expired. Please sign in again to access GitHub repositories.";
            } else if (repoResult.reason.status === 403) {
              detail = "GitHub App installation lacks access to list repositories. Please review app permissions on GitHub.";
            } else if (repoResult.reason.status === 502) {
              detail = repoResult.reason.detail || "Failed to communicate with GitHub. Please check your GitHub App configuration.";
            } else {
              detail = repoResult.reason.detail || detail;
            }
          }
          setRepoError(detail);
          errMsg = errMsg ? `${errMsg} | ${detail}` : detail;
        }

        if (hadError) {
          setError(errMsg);
        }
      } catch (err) {
        if (!active) return;
        setError(err instanceof ApiError ? err.detail : "Failed to load initial dialog data.");
      } finally {
        if (active) setLoading(false);
      }
    }

    loadData();

    return () => {
      active = false;
    };
  }, [isOpen]);

  // Handle escape key
  useEffect(() => {
    if (!isOpen) return;
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const filteredRepos = githubRepos.filter((r) =>
    r.full_name.toLowerCase().includes(searchFilter.toLowerCase().trim())
  );

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selectedRepoId === null) {
      setError("Please select a GitHub repository.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      let targetProjectId = selectedProjectId;

      // 1. Create project if user chose new project mode or has no projects
      if (isCreatingProject || !targetProjectId) {
        const trimmed = newProjectName.trim();
        if (!trimmed) {
          setError("Please provide a valid project name.");
          setSubmitting(false);
          return;
        }
        const createdProject = await apiClient.createProject(trimmed);
        targetProjectId = createdProject.id;
      }

      // 2. Register repository under target project
      const registeredRepo = await apiClient.createRepository(targetProjectId, selectedRepoId);

      onSuccess(registeredRepo);
      onClose();
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setError("This repository is already registered in DevTwin.");
        } else if (err.status === 403) {
          setError("The GitHub App installation lacks access to this repository.");
        } else {
          setError(err.detail || "Failed to register repository.");
        }
      } else {
        setError("Failed to register repository. Please try again.");
      }
    } finally {
      setSubmitting(false);
    }
  }

  const isSubmitDisabled =
    loading ||
    submitting ||
    selectedRepoId === null ||
    (isCreatingProject && !newProjectName.trim()) ||
    (!isCreatingProject && !selectedProjectId);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-xs animate-in fade-in duration-150"
      aria-modal="true"
      role="dialog"
      aria-labelledby={titleId}
    >
      <div className="relative w-full max-w-lg rounded-xl border border-slate-800 bg-[#0f172a] shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between border-b border-slate-800/80 px-5 py-4">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Plus className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id={titleId} className="text-sm font-semibold text-slate-100">
                Register Repository
              </h2>
              <p className="text-xs text-slate-400">
                Add an accessible GitHub repository to your DevTwin intelligence pipeline.
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
            aria-label="Close dialog"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Content */}
        <form onSubmit={handleSubmit}>
          <div className="p-5 space-y-4 max-h-[70vh] overflow-y-auto">
            {error && <InlineError message={error} />}

            {loading ? (
              <div className="py-2 space-y-3">
                <CardSkeleton lines={3} />
                <CardSkeleton lines={3} />
              </div>
            ) : (
              <>
                {/* 1. Project selection / creation */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <label className="text-xs font-medium text-slate-300">Target Project</label>
                    {projects.length > 0 && (
                      <button
                        type="button"
                        onClick={() => {
                          setIsCreatingProject(!isCreatingProject);
                          setError(null);
                        }}
                        className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1"
                      >
                        {isCreatingProject ? "Select existing project" : "+ Create new project"}
                      </button>
                    )}
                  </div>

                  {isCreatingProject ? (
                    <div className="space-y-1.5">
                      <input
                        type="text"
                        value={newProjectName}
                        onChange={(e) => setNewProjectName(e.target.value)}
                        placeholder="e.g. Minor Project / Core Services"
                        className="w-full px-3 py-2 text-xs rounded-lg border border-slate-700 bg-slate-900/60 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                        autoFocus
                      />
                      <p className="text-[11px] text-slate-500">
                        A new project will be created in DevTwin to group this repository.
                      </p>
                    </div>
                  ) : (
                    <select
                      value={selectedProjectId}
                      onChange={(e) => setSelectedProjectId(e.target.value)}
                      className="w-full px-3 py-2 text-xs rounded-lg border border-slate-700 bg-slate-900 text-slate-100 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                    >
                      {projects.map((proj) => (
                        <option key={proj.id} value={proj.id}>
                          {proj.name}
                        </option>
                      ))}
                    </select>
                  )}
                </div>

                {/* 2. Repository selection */}
                <div className="space-y-2">
                  <label className="text-xs font-medium text-slate-300">Select GitHub Repository</label>

                  {repoError ? (
                    <div className="rounded-lg border border-amber-500/20 bg-amber-500/5 p-4 text-center space-y-2">
                      <GitBranch className="h-6 w-6 text-amber-400/80 mx-auto" aria-hidden="true" />
                      <p className="text-xs text-amber-300 font-medium">
                        Unable to retrieve GitHub repositories
                      </p>
                      <p className="text-[11px] text-slate-400">
                        {repoError}
                      </p>
                    </div>
                  ) : githubRepos.length === 0 ? (
                    <div className="rounded-lg border border-slate-800 bg-slate-900/40 p-4 text-center space-y-2">
                      <GitBranch className="h-6 w-6 text-slate-500 mx-auto" aria-hidden="true" />
                      <p className="text-xs text-slate-400">
                        No accessible repositories found for your GitHub App installation.
                      </p>
                      <p className="text-[11px] text-slate-500">
                        Verify that your GitHub App has access to the repositories you wish to analyze.
                      </p>
                    </div>
                  ) : (
                    <>
                      {/* Search box if multiple repos */}
                      {githubRepos.length > 4 && (
                        <input
                          type="text"
                          value={searchFilter}
                          onChange={(e) => setSearchFilter(e.target.value)}
                          placeholder="Search repositories..."
                          className="w-full px-3 py-1.5 text-xs rounded-lg border border-slate-800 bg-slate-900/40 text-slate-200 placeholder-slate-500 focus:outline-none focus:border-cyan-400/80"
                        />
                      )}

                      <div
                        role="radiogroup"
                        aria-label="Accessible GitHub Repositories"
                        className="rounded-lg border border-slate-800/80 bg-slate-900/50 divide-y divide-slate-800/50 max-h-56 overflow-y-auto"
                      >
                        {filteredRepos.length === 0 ? (
                          <div className="p-3 text-center text-xs text-slate-500">
                            No repositories match &ldquo;{searchFilter}&rdquo;
                          </div>
                        ) : (
                          filteredRepos.map((repo) => {
                            const isSelected = selectedRepoId === repo.github_repo_id;
                            return (
                              <button
                                key={repo.github_repo_id}
                                type="button"
                                role="radio"
                                aria-checked={isSelected}
                                onClick={() => setSelectedRepoId(repo.github_repo_id)}
                                className={`w-full text-left px-3.5 py-2.5 flex items-center justify-between gap-3 transition-colors ${
                                  isSelected ? "bg-cyan-500/10 text-cyan-300" : "hover:bg-slate-800/40 text-slate-300"
                                }`}
                              >
                                <div className="min-w-0 flex items-center gap-2">
                                  {repo.private ? (
                                    <Lock className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                                  ) : (
                                    <Globe className="h-3.5 w-3.5 text-slate-500 flex-shrink-0" />
                                  )}
                                  <span className="text-xs font-mono truncate font-medium">{repo.full_name}</span>
                                </div>
                                <div className="flex items-center gap-2 flex-shrink-0">
                                  <Badge variant="muted" className="text-[10px] px-1.5 py-0.5">
                                    {repo.default_branch}
                                  </Badge>
                                  <div
                                    className={`h-3 w-3 rounded-full border flex items-center justify-center ${
                                      isSelected
                                        ? "border-cyan-400 bg-cyan-400"
                                        : "border-slate-600 bg-transparent"
                                    }`}
                                  >
                                    {isSelected && <span className="h-1.5 w-1.5 rounded-full bg-slate-950" />}
                                  </div>
                                </div>
                              </button>
                            );
                          })
                        )}
                      </div>
                    </>
                  )}
                </div>
              </>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-2.5 border-t border-slate-800/80 bg-slate-900/60 px-5 py-3">
            <Button type="button" variant="ghost" size="sm" onClick={onClose} disabled={submitting}>
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              loading={submitting}
              disabled={isSubmitDisabled}
              leftIcon={<FolderPlus className="h-3.5 w-3.5" />}
            >
              Register Repository
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
