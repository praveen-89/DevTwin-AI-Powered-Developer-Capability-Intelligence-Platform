import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthPage } from "@/components/auth/auth-page";
import * as AuthContextModule from "@/lib/auth-context";

const mockReplace = vi.fn();
const mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace, push: vi.fn() }),
  useSearchParams: () => mockSearchParams,
}));

function mockAuth(overrides: Partial<AuthContextModule.AuthState> = {}) {
  const base: AuthContextModule.AuthState = {
    token: null,
    user: null,
    developer: null,
    isAuthenticated: false,
    loading: false,
    error: null,
    isConfigured: true,
    setToken: vi.fn(),
    clearToken: vi.fn(),
    signIn: vi.fn(),
    signUp: vi.fn(),
    signInWithGithub: vi.fn().mockResolvedValue({ error: null }),
    signInWithGoogle: vi.fn().mockResolvedValue({ error: null }),
    signOut: vi.fn(),
    refreshDeveloper: vi.fn(),
  };
  const merged = { ...base, ...overrides };
  vi.spyOn(AuthContextModule, "useAuth").mockReturnValue(merged);
  return merged;
}

describe("AuthPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams.forEach((_v, k) => mockSearchParams.delete(k));
  });

  it("renders the sign-in copy with both provider buttons", () => {
    mockAuth();
    render(<AuthPage />);
    expect(screen.getByText("Sign in to DevTwin")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with GitHub" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with Google" })).toBeInTheDocument();
  });

  it("calls signInWithGithub with no arguments when the GitHub button is clicked", async () => {
    const auth = mockAuth();
    render(<AuthPage />);
    fireEvent.click(screen.getByRole("button", { name: "Continue with GitHub" }));
    await waitFor(() => {
      expect(auth.signInWithGithub).toHaveBeenCalledTimes(1);
    });
  });

  it("calls signInWithGoogle with no arguments when the Google button is clicked", async () => {
    const auth = mockAuth();
    render(<AuthPage />);
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      expect(auth.signInWithGoogle).toHaveBeenCalledTimes(1);
    });
  });

  it("surfaces an error message when signInWithGithub fails", async () => {
    const auth = mockAuth();
    (auth.signInWithGithub as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      error: "GitHub provider is not enabled.",
    });
    render(<AuthPage />);
    fireEvent.click(screen.getByRole("button", { name: "Continue with GitHub" }));
    await waitFor(() => {
      expect(screen.getByText("GitHub provider is not enabled.")).toBeInTheDocument();
    });
  });

  it("surfaces an error message when signInWithGoogle fails", async () => {
    const auth = mockAuth();
    (auth.signInWithGoogle as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      error: "Google provider is not enabled.",
    });
    render(<AuthPage />);
    fireEvent.click(screen.getByRole("button", { name: "Continue with Google" }));
    await waitFor(() => {
      expect(screen.getByText("Google provider is not enabled.")).toBeInTheDocument();
    });
  });

  it("shows the dev-token fallback form when Supabase is not configured", () => {
    mockAuth({ isConfigured: false });
    render(<AuthPage />);
    expect(screen.getByPlaceholderText("eyJhbGciOi...")).toBeInTheDocument();
  });

  it("redirects to /dashboard when a session already exists", async () => {
    mockAuth({ token: "existing-token" });
    render(<AuthPage />);
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("surfaces a denied-access error from OAuth callback query params", () => {
    mockSearchParams.set("error", "access_denied");
    mockAuth();
    render(<AuthPage />);
    expect(screen.getByText(/cancelled/i)).toBeInTheDocument();
  });
});
