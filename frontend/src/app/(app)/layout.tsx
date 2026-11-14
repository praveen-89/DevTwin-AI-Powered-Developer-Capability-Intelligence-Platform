/**
 * DevTwin — (app) Route Group Layout
 *
 * Server Component shell for every authenticated route (dashboard,
 * repositories, capabilities, coderisk, skillgraph, evidence). The actual
 * auth gate lives in `AppAuthGuard` (src/components/layout/app-auth-guard.tsx),
 * a client component — Next's route segment config below is only
 * recognized in a Server Component module, so it is declared here rather
 * than in the client guard itself.
 *
 * `instant = false`: this route group's rendering is gated on client-side
 * auth state (Supabase session restoration via useAuth()), which cannot be
 * resolved at build/prerender time. That makes every route under (app)
 * inherently dynamic, so it can never produce a deterministic static
 * "instant" navigation shell — opting out here (once, for the whole group)
 * avoids Next's Cache Components validation warning ("Could not validate
 * that a segment in your UI has instant navigation... Dropped segment")
 * that would otherwise fire per-page in dev.
 */

import { AppAuthGuard } from "@/components/layout/app-auth-guard";

export const instant = false;

export default function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return <AppAuthGuard>{children}</AppAuthGuard>;
}
