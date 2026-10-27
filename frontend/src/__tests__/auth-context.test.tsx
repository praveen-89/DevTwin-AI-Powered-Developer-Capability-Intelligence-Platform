import { renderHook, act, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import React from "react";
import { AuthProvider, useAuth } from "@/lib/auth-context";
import { apiClient, ApiError } from "@/lib/api-client";
import * as SupabaseModule from "@/lib/supabase";

describe("AuthContext and Supabase Session Integration", () => {
  const mockDeveloper = {
    id: "dev-uuid-1234",
    auth_user_id: "supabase-user-5678",
    github_account_id: null,
    created_at: "2026-10-26T00:00:00Z",
    updated_at: "2026-10-26T00:00:00Z",
  };

  const mockSupabaseAuth = {
    getSession: vi.fn(),
    onAuthStateChange: vi.fn(),
    signInWithPassword: vi.fn(),
    signUp: vi.fn(),
    signOut: vi.fn(),
  };

  const mockSupabaseClient = {
    auth: mockSupabaseAuth,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    sessionStorage.clear();

    mockSupabaseAuth.onAuthStateChange.mockReturnValue({
      data: { subscription: { unsubscribe: vi.fn() } },
    });
    mockSupabaseAuth.getSession.mockResolvedValue({
      data: { session: null },
      error: null,
    });

    vi.spyOn(SupabaseModule, "isSupabaseConfigured").mockReturnValue(true);
    vi.spyOn(SupabaseModule, "getSupabaseClient").mockReturnValue(mockSupabaseClient as any);

    vi.spyOn(apiClient, "getDeveloperMe").mockResolvedValue(mockDeveloper as any);
    vi.spyOn(apiClient, "createDeveloperMe").mockResolvedValue(mockDeveloper as any);
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <AuthProvider>{children}</AuthProvider>
  );

  it("restores session on mount when Supabase session is present", async () => {
    mockSupabaseAuth.getSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: "restored.supabase.jwt",
          user: { id: "user-abc", email: "dev@example.com" },
        },
      },
      error: null,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.token).toBe("restored.supabase.jwt");
      expect(result.current.user?.email).toBe("dev@example.com");
      expect(result.current.developer?.id).toBe("dev-uuid-1234");
      expect(apiClient.getDeveloperMe).toHaveBeenCalled();
    });
  });

  it("provisions developer profile if getDeveloperMe returns 404", async () => {
    mockSupabaseAuth.getSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: "new.developer.jwt",
          user: { id: "user-new", email: "new@example.com" },
        },
      },
      error: null,
    });

    vi.spyOn(apiClient, "getDeveloperMe").mockRejectedValueOnce(
      new ApiError(404, "Not Found", "Developer profile not found")
    );

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(apiClient.getDeveloperMe).toHaveBeenCalled();
      expect(apiClient.createDeveloperMe).toHaveBeenCalled();
      expect(result.current.developer?.id).toBe("dev-uuid-1234");
    });
  });

  it("synchronizes session token on signIn", async () => {
    mockSupabaseAuth.signInWithPassword.mockResolvedValueOnce({
      data: {
        session: {
          access_token: "signedin.supabase.jwt",
          user: { id: "user-123", email: "signin@devtwin.ai" },
        },
        user: { id: "user-123", email: "signin@devtwin.ai" },
      },
      error: null,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    let signInResult: any;
    await act(async () => {
      signInResult = await result.current.signIn("signin@devtwin.ai", "password123");
    });

    expect(signInResult.error).toBeNull();
    await waitFor(() => {
      expect(result.current.token).toBe("signedin.supabase.jwt");
      expect(result.current.user?.email).toBe("signin@devtwin.ai");
    });
  });

  it("clears state and calls supabase.auth.signOut on signOut", async () => {
    mockSupabaseAuth.getSession.mockResolvedValueOnce({
      data: {
        session: {
          access_token: "active.token",
          user: { id: "user-123", email: "active@example.com" },
        },
      },
      error: null,
    });

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.token).toBe("active.token");
    });

    await act(async () => {
      await result.current.signOut();
    });

    expect(mockSupabaseAuth.signOut).toHaveBeenCalled();
    expect(result.current.token).toBeNull();
    expect(result.current.user).toBeNull();
    expect(result.current.developer).toBeNull();
  });

  it("handles unconfigured Supabase gracefully without throwing", async () => {
    vi.spyOn(SupabaseModule, "isSupabaseConfigured").mockReturnValue(false);
    vi.spyOn(SupabaseModule, "getSupabaseClient").mockReturnValue(null);

    const { result } = renderHook(() => useAuth(), { wrapper });

    await waitFor(() => {
      expect(result.current.isConfigured).toBe(false);
      expect(result.current.token).toBeNull();
      expect(result.current.loading).toBe(false);
    });

    // Dev token fallback works
    act(() => {
      result.current.setToken("dev.test.token");
    });

    await waitFor(() => {
      expect(result.current.token).toBe("dev.test.token");
      expect(sessionStorage.getItem("devtwin_dev_token")).toBe("dev.test.token");
    });
  });
});
