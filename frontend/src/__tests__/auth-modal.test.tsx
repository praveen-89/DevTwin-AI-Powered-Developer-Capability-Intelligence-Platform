import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { AuthModal } from "@/components/auth/auth-modal";
import * as AuthContextModule from "@/lib/auth-context";

describe("AuthModal", () => {
  const mockSignIn = vi.fn();
  const mockSignUp = vi.fn();
  const mockSetToken = vi.fn();
  const mockClose = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      token: null,
      user: null,
      developer: null,
      loading: false,
      error: null,
      isConfigured: true,
      setToken: mockSetToken,
      clearToken: vi.fn(),
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: vi.fn(),
      refreshDeveloper: vi.fn(),
    });
  });

  it("does not render when isOpen is false", () => {
    render(<AuthModal isOpen={false} onClose={mockClose} />);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });

  it("renders sign-in form with email and password inputs when open", () => {
    render(<AuthModal isOpen={true} onClose={mockClose} />);
    expect(screen.getByRole("dialog")).toBeInTheDocument();
    expect(screen.getByText("Sign in to DevTwin")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("developer@example.com")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("••••••••")).toBeInTheDocument();
  });

  it("switches to Sign Up tab when clicked", () => {
    render(<AuthModal isOpen={true} onClose={mockClose} />);
    const signUpTab = screen.getByRole("tab", { name: "Sign Up" });
    fireEvent.click(signUpTab);

    expect(screen.getByText("Create DevTwin Account")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Submit Sign Up" })).toBeInTheDocument();
  });

  it("validates empty inputs and short password", async () => {
    render(<AuthModal isOpen={true} onClose={mockClose} />);
    const submitBtn = screen.getByRole("button", { name: "Submit Sign In" });

    // Submit with empty fields
    fireEvent.click(submitBtn);
    expect(screen.getByText("Please enter an email address.")).toBeInTheDocument();

    // Enter email but no password
    fireEvent.change(screen.getByPlaceholderText("developer@example.com"), {
      target: { value: "test@devtwin.ai" },
    });
    fireEvent.click(submitBtn);
    expect(screen.getByText("Please enter a password.")).toBeInTheDocument();

    // Enter short password
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "123" },
    });
    fireEvent.click(submitBtn);
    expect(screen.getByText("Password must be at least 6 characters long.")).toBeInTheDocument();
  });

  it("calls signIn on valid submit and closes on success", async () => {
    mockSignIn.mockResolvedValueOnce({ error: null });

    render(<AuthModal isOpen={true} onClose={mockClose} />);
    fireEvent.change(screen.getByPlaceholderText("developer@example.com"), {
      target: { value: "dev@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "securepassword123" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit Sign In" }));

    await waitFor(() => {
      expect(mockSignIn).toHaveBeenCalledWith("dev@example.com", "securepassword123");
      expect(mockClose).toHaveBeenCalledTimes(1);
    });
  });

  it("displays error message when signIn fails", async () => {
    mockSignIn.mockResolvedValueOnce({ error: "Invalid login credentials" });

    render(<AuthModal isOpen={true} onClose={mockClose} />);
    fireEvent.change(screen.getByPlaceholderText("developer@example.com"), {
      target: { value: "dev@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "wrongpassword" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit Sign In" }));

    await waitFor(() => {
      expect(screen.getByText("Invalid login credentials")).toBeInTheDocument();
      expect(mockClose).not.toHaveBeenCalled();
    });
  });

  it("shows confirmation notice when signUp requires email verification", async () => {
    mockSignUp.mockResolvedValueOnce({
      error: null,
      emailConfirmationRequired: true,
    });

    render(<AuthModal isOpen={true} onClose={mockClose} />);
    fireEvent.click(screen.getByRole("tab", { name: "Sign Up" }));

    fireEvent.change(screen.getByPlaceholderText("developer@example.com"), {
      target: { value: "newuser@example.com" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "strongpassword" },
    });

    fireEvent.click(screen.getByRole("button", { name: "Submit Sign Up" }));

    await waitFor(() => {
      expect(screen.getByText("Confirmation Required")).toBeInTheDocument();
      expect(
        screen.getByText(/Verification email sent to newuser@example.com/)
      ).toBeInTheDocument();
    });
  });

  it("renders dev token fallback form when isConfigured is false", () => {
    vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
      token: null,
      user: null,
      developer: null,
      loading: false,
      error: null,
      isConfigured: false,
      setToken: mockSetToken,
      clearToken: vi.fn(),
      signIn: mockSignIn,
      signUp: mockSignUp,
      signOut: vi.fn(),
      refreshDeveloper: vi.fn(),
    });

    render(<AuthModal isOpen={true} onClose={mockClose} />);

    expect(screen.getByText("Supabase Not Configured")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("eyJhbGciOi...")).toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("eyJhbGciOi..."), {
      target: { value: "mock.jwt.token" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Set Token" }));

    expect(mockSetToken).toHaveBeenCalledWith("mock.jwt.token");
    expect(mockClose).toHaveBeenCalledTimes(1);
  });

  it("disables manual dev token fallback when running in production", () => {
    const originalEnv = process.env.NODE_ENV;
    try {
      (process.env as any).NODE_ENV = "production";

      vi.spyOn(AuthContextModule, "useAuth").mockReturnValue({
        token: null,
        user: null,
        developer: null,
        loading: false,
        error: null,
        isConfigured: false,
        setToken: mockSetToken,
        clearToken: vi.fn(),
        signIn: mockSignIn,
        signUp: mockSignUp,
        signOut: vi.fn(),
        refreshDeveloper: vi.fn(),
      });

      render(<AuthModal isOpen={true} onClose={mockClose} />);

      expect(screen.getByText("Authentication Service Unavailable")).toBeInTheDocument();
      expect(screen.getByText("Manual token injection is disabled in production environments.")).toBeInTheDocument();
      expect(screen.queryByPlaceholderText("eyJhbGciOi...")).toBeNull();
      expect(screen.queryByRole("button", { name: "Set Token" })).toBeNull();
    } finally {
      (process.env as any).NODE_ENV = originalEnv;
    }
  });
});
