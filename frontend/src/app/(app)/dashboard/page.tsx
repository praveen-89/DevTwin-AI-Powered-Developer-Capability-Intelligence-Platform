import type { Metadata } from "next";
import { Shell, PageContainer } from "@/components/layout/shell";
import { OverviewView } from "@/components/overview/overview-view";

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
