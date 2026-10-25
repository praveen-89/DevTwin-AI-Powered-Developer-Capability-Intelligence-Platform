"use client";

import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { GitBranch, LogIn, LogOut, User } from "lucide-react";

interface HeaderProps {
  pageTitle: string;
  className?: string;
}

export function Header({ pageTitle, className }: HeaderProps) {
  const { developer, token, loading, clearToken, setToken } = useAuth();

  return (
    <header
      className={cn(
        "flex items-center justify-between h-12 px-5 border-b border-slate-800/60 bg-[#0b1120]/95 backdrop-blur-sm",
        className
      )}
    >
      {/* Page title */}
      <div className="flex items-center gap-3 min-w-0">
        <h1 className="text-sm font-semibold text-slate-100 truncate">{pageTitle}</h1>
      </div>

      {/* Right controls */}
      <div className="flex items-center gap-2">
        {loading ? (
          <div className="h-6 w-20 rounded-md bg-slate-800 animate-pulse" aria-hidden="true" />
        ) : token && developer ? (
          <>
            {/* Authenticated state */}
            <Badge variant="muted" className="hidden sm:flex gap-1.5 items-center">
              <User className="h-3 w-3" aria-hidden="true" />
              <span className="font-mono text-xs truncate max-w-[100px]">
                {developer.id.slice(0, 8)}…
              </span>
            </Badge>
            <Button
              variant="ghost"
              size="sm"
              leftIcon={<LogOut className="h-3.5 w-3.5" />}
              onClick={clearToken}
              aria-label="Sign out"
            >
              <span className="hidden sm:inline">Sign out</span>
            </Button>
          </>
        ) : (
          <>
            {/* Unauthenticated — dev-mode token entry */}
            <span className="text-xs text-slate-500 hidden sm:block">
              Set a token to connect
            </span>
            <Button
              variant="outline"
              size="sm"
              leftIcon={<LogIn className="h-3.5 w-3.5" />}
              onClick={() => {
                const t = prompt(
                  "Enter your DevTwin backend JWT (dev mode).\nLeave blank to cancel."
                );
                if (t?.trim()) setToken(t.trim());
              }}
            >
              Sign in
            </Button>
          </>
        )}

        {/* GitHub link */}
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className={cn(
            "flex items-center justify-center h-8 w-8 rounded-lg border border-slate-700/50",
            "text-slate-400 hover:text-slate-200 hover:border-slate-600",
            "transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
          )}
          aria-label="GitHub"
        >
          <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />
        </a>
      </div>
    </header>
  );
}
