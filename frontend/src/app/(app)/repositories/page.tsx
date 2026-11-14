import type { Metadata } from "next";
import { RepositoriesView } from "@/components/repositories/repositories-view";

// See frontend/src/app/(app)/dashboard/page.tsx for why this is needed:
// content here is decided client-side by the auth guard, so this page can
// never produce a deterministic static shell.
export const instant = false;

export const metadata: Metadata = {
  title: "Repositories | DevTwin",
  description: "Registered repositories and their analysis pipeline state.",
};

export default function RepositoriesPage() {
  return <RepositoriesView />;
}
