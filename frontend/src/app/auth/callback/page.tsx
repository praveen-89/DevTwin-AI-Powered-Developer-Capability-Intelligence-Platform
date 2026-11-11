"use client";

/**
 * DevTwin — OAuth Callback Landing
 *
 * Supabase redirects here after the GitHub OAuth round-trip
 * (`signInWithOAuth({ redirectTo: "<origin>/auth/callback" })`). The
 * Supabase browser client (`detectSessionInUrl: true`, see
 * src/lib/supabase.ts) exchanges the `?code=` for a session automatically
 * during its own initialization, so this page's only job is to:
 *   1. Surface a denied/expired OAuth error visibly, instead of looping.
 *   2. Wait for AuthProvider to pick up the new session.
 *   3. Redirect to /dashboard once a token is present (first-time users
 *      still hit the existing POST /developers/me provisioning call inside
 *      AuthProvider's fetchDeveloper effect — unchanged here).
 *   4. Fall back to /login with an error if nothing happens within a
 *      reasonable timeout (e.g. a cancelled/expired PKCE exchange).
 */

import { Suspense, useEffect, useRef, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

const CALLBACK_TIMEOUT_MS = 10_000;

function CallbackSpinner() {
  return (
    <div className="flex min-h-screen w-full flex-col items-center justify-center gap-3 bg-[#090d16] px-4 text-center">
      <Loader2 className="h-6 w-6 animate-spin text-cyan-400" aria-hidden="true" />
      <p className="text-sm text-slate-400">Completing sign-in…</p>
    </div>
  );
}

// `useSearchParams()` opts this page out of static prerendering in Next.js
// 16's Cache Components model unless isolated behind <Suspense> — the
// fallback below is shown for the (effectively instant) client-side read.
export default function AuthCallbackPage() {
  return (
    <Suspense fallback={<CallbackSpinner />}>
      <AuthCallbackContent />
    </Suspense>
  );
}

function AuthCallbackContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { token, loading } = useAuth();
  const [timedOut, setTimedOut] = useState(false);
  const redirected = useRef(false);

  useEffect(() => {
    const oauthError = searchParams.get("error");
    if (oauthError) {
      const description = searchParams.get("error_description") ?? "";
      const qs = new URLSearchParams({ error: oauthError, ...(description ? { error_description: description } : {}) });
      router.replace(`/login?${qs.toString()}`);
      return;
    }

    const timer = window.setTimeout(() => setTimedOut(true), CALLBACK_TIMEOUT_MS);
    return () => window.clearTimeout(timer);
  }, [router, searchParams]);

  useEffect(() => {
    if (redirected.current) return;
    if (!loading && token) {
      redirected.current = true;
      router.replace("/dashboard");
    }
  }, [loading, token, router]);

  useEffect(() => {
    if (timedOut && !token) {
      router.replace(
        "/login?error=callback_timeout&error_description=Sign-in+took+too+long.+Please+try+again."
      );
    }
  }, [timedOut, token, router]);

  return <CallbackSpinner />;
}
