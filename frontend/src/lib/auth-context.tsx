"use client";

/**
 * DevTwin Auth Context
 * Manages developer session state and wires the bearer token to the API client.
 * Uses a simple token store pattern — real Supabase integration can be dropped in
 * by replacing setToken/clearToken with a Supabase onAuthStateChange listener.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import { apiClient, ApiError } from "@/lib/api-client";
import type { DeveloperResponse } from "@/types/api";

interface AuthState {
  /** Raw bearer token — null when unauthenticated */
  token: string | null;
  /** Resolved developer profile — null until loaded */
  developer: DeveloperResponse | null;
  /** True while the initial session/profile check is in flight */
  loading: boolean;
  /** Non-null when auth or profile fetch has failed */
  error: string | null;
  /** Set a new token (call after successful Supabase sign-in) */
  setToken: (token: string) => void;
  /** Clear auth state (call on sign-out) */
  clearToken: () => void;
  /** Re-fetch the developer profile */
  refreshDeveloper: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Read a stored dev-mode token from sessionStorage.
 * This is ONLY for local development without a live Supabase instance.
 * Never persists a real production token in sessionStorage.
 */
function getPersistedDevToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return sessionStorage.getItem("devtwin_dev_token");
  } catch {
    return null;
  }
}

function persistDevToken(token: string | null) {
  if (typeof window === "undefined") return;
  try {
    if (token) {
      sessionStorage.setItem("devtwin_dev_token", token);
    } else {
      sessionStorage.removeItem("devtwin_dev_token");
    }
  } catch {
    // Storage unavailable — silent fail
  }
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [token, setTokenState] = useState<string | null>(null);
  const [developer, setDeveloper] = useState<DeveloperResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Read persisted dev token after mount to avoid hydration mismatch
  useEffect(() => {
    const persisted = getPersistedDevToken();
    if (persisted) {
      setTokenState(persisted);
    }
  }, []);

  // Wire the token into the API client on every change
  useEffect(() => {
    apiClient.setTokenGetter(() => token);
  }, [token]);

  const fetchDeveloper = useCallback(async () => {
    try {
      try {
        const dev = await apiClient.getDeveloperMe();
        setDeveloper(dev);
        setError(null);
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
          // Profile not yet created — provision identity via POST /developers/me
          const dev = await apiClient.createDeveloperMe();
          setDeveloper(dev);
          setError(null);
        } else {
          throw err;
        }
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        // Token is invalid or expired
        setDeveloper(null);
        setError("Session expired or invalid. Please sign in again.");
        persistDevToken(null);
        setTokenState(null);
      } else {
        setDeveloper(null);
        setError("Could not load your developer profile. The backend may be unavailable.");
      }
    }
  }, []);

  // When token changes to non-null, fetch the developer profile
  useEffect(() => {
    if (!token) return;
    let active = true;
    fetchDeveloper().finally(() => {
      if (active) setLoading(false);
    });
    return () => {
      active = false;
    };
  }, [token, fetchDeveloper]);

  const setToken = useCallback((newToken: string) => {
    persistDevToken(newToken);
    setTokenState(newToken);
    setError(null);
  }, []);

  const clearToken = useCallback(() => {
    persistDevToken(null);
    setTokenState(null);
    setDeveloper(null);
    setError(null);
  }, []);

  const refreshDeveloper = useCallback(async () => {
    if (!token) return;
    await fetchDeveloper();
  }, [token, fetchDeveloper]);

  return (
    <AuthContext.Provider
      value={{ token, developer, loading, error, setToken, clearToken, refreshDeveloper }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used inside <AuthProvider>");
  }
  return ctx;
}
