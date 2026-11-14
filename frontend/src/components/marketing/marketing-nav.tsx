"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { GitBranch, Home, Compass, Info, LogIn } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme/theme-toggle";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
];

/** Mobile bottom tab bar items — nav links plus a sign-in shortcut, since
 *  there's no room on the top bar once the hamburger/dropdown is removed. */
const MOBILE_TABS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/how-it-works", label: "Guide", icon: Compass },
  { href: "/about", label: "About", icon: Info },
  { href: "/login", label: "Sign in", icon: LogIn },
];

export function MarketingNav() {
  const pathname = usePathname();

  return (
    <>
      <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-md dark:border-slate-800/60 dark:bg-[#090d16]/85">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4 sm:h-16 sm:px-5 md:px-8">
          <Link href="/" className="flex items-center gap-2 sm:gap-2.5" aria-label="DevTwin home">
            <div className="h-7 w-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
              <GitBranch className="h-3.5 w-3.5 text-cyan-600 dark:text-cyan-400" aria-hidden="true" />
            </div>
            <span className="text-sm font-bold tracking-tight text-slate-900 dark:text-slate-100">DevTwin</span>
          </Link>

          <nav className="hidden items-center gap-1 md:flex" aria-label="Marketing navigation">
            {LINKS.map((link) => {
              const isActive = pathname === link.href;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "text-cyan-600 dark:text-cyan-400"
                      : "text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-slate-200"
                  )}
                  aria-current={isActive ? "page" : undefined}
                >
                  {link.label}
                </Link>
              );
            })}
          </nav>

          <div className="hidden items-center gap-3 md:flex">
            <ThemeToggle />
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign in
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="primary" size="sm">
                Get Started
              </Button>
            </Link>
          </div>

          {/* Mobile: just the theme toggle + primary CTA — nav links live in
              the bottom tab bar instead of a hamburger dropdown. */}
          <div className="flex items-center gap-2 md:hidden">
            <ThemeToggle />
            <Link href="/login">
              <Button variant="primary" size="sm">
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Mobile bottom tab bar — fixed to the bottom of the viewport,
          standard mobile-app nav pattern. Hidden at md+ where the top nav
          takes over. */}
      <nav
        className={cn(
          "fixed inset-x-0 bottom-0 z-40 md:hidden",
          "border-t border-slate-200/80 bg-white/95 backdrop-blur-md",
          "dark:border-slate-800/60 dark:bg-[#0b1120]/95",
          "pb-[env(safe-area-inset-bottom)]"
        )}
        aria-label="Mobile navigation"
      >
        <div className="grid grid-cols-4">
          {MOBILE_TABS.map((tab) => {
            const isActive = pathname === tab.href;
            const Icon = tab.icon;
            return (
              <Link
                key={tab.href}
                href={tab.href}
                className={cn(
                  "flex flex-col items-center justify-center gap-1 py-2.5 text-[11px] font-medium transition-colors",
                  "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 focus-visible:ring-inset",
                  isActive
                    ? "text-cyan-600 dark:text-cyan-400"
                    : "text-slate-500 dark:text-slate-400"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                <Icon className="h-5 w-5" aria-hidden="true" />
                <span>{tab.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
