import type { Metadata } from "next";
import { EvidenceView } from "@/components/evidence/evidence-view";

// See frontend/src/app/(app)/dashboard/page.tsx for why this is needed:
// content here is decided client-side by the auth guard, so this page can
// never produce a deterministic static shell.
export const instant = false;

export const metadata: Metadata = {
  title: "Evidence | DevTwin",
  description: "Raw evidence items extracted from repository analysis.",
};

export default function EvidencePage() {
  return <EvidenceView />;
}
