import type { Metadata } from "next";
import { CapabilitiesView } from "@/components/capabilities/capabilities-view";

// See frontend/src/app/(app)/dashboard/page.tsx for why this is needed:
// content here is decided client-side by the auth guard, so this page can
// never produce a deterministic static shell.
export const instant = false;

export const metadata: Metadata = {
  title: "Capabilities | DevTwin",
  description: "Developer capability scores and temporal history derived from evidence.",
};

export default function CapabilitiesPage() {
  return <CapabilitiesView />;
}
