/**
 * DevTwin Marketing — Glassmorphic Card
 *
 * Shared translucent/backdrop-blur card treatment for feature and pipeline
 * stage cards across the marketing site and the auth pages. Scoped to
 * these surfaces only (not used by the dashboard).
 */

import { cn } from "@/lib/utils";

export function GlassCard({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border transition-all duration-150",
        // Crisp, high-contrast white in light theme without blurring artifacts; elegant dark slate in dark mode
        "border-slate-200 bg-white text-slate-800 shadow-sm shadow-slate-200/50",
        "dark:border-slate-800/80 dark:bg-slate-900/60 dark:text-slate-200 dark:shadow-black/20 dark:backdrop-blur-md",
        className
      )}
    >
      {children}
    </div>
  );
}
