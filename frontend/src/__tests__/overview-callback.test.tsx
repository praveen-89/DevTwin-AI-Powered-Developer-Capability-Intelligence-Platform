import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { OverviewView } from "@/components/overview/overview-view";
import { apiClient } from "@/lib/api-client";
import * as AuthContextModule from "@/lib/auth-context";

describe("OverviewView Callback Feedback and URL Sanitization", () => {
  const mockDeveloper = {
    id: "dev-123",
    auth_user_id: "auth-123",
    github_account_id: null,
    created_at: "2026-10-26T00:00:00Z",
    updated_at: "2026-10-26T00:00:00Z",
  };

  beforeEach(() => {
    vi.clearAllMocks();

    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      token: "test.token",
      user: null,
      developer: mockDeveloper as any,
      loading: false,
      error: null,
      isConfigured: true,
      setToken: vi.fn(),
      clearToken: vi.fn(),
      signIn: vi.fn(),
      signUp: vi.fn(),
      signOut: vi.fn(),
      refreshDeveloper: vi.fn(),
    });

    vi.spyOn(apiClient, "getGitHubStatus").mockResolvedValue({
      is_connected: true,
      is_installed: true,
      is_disconnected: false,
      github_username: "octocat",
    });

    vi.spyOn(apiClient, "getRepositories").mockResolvedValue([]);
    vi.spyOn(apiClient, "getProjects").mockResolvedValue([]);
    vi.spyOn(apiClient, "getCapabilities").mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });
    vi.spyOn(apiClient, "getEvidence").mockResolvedValue({ items: [], total: 0, limit: 10, offset: 0 });
  });

  it("displays success banner and sanitizes URL when ?github=success is present", async () => {
    // Set window.location search
    window.history.pushState({}, "Test", "/?github=success");
    const replaceStateSpy = vi.spyOn(window.history, "replaceState");

    render(<OverviewView />);

    await waitFor(() => {
      expect(
        screen.getByText("GitHub account connected successfully! Your accessible repositories are ready.")
      ).toBeInTheDocument();
    });

    // Verify apiClient.getGitHubStatus was called to refresh
    expect(apiClient.getGitHubStatus).toHaveBeenCalled();

    // Verify URL was sanitized without full page reload
    expect(replaceStateSpy).toHaveBeenCalled();
    const replacedUrl = replaceStateSpy.mock.calls[0][2];
    expect(replacedUrl).not.toContain("github=success");
  });

  it("displays error banner when ?github_error=access_denied is present", async () => {
    window.history.pushState({}, "Test", "/?github_error=access_denied");
    const replaceStateSpy = vi.spyOn(window.history, "replaceState");

    render(<OverviewView />);

    await waitFor(() => {
      expect(
        screen.getByText("GitHub App authorization was cancelled or denied.")
      ).toBeInTheDocument();
    });

    expect(replaceStateSpy).toHaveBeenCalled();
  });

  it("dismisses callback feedback banner when close button is clicked", async () => {
    window.history.pushState({}, "Test", "/?github=success");

    render(<OverviewView />);

    await waitFor(() => {
      expect(
        screen.getByText("GitHub account connected successfully! Your accessible repositories are ready.")
      ).toBeInTheDocument();
    });

    const dismissButton = screen.getByRole("button", { name: "Dismiss message" });
    fireEvent.click(dismissButton);

    expect(
      screen.queryByText("GitHub account connected successfully! Your accessible repositories are ready.")
    ).not.toBeInTheDocument();
  });
});
