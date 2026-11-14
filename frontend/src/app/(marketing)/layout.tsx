import { MarketingNav } from "@/components/marketing/marketing-nav";
import { MarketingFooter } from "@/components/marketing/marketing-footer";

/**
 * Shared layout for the public marketing site (/, /how-it-works, /about).
 * Intentionally separate from the authenticated app's `Shell` — the
 * marketing site has no sidebar and shares no layout with the dashboard,
 * per the route-group split in src/app/(app)/layout.tsx.
 */
export default function MarketingLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen flex-col bg-white text-slate-900 dark:bg-[#090d16] dark:text-slate-100">
      <MarketingNav />
      <main className="flex-1">{children}</main>
      <MarketingFooter />
    </div>
  );
}
