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

  it("renders the login copy and a primary GitHub button for mode=login", () => {
    mockAuth();
    render(<AuthPage mode="login" />);
    expect(screen.getByText("Sign in to DevTwin")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Continue with GitHub" })).toBeInTheDocument();
  });

  it("renders the signup copy for mode=signup", () => {
    mockAuth();
    render(<AuthPage mode="signup" />);
    expect(screen.getByText("Create your DevTwin account")).toBeInTheDocument();
  });

  it("calls signInWithGithub with no arguments when the GitHub button is clicked", async () => {
    const auth = mockAuth();
    render(<AuthPage mode="login" />);
    fireEvent.click(screen.getByRole("button", { name: "Continue with GitHub" }));
    await waitFor(() => {
      expect(auth.signInWithGithub).toHaveBeenCalledTimes(1);
    });
  });

  it("shows the Google button disabled with a coming-soon affordance", () => {
    mockAuth();
    render(<AuthPage mode="login" />);
    const googleBtn = screen.getByRole("button", { name: /Continue with Google/i });
    expect(googleBtn).toBeDisabled();
    expect(screen.getByText("Coming soon")).toBeInTheDocument();
  });

  it("surfaces an error message when signInWithGithub fails", async () => {
    const auth = mockAuth();
    (auth.signInWithGithub as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
      error: "GitHub provider is not enabled.",
    });
    render(<AuthPage mode="login" />);
    fireEvent.click(screen.getByRole("button", { name: "Continue with GitHub" }));
    await waitFor(() => {
      expect(screen.getByText("GitHub provider is not enabled.")).toBeInTheDocument();
    });
  });

  it("shows the dev-token fallback form when Supabase is not configured", () => {
    mockAuth({ isConfigured: false });
    render(<AuthPage mode="login" />);
    expect(screen.getByPlaceholderText("eyJhbGciOi...")).toBeInTheDocument();
  });

  it("redirects to /dashboard when a session already exists", async () => {
    mockAuth({ token: "existing-token" });
    render(<AuthPage mode="login" />);
    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/dashboard");
    });
  });

  it("surfaces a denied-access error from OAuth callback query params", () => {
    mockSearchParams.set("error", "access_denied");
    mockAuth();
    render(<AuthPage mode="login" />);
    expect(screen.getByText(/cancelled/i)).toBeInTheDocument();
  });
});
