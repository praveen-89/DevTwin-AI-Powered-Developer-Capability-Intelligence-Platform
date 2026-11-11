"use client";

/**
 * DevTwin — Authenticated App Route Guard
 *
 * Wraps every route inside the `(app)` group (dashboard, repositories,
 * capabilities, coderisk, skillgraph, evidence). Redirects unauthenticated
 * visitors to /login instead of rendering a broken/empty dashboard page.
 *
 * Session detection relies on `useAuth()` (Supabase session restoration or
 * the local dev-token fallback) — see src/lib/auth-context.tsx. This is a
 * client-side guard: Supabase's browser client persists sessions in
 * localStorage, not a cookie, so there is no session-aware Next.js
 * middleware check available without introducing @supabase/ssr, which is
 * out of scope for this change.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

export default function AuthenticatedAppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { token, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !token) {
      router.replace("/login");
    }
  }, [loading, token, router]);

  if (loading) {
    return (
      <div
        className="flex h-screen w-full items-center justify-center bg-[#090d16]"
        role="status"
        aria-label="Checking authentication"
      >
        <Loader2 className="h-6 w-6 animate-spin text-cyan-400" aria-hidden="true" />
      </div>
    );
  }

  if (!token) {
    // Redirect is in flight (see effect above) — render nothing to avoid a
    // flash of protected content.
    return null;
  }

  return <>{children}</>;
}
