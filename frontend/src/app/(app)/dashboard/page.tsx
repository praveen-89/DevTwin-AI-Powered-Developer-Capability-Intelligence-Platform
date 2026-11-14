import type { Metadata } from "next";
import { Shell, PageContainer } from "@/components/layout/shell";
import { OverviewView } from "@/components/overview/overview-view";

// Instant-navigation validation is per-segment: the (app) layout's
// `instant = false` only exempts the layout boundary, not this page
// segment, which Next.js validates independently (the "Dropped segment:
// src/app/(app)/dashboard/page.tsx" warning). Content here is only ever
// decided client-side by the auth guard (AppAuthGuard, rendered from the
// layout), so this page can never produce a deterministic static shell
// either — opt it out explicitly too.
export const instant = false;

export const metadata: Metadata = {
  title: "Overview | DevTwin",
  description: "Developer capability intelligence overview: GitHub status, repository analysis, capability scores, and code risk summary.",
};

export default function OverviewPage() {
  return (
    <Shell pageTitle="Overview">
      <PageContainer>
        <OverviewView />
      </PageContainer>
    </Shell>
  );
}
