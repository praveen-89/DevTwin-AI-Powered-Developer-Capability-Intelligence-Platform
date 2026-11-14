"use client";

/**
 * DevTwin — Theme Toggle
 *
 * A small three-way Light / Dark / System control used on the marketing
 * nav and the login page only. Renders a neutral placeholder
 * until mounted to avoid a hydration mismatch against the theme
 * `next-themes` resolves from `localStorage` / the OS preference.
 */

import { useEffect, useState } from "react";
import { useTheme } from "next-themes";
import { Monitor, Moon, Sun } from "lucide-react";
import { cn } from "@/lib/utils";

const OPTIONS = [
  { value: "light", label: "Light", icon: Sun },
  { value: "system", label: "System", icon: Monitor },
  { value: "dark", label: "Dark", icon: Moon },
] as const;

export function ThemeToggle({ className }: { className?: string }) {
  const { theme, setTheme } = useTheme();
  const [mounted, setMounted] = useState(false);

  useEffect(() => setMounted(true), []);

  return (
    <div
      className={cn(
        "inline-flex items-center gap-0.5 rounded-lg border border-slate-200 bg-slate-100/80 p-0.5 dark:border-slate-800 dark:bg-slate-900/60",
        className
      )}
      role="radiogroup"
      aria-label="Theme preference"
    >
      {OPTIONS.map((opt) => {
        const Icon = opt.icon;
        const isActive = mounted && theme === opt.value;
        return (
          <button
            key={opt.value}
            type="button"
            role="radio"
            aria-checked={isActive}
            aria-label={`${opt.label} theme`}
            title={`${opt.label} theme`}
            onClick={() => setTheme(opt.value)}
            className={cn(
              "flex h-6.5 w-6.5 items-center justify-center rounded-md transition-colors",
              "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-400",
              isActive
                ? "bg-white text-cyan-600 shadow-sm dark:bg-cyan-500/20 dark:text-cyan-300"
                : "text-slate-500 hover:text-slate-700 dark:text-slate-500 dark:hover:text-slate-300"
            )}
          >
            <Icon className="h-3.5 w-3.5" aria-hidden="true" />
          </button>
        );
      })}
    </div>
  );
}
