"use client";

import { useEffect, useState, useId } from "react";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { InlineError } from "@/components/ui/empty-state";
import {
  AlertCircle,
  CheckCircle2,
  KeyRound,
  Lock,
  Mail,
  Shield,
  X,
} from "lucide-react";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

type AuthMode = "signin" | "signup";

export function AuthModal({ isOpen, onClose }: AuthModalProps) {
  const titleId = useId();
  const { signIn, signUp, setToken, isConfigured, loading } = useAuth();

  const [mode, setMode] = useState<AuthMode>("signin");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [devTokenInput, setDevTokenInput] = useState("");

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmationNotice, setConfirmationNotice] = useState<string | null>(null);

  // Close on Escape key
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape" && isOpen) {
        onClose();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  // Reset errors and notice when modal reopens or mode changes
  useEffect(() => {
    if (isOpen) {
      setErrorMessage(null);
      setConfirmationNotice(null);
    }
  }, [isOpen, mode]);

  if (!isOpen) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setErrorMessage(null);
    setConfirmationNotice(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setErrorMessage("Please enter an email address.");
      return;
    }
    if (!password) {
      setErrorMessage("Please enter a password.");
      return;
    }
    if (password.length < 6) {
      setErrorMessage("Password must be at least 6 characters long.");
      return;
    }

    setSubmitting(true);
    try {
      if (mode === "signin") {
        const result = await signIn(trimmedEmail, password);
        if (result.error) {
          setErrorMessage(result.error);
        } else {
          onClose();
        }
      } else {
        const result = await signUp(trimmedEmail, password);
        if (result.error) {
          setErrorMessage(result.error);
        } else if (result.emailConfirmationRequired) {
          setConfirmationNotice(
            `Verification email sent to ${trimmedEmail}. Please check your inbox to confirm your account.`
          );
        } else {
          // Automatic login occurred
          onClose();
        }
      }
    } finally {
      setSubmitting(false);
    }
  }

  function handleDevTokenSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!devTokenInput.trim()) {
      setErrorMessage("Please enter a valid JWT token.");
      return;
    }
    setToken(devTokenInput.trim());
    onClose();
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-in fade-in"
      role="dialog"
      aria-modal="true"
      aria-labelledby={titleId}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0d1526] shadow-2xl shadow-black/60 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800/80 bg-slate-900/40">
          <div className="flex items-center gap-2.5">
            <div className="p-1.5 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400">
              <Shield className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h2 id={titleId} className="text-sm font-semibold text-slate-100">
                {mode === "signin" ? "Sign in to DevTwin" : "Create DevTwin Account"}
              </h2>
              <p className="text-xs text-slate-400">
                AI-Powered Developer Capability Intelligence
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
            aria-label="Close authentication modal"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Unconfigured Supabase Notice */}
        {!isConfigured && (
          <div className="m-5 p-3.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-xs text-amber-200 space-y-2">
            <div className="flex items-center gap-2 font-medium">
              <AlertCircle className="h-4 w-4 text-amber-400 shrink-0" />
              <span>{process.env.NODE_ENV === "production" ? "Authentication Service Unavailable" : "Supabase Not Configured"}</span>
            </div>
            {process.env.NODE_ENV === "production" ? (
              <p className="text-[11px] text-amber-300/80 leading-relaxed">
                Authentication services are not configured for this deployment. Please contact the administrator.
              </p>
            ) : (
              <>
                <p className="text-[11px] text-amber-300/80 leading-relaxed">
                  Environment variables <code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">NEXT_PUBLIC_SUPABASE_URL</code> and{" "}
                  <code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">NEXT_PUBLIC_SUPABASE_ANON_KEY</code> are not set in{" "}
                  <code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">frontend/.env.local</code>.
                </p>
                <p className="text-[11px] text-amber-300/80">
                  You can enter a developer backend token directly below for local development.
                </p>
              </>
            )}
          </div>
        )}

        {/* Content */}
        {isConfigured ? (
          <div className="p-6 space-y-4">
            {/* Mode switcher tabs */}
            <div className="grid grid-cols-2 p-1 rounded-lg bg-slate-900/80 border border-slate-800" role="tablist">
              <button
                type="button"
                role="tab"
                aria-selected={mode === "signin"}
                onClick={() => setMode("signin")}
                className={`py-1.5 text-xs font-medium rounded-md transition-all ${
                  mode === "signin"
                    ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Sign In
              </button>
              <button
                type="button"
                role="tab"
                aria-selected={mode === "signup"}
                onClick={() => setMode("signup")}
                className={`py-1.5 text-xs font-medium rounded-md transition-all ${
                  mode === "signup"
                    ? "bg-cyan-500/15 text-cyan-300 border border-cyan-500/30 shadow-sm"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                Sign Up
              </button>
            </div>

            {errorMessage && <InlineError message={errorMessage} />}

            {confirmationNotice && (
              <div className="p-3.5 rounded-lg border border-emerald-500/30 bg-emerald-500/10 text-emerald-300 text-xs flex items-start gap-2.5">
                <CheckCircle2 className="h-4 w-4 text-emerald-400 shrink-0 mt-0.5" />
                <div className="space-y-1">
                  <p className="font-medium text-emerald-200">Confirmation Required</p>
                  <p className="text-emerald-300/90 leading-relaxed text-[11px]">
                    {confirmationNotice}
                  </p>
                </div>
              </div>
            )}

            {!confirmationNotice && (
              <form onSubmit={handleSubmit} noValidate className="space-y-3.5">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Mail className="h-3.5 w-3.5 text-slate-400" />
                    Email
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="developer@example.com"
                    autoComplete="email"
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-700 bg-slate-900/60 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                    autoFocus
                  />
                </div>

                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                    <Lock className="h-3.5 w-3.5 text-slate-400" />
                    Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    autoComplete={mode === "signin" ? "current-password" : "new-password"}
                    className="w-full px-3 py-2 text-xs rounded-lg border border-slate-700 bg-slate-900/60 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                  />
                </div>

                <div className="pt-2">
                  <Button
                    type="submit"
                    variant="primary"
                    size="sm"
                    loading={submitting || loading}
                    className="w-full justify-center"
                    aria-label={mode === "signin" ? "Submit Sign In" : "Submit Sign Up"}
                  >
                    {mode === "signin" ? "Sign In" : "Create Account"}
                  </Button>
                </div>
              </form>
            )}
          </div>
        ) : process.env.NODE_ENV === "production" ? (
          <div className="p-6 text-center space-y-4">
            <p className="text-xs text-slate-400">
              Manual token injection is disabled in production environments.
            </p>
            <Button type="button" variant="outline" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        ) : (
          /* Manual Dev Token Fallback Form when Supabase env vars are missing */
          <form onSubmit={handleDevTokenSubmit} className="p-6 space-y-4">
            {errorMessage && <InlineError message={errorMessage} />}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
                <KeyRound className="h-3.5 w-3.5 text-slate-400" />
                Backend Bearer Token (JWT)
              </label>
              <textarea
                rows={3}
                required
                value={devTokenInput}
                onChange={(e) => setDevTokenInput(e.target.value)}
                placeholder="eyJhbGciOi..."
                className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-700 bg-slate-900/60 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
                autoFocus
              />
            </div>
            <div className="flex gap-2 justify-end pt-1">
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                variant="primary"
                size="sm"
              >
                Set Token
              </Button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
