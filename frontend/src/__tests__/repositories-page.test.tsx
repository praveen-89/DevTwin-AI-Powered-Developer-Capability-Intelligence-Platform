import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import RepositoriesPage from "@/app/repositories/page";
import { apiClient, ApiError } from "@/lib/api-client";
import * as authModule from "@/lib/auth-context";
import type { RepositoryResponse, AnalysisJobResponse, AnalysisRunResponse } from "@/types/api";

describe("RepositoriesPage", () => {
  const mockRepo: RepositoryResponse = {
    id: "repo-uuid-1",
    project_id: "proj-uuid-1",
    github_repo_id: 12345,
    owner_login: "octocat",
    name: "hello-world",
    full_name: "octocat/hello-world",
    url: "https://github.com/octocat/hello-world",
    default_branch: "main",
    visibility: "public",
    synced_at: null,
    created_at: "2026-10-25T10:00:00Z",
  };

  const mockJob: AnalysisJobResponse = {
    id: "job-uuid-1",
    job_id: "job-uuid-1",
    repository_id: "repo-uuid-1",
    status: "QUEUED",
    attempt_count: 0,
    requested_at: "2026-10-26T12:00:00Z",
    completed_at: null,
  };

  const mockAuthContext = {
    token: "mock-jwt-token",
    user: null,
    developer: null,
    loading: false,
    error: null,
    isConfigured: true,
    setToken: vi.fn(),
    clearToken: vi.fn(),
    signIn: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
    refreshDeveloper: vi.fn(),
  };

  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("renders unauthenticated prompt when user is not signed in", () => {
    vi.spyOn(authModule, "useAuth").mockReturnValue({
      ...mockAuthContext,
      token: null,
    });

    render(<RepositoriesPage />);
    expect(screen.getByText(/Sign in to view your repositories/i)).toBeInTheDocument();
  });

  it("renders repositories and allows triggering analysis pipeline", async () => {
    vi.spyOn(authModule, "useAuth").mockReturnValue(mockAuthContext);
    const mockGetRepos = vi.spyOn(apiClient, "getRepositories").mockResolvedValue([mockRepo]);
    vi.spyOn(apiClient, "submitAnalysisJob").mockResolvedValue({
      id: "job-uuid-1",
      job_id: "job-uuid-1",
      status: "QUEUED",
    });
    vi.spyOn(apiClient, "getAnalysisJob").mockResolvedValue(mockJob);
    vi.spyOn(apiClient, "getAnalysisJobRuns").mockResolvedValue([]);

    render(<RepositoriesPage />);

    await waitFor(() => {
      expect(mockGetRepos).toHaveBeenCalled();
    });

    expect(screen.getByText(/No analysis has been run for this repository/i)).toBeInTheDocument();
    const runBtn = screen.getByRole("button", { name: /Run Analysis/i });
    expect(runBtn).toBeInTheDocument();

    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(apiClient.submitAnalysisJob).toHaveBeenCalledWith("repo-uuid-1");
      expect(apiClient.getAnalysisJob).toHaveBeenCalledWith("job-uuid-1");
    });

    // Verify StageStepper rendered with Queued stage
    await waitFor(() => {
      expect(screen.getByText("Latest Analysis")).toBeInTheDocument();
      expect(screen.getByText("QUEUED")).toBeInTheDocument();
    });
  });

  it("surfaces error when submitAnalysisJob fails", async () => {
    vi.spyOn(authModule, "useAuth").mockReturnValue(mockAuthContext);
    const mockGetRepos = vi.spyOn(apiClient, "getRepositories").mockResolvedValue([mockRepo]);
    vi.spyOn(apiClient, "submitAnalysisJob").mockRejectedValue(
      new ApiError(403, "Forbidden", "Repository access denied by GitHub installation.")
    );

    render(<RepositoriesPage />);

    await waitFor(() => {
      expect(mockGetRepos).toHaveBeenCalled();
    });

    const runBtn = await screen.findByRole("button", { name: /Run Analysis/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(screen.getByText(/Repository access denied by GitHub installation/i)).toBeInTheDocument();
    });
  });
});
