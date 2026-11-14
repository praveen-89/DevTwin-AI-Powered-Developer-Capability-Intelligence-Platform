import type { Metadata } from "next";
import { SkillGraphView } from "@/components/skillgraph/skillgraph-view";

// See frontend/src/app/(app)/dashboard/page.tsx for why this is needed:
// content here is decided client-side by the auth guard, so this page can
// never produce a deterministic static shell.
export const instant = false;

export const metadata: Metadata = {
  title: "SkillGraph | DevTwin",
  description: "Interactive taxonomy of skills, technologies, and concepts extracted from repository analysis.",
};

export default function SkillGraphPage() {
  return <SkillGraphView />;
}
