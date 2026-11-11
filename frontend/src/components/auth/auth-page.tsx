"use client";

/**
 * DevTwin — Dedicated Login / Signup Page
 *
 * Shared by /login and /signup (two distinct URLs, one component with a
 * `mode` toggle, matching the AuthModal's existing sign-in/sign-up tab
 * pattern). GitHub OAuth is the primary path; Google is a visible but
 * disabled stub reserved for a later checkpoint.
 *
 * A logged-in user who lands here directly is redirected to /dashboard —
 * this page is never shown while a session already exists.
 */

import { useEffect, useId, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { InlineError } from "@/components/ui/empty-state";
import { GitBranch, KeyRound, Loader2, Shield } from "lucide-react";

export type AuthPageMode = "login" | "signup";

const COPY: Record<AuthPageMode, { title: string; subtitle: string; switchLabel: string; switchHref: string; switchCta: string }> = {
  login: {
    title: "Sign in to DevTwin",
    subtitle: "Continue with GitHub to resume tracking your evidence-backed capability profile.",
    switchLabel: "New to DevTwin?",
    switchHref: "/signup",
    switchCta: "Create an account",
  },
  signup: {
    title: "Create your DevTwin account",
    subtitle: "Connect GitHub to start building your evidence-backed capability profile.",
    switchLabel: "Already have an account?",
    switchHref: "/login",
    switchCta: "Sign in",
  },
};

/** Maps a Supabase OAuth callback error code to a readable message. */
function describeOAuthError(error: string | null, description: string | null): string | null {
  if (!error) return null;
  if (error === "access_denied") {
    return "GitHub sign-in was cancelled. You can try again when you're ready.";
  }
  return description || `Sign-in failed (${error}). Please try again.`;
}

export function AuthPage({ mode }: { mode: AuthPageMode }) {
  const titleId = useId();
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, loading, isConfigured, signInWithGithub, setToken } = useAuth();

  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [devTokenInput, setDevTokenInput] = useState("");

  const copy = COPY[mode];

  // Logged-in users should never see the auth form — send them to the dashboard.
  useEffect(() => {
    if (!loading && token) {
      router.replace("/dashboard");
    }
  }, [loading, token, router]);

  // Surface OAuth callback errors (denied access, expired state, etc.)
  useEffect(() => {
    const err = describeOAuthError(
      searchParams.get("error"),
      searchParams.get("error_description")
    );
    if (err) setErrorMessage(err);
  }, [searchParams]);

  async function handleGithubSignIn() {
    setErrorMessage(null);
    setSubmitting(true);
    const result = await signInWithGithub();
    // A successful call redirects the browser away from this page, so we
    // only ever reach this line on failure.
    if (result.error) {
      setErrorMessage(result.error);
    }
    setSubmitting(false);
  }

  function handleDevTokenSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!devTokenInput.trim()) {
      setErrorMessage("Please enter a valid JWT token.");
      return;
    }
    setToken(devTokenInput.trim());
    router.replace("/dashboard");
  }

  // While we don't yet know whether a session exists, or once we know one
  // does (redirect in flight), avoid flashing the auth form.
  if (loading || token) {
    return (
      <div className="flex min-h-screen w-full items-center justify-center bg-[#090d16]">
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" aria-hidden="true" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-[#090d16] px-4 py-12">
      <div className="w-full max-w-md rounded-xl border border-slate-800 bg-[#0d1526] shadow-2xl shadow-black/60 overflow-hidden">
        {/* Header */}
        <div className="flex items-center gap-2.5 px-6 py-5 border-b border-slate-800/80 bg-slate-900/40">
          <Link href="/" className="flex items-center gap-2.5" aria-label="DevTwin home">
            <div className="h-7 w-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
              <GitBranch className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
            </div>
            <span className="text-sm font-bold text-slate-100 tracking-tight">DevTwin</span>
          </Link>
        </div>

        <div className="p-6 space-y-5">
          <div className="space-y-1.5">
            <h1 id={titleId} className="text-lg font-semibold text-slate-100 flex items-center gap-2">
              <Shield className="h-4 w-4 text-cyan-400" aria-hidden="true" />
              {copy.title}
            </h1>
            <p className="text-sm text-slate-400 leading-relaxed">{copy.subtitle}</p>
          </div>

          {errorMessage && <InlineError message={errorMessage} />}

          <div className="space-y-2.5">
            <Button
              type="button"
              variant="primary"
              size="lg"
              className="w-full justify-center"
              loading={submitting}
              leftIcon={<GitBranch className="h-4 w-4" />}
              onClick={handleGithubSignIn}
              aria-label="Continue with GitHub"
            >
              Continue with GitHub
            </Button>

            <div className="relative">
              <Button
                type="button"
                variant="outline"
                size="lg"
                className="w-full justify-center opacity-60"
                disabled
                aria-label="Continue with Google (coming soon)"
                title="Google sign-in is coming soon"
              >
                <GoogleGlyph />
                Continue with Google
              </Button>
              <span className="absolute -top-2 right-2 rounded-full border border-slate-700 bg-slate-800 px-2 py-0.5 text-[10px] font-medium text-slate-400">
                Coming soon
              </span>
            </div>
          </div>

          {!isConfigured && (
            <DevTokenFallback
              value={devTokenInput}
              onChange={setDevTokenInput}
              onSubmit={handleDevTokenSubmit}
            />
          )}

          <p className="text-xs text-slate-500 text-center">
            {copy.switchLabel}{" "}
            <Link href={copy.switchHref} className="text-cyan-400 hover:text-cyan-300 font-medium">
              {copy.switchCta}
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

function GoogleGlyph() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden="true">
      <path
        fill="currentColor"
        d="M21.35 11.1h-9.17v2.92h5.26c-.23 1.49-1.66 4.36-5.26 4.36-3.17 0-5.76-2.62-5.76-5.85s2.59-5.85 5.76-5.85c1.8 0 3.01.77 3.7 1.43l2.53-2.44C16.95 4.16 14.84 3.2 12.18 3.2 7.1 3.2 3 7.27 3 12.4s4.1 9.2 9.18 9.2c5.3 0 8.8-3.73 8.8-8.98 0-.6-.07-1.06-.17-1.52Z"
      />
    </svg>
  );
}

function DevTokenFallback({
  value,
  onChange,
  onSubmit,
}: {
  value: string;
  onChange: (v: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}) {
  if (process.env.NODE_ENV === "production") {
    return (
      <div className="p-3.5 rounded-lg border border-amber-500/30 bg-amber-500/10 text-xs text-amber-200">
        Authentication is not configured for this deployment. Please contact the administrator.
      </div>
    );
  }
  return (
    <form onSubmit={onSubmit} className="p-3.5 rounded-lg border border-amber-500/30 bg-amber-500/10 space-y-2.5">
      <p className="text-[11px] text-amber-300/80 leading-relaxed">
        Supabase is not configured in this environment (<code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">NEXT_PUBLIC_SUPABASE_URL</code> /{" "}
        <code className="bg-amber-950/60 px-1 py-0.5 rounded text-amber-200">NEXT_PUBLIC_SUPABASE_ANON_KEY</code>). Enter a developer backend token for local testing.
      </p>
      <label className="text-xs font-medium text-slate-300 flex items-center gap-1.5">
        <KeyRound className="h-3.5 w-3.5 text-slate-400" />
        Backend Bearer Token (JWT)
      </label>
      <textarea
        rows={3}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="eyJhbGciOi..."
        className="w-full px-3 py-2 text-xs font-mono rounded-lg border border-slate-700 bg-slate-900/60 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-cyan-400 focus:ring-1 focus:ring-cyan-400"
      />
      <Button type="submit" variant="secondary" size="sm" className="w-full justify-center">
        Set Token
      </Button>
    </form>
  );
}
