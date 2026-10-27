"use client";

/**
 * DevTwin Auth Context
 * Manages developer session state, Supabase auth lifecycle,
 * and wires the bearer token to the API client.
 */

import React, {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import type { User } from "@supabase/supabase-js";
import { apiClient, ApiError } from "@/lib/api-client";
import { getSupabaseClient, isSupabaseConfigured } from "@/lib/supabase";
import type { DeveloperResponse } from "@/types/api";

export interface AuthState {
  /** Raw bearer token — null when unauthenticated */
  token: string | null;
  /** Supabase authenticated user object — null when unauthenticated or using dev token */
  user: User | null;
  /** Resolved developer profile — null until loaded */
  developer: DeveloperResponse | null;
  /** True while the initial session/profile check or an auth action is in flight */
  loading: boolean;
  /** Non-null when auth or profile fetch has failed */
  error: string | null;
  /** Whether Supabase is configured with valid environment variables */
  isConfigured: boolean;
  /** Set a manual dev token (fallback for dev/testing environments) */
  setToken: (token: string) => void;
  /** Clear auth state and sign out */
  clearToken: () => void;
  /** Authenticate with email and password via Supabase */
  signIn: (email: string, password: string) => Promise<{ error: string | null }>;
  /** Register a new user with email and password via Supabase */
  signUp: (email: string, password: string) => Promise<{
    error: string | null;
    emailConfirmationRequired: boolean;
  }>;
  /** Sign out of Supabase and clear session state */
  signOut: () => Promise<void>;
  /** Re-fetch the developer profile */
  refreshDeveloper: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

/**
 * Read a stored dev-mode token from sessionStorage.
 * This is used for local development fallback or testing.
 */
function getPersistedDevToken(): string | null {
  if (typeof window === "undefined") return null;
  if (process.env.NODE_ENV === "production") return null;
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
  const [user, setUser] = useState<User | null>(null);
  const [developer, setDeveloper] = useState<DeveloperResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const isConfigured = isSupabaseConfigured();
  const supabase = useMemo(() => getSupabaseClient(), []);

  // Fetch or provision developer identity
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
        setUser(null);
      } else {
        setDeveloper(null);
        setError("Could not load your developer profile. The backend may be unavailable.");
      }
    }
  }, []);

  // Wire token getter to apiClient
  useEffect(() => {
    apiClient.setTokenGetter(async () => {
      if (supabase) {
        try {
          const { data } = await supabase.auth.getSession();
          if (data.session?.access_token) {
            return data.session.access_token;
          }
        } catch {
          // Fall back to token in state
        }
      }
      return token;
    });
  }, [supabase, token]);

  // Initial session restoration and Supabase auth lifecycle
  useEffect(() => {
    let active = true;

    async function initializeAuth() {
      if (supabase) {
        try {
          const { data, error: sessionErr } = await supabase.auth.getSession();
          if (!active) return;

          if (sessionErr) {
            setError(sessionErr.message);
          } else if (data.session?.access_token) {
            setTokenState(data.session.access_token);
            setUser(data.session.user);
            return;
          }
        } catch (e: unknown) {
          if (!active) return;
          console.error("Failed to restore Supabase session", e);
        }
      }

      // If no Supabase session or Supabase not configured, check persisted dev token
      const persisted = getPersistedDevToken();
      if (persisted && active) {
        setTokenState(persisted);
      } else if (active) {
        setLoading(false);
      }
    }

    initializeAuth();

    // Subscribe to auth state changes if Supabase is active
    if (supabase) {
      const { data: { subscription } } = supabase.auth.onAuthStateChange(
        async (event, session) => {
          if (!active) return;

          if (session?.access_token) {
            setTokenState(session.access_token);
            setUser(session.user);
            setError(null);
          } else if (event === "SIGNED_OUT") {
            setTokenState(null);
            setUser(null);
            setDeveloper(null);
            persistDevToken(null);
            setError(null);
            setLoading(false);
          }
        }
      );

      return () => {
        active = false;
        subscription.unsubscribe();
      };
    }

    return () => {
      active = false;
    };
  }, [supabase]);

  // Whenever token changes, fetch/provision developer profile
  useEffect(() => {
    if (!token) {
      setDeveloper(null);
      setLoading(false);
      return;
    }

    let active = true;
    setLoading(true);
    fetchDeveloper().finally(() => {
      if (active) setLoading(false);
    });

    return () => {
      active = false;
    };
  }, [token, fetchDeveloper]);

  // Sign In via Supabase email/password
  const signIn = useCallback(
    async (email: string, password: string): Promise<{ error: string | null }> => {
      if (!supabase) {
        const msg = "Supabase authentication is not configured. Please check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.";
        setError(msg);
        return { error: msg };
      }

      setLoading(true);
      setError(null);

      try {
        const { data, error: sbError } = await supabase.auth.signInWithPassword({
          email: email.trim(),
          password,
        });

        if (sbError) {
          setError(sbError.message);
          return { error: sbError.message };
        }

        if (data.session) {
          setTokenState(data.session.access_token);
          setUser(data.user);
          persistDevToken(data.session.access_token);
        }

        return { error: null };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to sign in.";
        setError(msg);
        return { error: msg };
      } finally {
        setLoading(false);
      }
    },
    [supabase]
  );

  // Sign Up via Supabase email/password
  const signUp = useCallback(
    async (
      email: string,
      password: string
    ): Promise<{ error: string | null; emailConfirmationRequired: boolean }> => {
      if (!supabase) {
        const msg = "Supabase authentication is not configured. Please check NEXT_PUBLIC_SUPABASE_URL and NEXT_PUBLIC_SUPABASE_ANON_KEY.";
        setError(msg);
        return { error: msg, emailConfirmationRequired: false };
      }

      setLoading(true);
      setError(null);

      try {
        const { data, error: sbError } = await supabase.auth.signUp({
          email: email.trim(),
          password,
        });

        if (sbError) {
          setError(sbError.message);
          return { error: sbError.message, emailConfirmationRequired: false };
        }

        // When email confirmation is required by Supabase, session is null
        const emailConfirmationRequired = !data.session;

        if (data.session) {
          setTokenState(data.session.access_token);
          setUser(data.user);
          persistDevToken(data.session.access_token);
        }

        return { error: null, emailConfirmationRequired };
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Failed to sign up.";
        setError(msg);
        return { error: msg, emailConfirmationRequired: false };
      } finally {
        setLoading(false);
      }
    },
    [supabase]
  );

  // Sign Out
  const signOut = useCallback(async () => {
    setLoading(true);
    try {
      if (supabase) {
        await supabase.auth.signOut();
      }
    } catch (err) {
      console.error("Sign-out error", err);
    } finally {
      persistDevToken(null);
      setTokenState(null);
      setUser(null);
      setDeveloper(null);
      setError(null);
      setLoading(false);
    }
  }, [supabase]);

  // Backward-compatible token setters for dev mode and tests
  const setToken = useCallback((newToken: string) => {
    if (process.env.NODE_ENV === "production") {
      console.warn("Manual dev token injection is disabled in production.");
      return;
    }
    persistDevToken(newToken);
    setTokenState(newToken);
    setError(null);
  }, []);

  const clearToken = useCallback(() => {
    signOut();
  }, [signOut]);

  const refreshDeveloper = useCallback(async () => {
    if (!token) return;
    await fetchDeveloper();
  }, [token, fetchDeveloper]);

  return (
    <AuthContext.Provider
      value={{
        token,
        user,
        developer,
        loading,
        error,
        isConfigured,
        setToken,
        clearToken,
        signIn,
        signUp,
        signOut,
        refreshDeveloper,
      }}
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
