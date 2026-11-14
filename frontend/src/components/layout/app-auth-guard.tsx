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
 *
 * Gate: `isAuthenticated` from useAuth() — the SAME boolean the header
 * (src/components/layout/header.tsx) uses to decide its signed-in/
 * signed-out display. A bearer token alone is not sufficient: a stale or
 * backend-rejected token leaves `token` set but `developer` unresolved,
 * and previously this guard treated that as "authenticated" (rendering the
 * full protected dashboard shell) while the header correctly showed
 * signed-out. Both must now agree by construction, since both read the
 * same derived field instead of applying their own predicate.
 *
 * This component is split out from src/app/(app)/layout.tsx because Next's
 * route segment config (`export const instant = false` in the layout) is
 * only recognized in a Server Component module — a "use client" file
 * cannot export it. The layout stays a thin Server Component that declares
 * `instant = false` and renders this guard as its client boundary.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { Loader2 } from "lucide-react";

export function AppAuthGuard({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !isAuthenticated) {
      router.replace("/login");
    }
  }, [loading, isAuthenticated, router]);

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

  if (!isAuthenticated) {
    // Redirect is in flight (see effect above) — render nothing to avoid a
    // flash of protected content.
    return null;
  }

  return <>{children}</>;
}
