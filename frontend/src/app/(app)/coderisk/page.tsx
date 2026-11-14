import type { Metadata } from "next";
import { CodeRiskView } from "@/components/coderisk/coderisk-view";

// See frontend/src/app/(app)/dashboard/page.tsx for why this is needed:
// content here is decided client-side by the auth guard, so this page can
// never produce a deterministic static shell.
export const instant = false;

export const metadata: Metadata = {
  title: "CodeRisk | DevTwin",
  description: "Static risk findings extracted from repository analysis runs.",
};

export default function CodeRiskPage() {
  return <CodeRiskView />;
}
