import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AddRepositoryDialog } from "@/components/repositories/add-repository-dialog";
import { apiClient, ApiError } from "@/lib/api-client";
import type { GitHubRepositoryOption, ProjectResponse, RepositoryResponse } from "@/types/api";

describe("AddRepositoryDialog", () => {
  const mockProjects: ProjectResponse[] = [
    { id: "proj-123", name: "Alpha Project", created_at: "2026-10-20T00:00:00Z" },
    { id: "proj-456", name: "Beta Project", created_at: "2026-10-21T00:00:00Z" },
  ];

  const mockGitHubRepos: GitHubRepositoryOption[] = [
    {
      github_repo_id: 101,
      name: "frontend-repo",
      full_name: "org/frontend-repo",
      visibility: "public",
      private: false,
      default_branch: "main",
    },
    {
      github_repo_id: 102,
      name: "backend-repo",
      full_name: "org/backend-repo",
      visibility: "private",
      private: true,
      default_branch: "develop",
    },
  ];

  const mockCreatedRepo: RepositoryResponse = {
    id: "repo-999",
    project_id: "proj-123",
    github_repo_id: 101,
    owner_login: "org",
    name: "frontend-repo",
    full_name: "org/frontend-repo",
    url: "https://github.com/org/frontend-repo",
    default_branch: "main",
    visibility: "public",
    synced_at: null,
    created_at: "2026-10-25T00:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("does not render when isOpen is false", () => {
    render(<AddRepositoryDialog isOpen={false} onClose={vi.fn()} onSuccess={vi.fn()} />);
    expect(screen.queryByRole("dialog")).toBeNull();
  });

  it("loads and displays projects and accessible GitHub repositories", async () => {
    vi.spyOn(apiClient, "getProjects").mockResolvedValue(mockProjects);
    vi.spyOn(apiClient, "getGitHubRepositories").mockResolvedValue(mockGitHubRepos);

    render(<AddRepositoryDialog isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    expect(screen.getByRole("dialog")).toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByText("Alpha Project")).toBeInTheDocument();
      expect(screen.getByText("org/frontend-repo")).toBeInTheDocument();
      expect(screen.getByText("org/backend-repo")).toBeInTheDocument();
    });
  });

  it("registers repository under selected existing project", async () => {
    vi.spyOn(apiClient, "getProjects").mockResolvedValue(mockProjects);
    vi.spyOn(apiClient, "getGitHubRepositories").mockResolvedValue(mockGitHubRepos);
    const createRepoSpy = vi.spyOn(apiClient, "createRepository").mockResolvedValue(mockCreatedRepo);
    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(<AddRepositoryDialog isOpen={true} onClose={onClose} onSuccess={onSuccess} />);

    await waitFor(() => {
      expect(screen.getByText("org/frontend-repo")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: /Register Repository/i });
    expect(submitBtn).not.toBeDisabled();
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createRepoSpy).toHaveBeenCalledWith("proj-123", 101);
      expect(onSuccess).toHaveBeenCalledWith(mockCreatedRepo);
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("creates a new project first if user switches to new project mode", async () => {
    vi.spyOn(apiClient, "getProjects").mockResolvedValue(mockProjects);
    vi.spyOn(apiClient, "getGitHubRepositories").mockResolvedValue(mockGitHubRepos);
    const createProjectSpy = vi.spyOn(apiClient, "createProject").mockResolvedValue({
      id: "new-proj-id",
      name: "Brand New Project",
      created_at: "2026-10-25T00:00:00Z",
    });
    const createRepoSpy = vi.spyOn(apiClient, "createRepository").mockResolvedValue({
      ...mockCreatedRepo,
      project_id: "new-proj-id",
    });
    const onSuccess = vi.fn();
    const onClose = vi.fn();

    render(<AddRepositoryDialog isOpen={true} onClose={onClose} onSuccess={onSuccess} />);

    await waitFor(() => {
      expect(screen.getByText("+ Create new project")).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText("+ Create new project"));

    const input = screen.getByPlaceholderText(/e\.g\. Minor Project/i);
    fireEvent.change(input, { target: { value: "Brand New Project" } });

    const submitBtn = screen.getByRole("button", { name: /Register Repository/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(createProjectSpy).toHaveBeenCalledWith("Brand New Project");
      expect(createRepoSpy).toHaveBeenCalledWith("new-proj-id", 101);
      expect(onSuccess).toHaveBeenCalled();
      expect(onClose).toHaveBeenCalled();
    });
  });

  it("handles duplicate repository registration error (409)", async () => {
    vi.spyOn(apiClient, "getProjects").mockResolvedValue(mockProjects);
    vi.spyOn(apiClient, "getGitHubRepositories").mockResolvedValue(mockGitHubRepos);
    vi.spyOn(apiClient, "createRepository").mockRejectedValue(
      new ApiError(409, "Conflict", "Repository already registered.")
    );

    render(<AddRepositoryDialog isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    await waitFor(() => {
      expect(screen.getByText("org/frontend-repo")).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: /Register Repository/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/This repository is already registered in DevTwin/i)).toBeInTheDocument();
    });
  });

  it("displays empty state when GitHub returns no accessible repositories", async () => {
    vi.spyOn(apiClient, "getProjects").mockResolvedValue(mockProjects);
    vi.spyOn(apiClient, "getGitHubRepositories").mockResolvedValue([]);

    render(<AddRepositoryDialog isOpen={true} onClose={vi.fn()} onSuccess={vi.fn()} />);

    await waitFor(() => {
      expect(
        screen.getByText(/No accessible repositories found for your GitHub App installation/i)
      ).toBeInTheDocument();
    });

    const submitBtn = screen.getByRole("button", { name: /Register Repository/i });
    expect(submitBtn).toBeDisabled();
  });
});
