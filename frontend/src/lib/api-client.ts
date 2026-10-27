/**
 * DevTwin Frontend — Typed API Client
 * Wraps all backend endpoints with Authorization Bearer token injection,
 * error normalization, and strict schema validation.
 */

import { env } from "@/lib/config";
import type {
  AnalysisJobCreateResponse,
  AnalysisJobResponse,
  AnalysisRunResponse,
  CapabilityHistoryListResponse,
  DeveloperCapabilityListResponse,
  DeveloperResponse,
  EvidenceListResponse,
  GitHubRepositoryOption,
  GitHubStatusResponse,
  ProjectResponse,
  RepositoryResponse,
  RiskFindingListResponse,
  SkillGraphResponse,
} from "@/types/api";

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    public detail: string,
    public raw?: unknown
  ) {
    super(`API Error ${status} (${statusText}): ${detail}`);
    this.name = "ApiError";
  }
}

class ApiClient {
  private tokenGetter: (() => string | null | Promise<string | null>) | null = null;

  public setTokenGetter(fn: () => string | null | Promise<string | null>) {
    this.tokenGetter = fn;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${env.apiBaseUrl.replace(/\/$/, "")}${endpoint}`;
    const headers = new Headers(options.headers || {});

    headers.set("Content-Type", "application/json");

    const token = this.tokenGetter ? await this.tokenGetter() : null;
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }

    try {
      const res = await fetch(url, {
        ...options,
        headers,
      });

      if (!res.ok) {
        let detail = res.statusText;
        try {
          const errData = await res.json();
          detail = errData.detail || errData.message || JSON.stringify(errData);
        } catch {
          // Response body was not JSON
        }
        throw new ApiError(res.status, res.statusText, detail);
      }

      if (res.status === 204) {
        return null as T;
      }

      return (await res.json()) as T;
    } catch (err) {
      if (err instanceof ApiError) {
        throw err;
      }
      throw new ApiError(0, "NetworkError", (err as Error).message || "Failed to communicate with DevTwin backend.");
    }
  }

  // System
  public async getHealth(): Promise<{ status: string; app: string; version: string; timestamp: string }> {
    return this.request("/health");
  }

  // Developer Profile
  public async getDeveloperMe(): Promise<DeveloperResponse> {
    return this.request("/developers/me");
  }

  public async createDeveloperMe(): Promise<DeveloperResponse> {
    return this.request("/developers/me", { method: "POST" });
  }

  // GitHub Connection
  public async getGitHubStatus(): Promise<GitHubStatusResponse> {
    return this.request("/github/status");
  }

  public async getGitHubInstallUrl(): Promise<{ install_url: string }> {
    return this.request("/github/install");
  }

  public async getGitHubRepositories(): Promise<GitHubRepositoryOption[]> {
    return this.request("/github/repositories");
  }

  public async disconnectGitHub(): Promise<void> {
    return this.request("/github/disconnect", { method: "DELETE" });
  }

  // Projects & Repositories
  public async getProjects(): Promise<ProjectResponse[]> {
    return this.request("/projects");
  }

  public async createProject(name: string): Promise<ProjectResponse> {
    return this.request("/projects", {
      method: "POST",
      body: JSON.stringify({ name }),
    });
  }

  public async getRepositories(projectId?: string): Promise<RepositoryResponse[]> {
    const query = projectId ? `?project_id=${encodeURIComponent(projectId)}` : "";
    return this.request(`/repositories${query}`);
  }

  public async getRepository(id: string): Promise<RepositoryResponse> {
    return this.request(`/repositories/${id}`);
  }

  public async createRepository(projectId: string, githubRepoId: number): Promise<RepositoryResponse> {
    return this.request("/repositories", {
      method: "POST",
      body: JSON.stringify({ project_id: projectId, github_repo_id: githubRepoId }),
    });
  }

  // Capabilities & History
  public async getCapabilities(params?: {
    target_type?: "skill" | "technology" | "concept";
    min_confidence?: number;
    limit?: number;
    offset?: number;
  }): Promise<DeveloperCapabilityListResponse> {
    const q = new URLSearchParams();
    if (params?.target_type) q.set("target_type", params.target_type);
    if (params?.min_confidence !== undefined) q.set("min_confidence", params.min_confidence.toString());
    if (params?.limit) q.set("limit", params.limit.toString());
    if (params?.offset) q.set("offset", params.offset.toString());
    const query = q.toString() ? `?${q.toString()}` : "";
    return this.request(`/developers/me/capabilities${query}`);
  }

  public async getCapabilityHistory(params?: {
    target_id?: string;
    target_type?: "skill" | "technology" | "concept";
    capability_id?: string;
    analysis_run_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<CapabilityHistoryListResponse> {
    const q = new URLSearchParams();
    if (params?.target_id) q.set("target_id", params.target_id);
    if (params?.target_type) q.set("target_type", params.target_type);
    if (params?.capability_id) q.set("capability_id", params.capability_id);
    if (params?.analysis_run_id) q.set("analysis_run_id", params.analysis_run_id);
    if (params?.limit) q.set("limit", params.limit.toString());
    if (params?.offset) q.set("offset", params.offset.toString());
    const query = q.toString() ? `?${q.toString()}` : "";
    return this.request(`/developers/me/capabilities/history${query}`);
  }

  // Evidence
  public async getEvidence(params?: {
    repository_id?: string;
    analysis_run_id?: string;
    evidence_type?: string;
    polarity?: "positive" | "negative";
    target_id?: string;
    limit?: number;
    offset?: number;
  }): Promise<EvidenceListResponse> {
    const q = new URLSearchParams();
    if (params?.repository_id) q.set("repository_id", params.repository_id);
    if (params?.analysis_run_id) q.set("analysis_run_id", params.analysis_run_id);
    if (params?.evidence_type) q.set("evidence_type", params.evidence_type);
    if (params?.polarity) q.set("polarity", params.polarity);
    if (params?.target_id) q.set("target_id", params.target_id);
    if (params?.limit) q.set("limit", params.limit.toString());
    if (params?.offset) q.set("offset", params.offset.toString());
    const query = q.toString() ? `?${q.toString()}` : "";
    return this.request(`/developers/me/evidence${query}`);
  }

  // CodeRisk & SkillGraph
  public async getRepositoryRisks(
    repositoryId: string,
    params?: { run_id?: string; severity?: string; category?: string; limit?: number; offset?: number }
  ): Promise<RiskFindingListResponse> {
    const q = new URLSearchParams();
    if (params?.run_id) q.set("run_id", params.run_id);
    if (params?.severity) q.set("severity", params.severity);
    if (params?.category) q.set("category", params.category);
    if (params?.limit) q.set("limit", params.limit.toString());
    if (params?.offset) q.set("offset", params.offset.toString());
    const query = q.toString() ? `?${q.toString()}` : "";
    return this.request(`/repositories/${repositoryId}/risks${query}`);
  }

  public async getRepositorySkillGraph(
    repositoryId: string,
    runId?: string
  ): Promise<SkillGraphResponse> {
    const query = runId ? `?run_id=${encodeURIComponent(runId)}` : "";
    return this.request(`/repositories/${repositoryId}/skillgraph${query}`);
  }

  // Analysis Pipeline
  public async submitAnalysisJob(repositoryId: string): Promise<AnalysisJobCreateResponse> {
    return this.request("/analysis/jobs", {
      method: "POST",
      body: JSON.stringify({ repository_id: repositoryId }),
    });
  }

  public async getAnalysisJob(jobId: string): Promise<AnalysisJobResponse> {
    return this.request(`/analysis/jobs/${jobId}`);
  }

  public async getAnalysisJobRuns(jobId: string): Promise<AnalysisRunResponse[]> {
    return this.request(`/analysis/jobs/${jobId}/runs`);
  }
}

export const apiClient = new ApiClient();
