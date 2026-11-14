"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { GitBranch, Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";
import { ThemeToggle } from "@/components/theme/theme-toggle";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
];

export function MarketingNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-200/70 bg-white/80 backdrop-blur-md dark:border-slate-800/60 dark:bg-[#090d16]/85">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 md:px-8">
        <Link href="/" className="flex items-center gap-2.5" aria-label="DevTwin home">
          <div className="h-7 w-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
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
          <Link href="/signup">
            <Button variant="primary" size="sm">
              Connect with GitHub
            </Button>
          </Link>
        </div>

        <div className="flex items-center gap-2 md:hidden">
          <ThemeToggle />
          <button
            className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-600 dark:text-slate-300"
            onClick={() => setMobileOpen((v) => !v)}
            aria-label={mobileOpen ? "Close menu" : "Open menu"}
            aria-expanded={mobileOpen}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>
        </div>
      </div>

      {mobileOpen && (
        <div className="border-t border-slate-200/70 bg-white px-5 py-4 md:hidden dark:border-slate-800/60 dark:bg-[#0b1120]">
          <nav className="flex flex-col gap-1" aria-label="Marketing navigation (mobile)">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800/60"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-2 flex flex-col gap-2 border-t border-slate-200/70 pt-3 dark:border-slate-800/60">
              <Link href="/login" onClick={() => setMobileOpen(false)}>
                <Button variant="ghost" size="sm" className="w-full justify-center">
                  Sign in
                </Button>
              </Link>
              <Link href="/signup" onClick={() => setMobileOpen(false)}>
                <Button variant="primary" size="sm" className="w-full justify-center">
                  Connect with GitHub
                </Button>
              </Link>
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}
