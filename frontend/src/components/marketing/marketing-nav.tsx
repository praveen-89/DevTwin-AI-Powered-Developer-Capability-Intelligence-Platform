"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { GitBranch, Menu, X } from "lucide-react";
import { useState } from "react";
import { Button } from "@/components/ui/button";

const LINKS = [
  { href: "/", label: "Home" },
  { href: "/how-it-works", label: "How it works" },
  { href: "/about", label: "About" },
];

export function MarketingNav() {
  const pathname = usePathname();
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800/60 bg-[#090d16]/85 backdrop-blur-md">
      <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-5 md:px-8">
        <Link href="/" className="flex items-center gap-2.5" aria-label="DevTwin home">
          <div className="h-7 w-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center">
            <GitBranch className="h-3.5 w-3.5 text-cyan-400" aria-hidden="true" />
          </div>
          <span className="text-sm font-bold text-slate-100 tracking-tight">DevTwin</span>
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
                    ? "text-cyan-400"
                    : "text-slate-400 hover:text-slate-200"
                )}
                aria-current={isActive ? "page" : undefined}
              >
                {link.label}
              </Link>
            );
          })}
        </nav>

        <div className="hidden items-center gap-2 md:flex">
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

        <button
          className="flex h-9 w-9 items-center justify-center rounded-lg text-slate-300 md:hidden"
          onClick={() => setMobileOpen((v) => !v)}
          aria-label={mobileOpen ? "Close menu" : "Open menu"}
          aria-expanded={mobileOpen}
        >
          {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>

      {mobileOpen && (
        <div className="border-t border-slate-800/60 bg-[#0b1120] px-5 py-4 md:hidden">
          <nav className="flex flex-col gap-1" aria-label="Marketing navigation (mobile)">
            {LINKS.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className="rounded-lg px-3 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800/60"
                onClick={() => setMobileOpen(false)}
              >
                {link.label}
              </Link>
            ))}
            <div className="mt-2 flex flex-col gap-2 border-t border-slate-800/60 pt-3">
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
