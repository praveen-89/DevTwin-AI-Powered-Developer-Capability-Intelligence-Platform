"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth-context";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { AuthModal } from "@/components/auth/auth-modal";
import { ThemeToggle } from "@/components/theme/theme-toggle";
import { GitBranch, LogIn, LogOut, User } from "lucide-react";

interface HeaderProps {
  pageTitle: string;
  className?: string;
}

export function Header({ pageTitle, className }: HeaderProps) {
  const { developer, user, isAuthenticated, loading, signOut } = useAuth();
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  return (
    <>
      <header
        className={cn(
          "flex items-center justify-between h-12 px-5 border-b transition-colors",
          "border-slate-200/80 bg-white/95 text-slate-800",
          "dark:border-slate-800/60 dark:bg-[#0b1120]/95 dark:text-slate-100 backdrop-blur-sm",
          className
        )}
      >
        {/* Page title */}
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-sm font-semibold text-slate-900 dark:text-slate-100 truncate">{pageTitle}</h1>
        </div>

        {/* Right controls */}
        <div className="flex items-center gap-2">
          {/* Theme switcher: Light / Dark / System */}
          <ThemeToggle />

          {loading ? (
            <div className="h-6 w-20 rounded-md bg-slate-200 dark:bg-slate-800 animate-pulse" aria-hidden="true" />
          ) : isAuthenticated ? (
            <>
              {/* Authenticated state */}
              <Badge variant="muted" className="hidden sm:flex gap-1.5 items-center">
                <User className="h-3 w-3" aria-hidden="true" />
                <span className="font-mono text-xs truncate max-w-[120px]">
                  {user?.email ?? `${developer?.id.slice(0, 8)}…`}
                </span>
              </Badge>
              <Button
                variant="ghost"
                size="sm"
                leftIcon={<LogOut className="h-3.5 w-3.5" />}
                onClick={signOut}
                aria-label="Sign out"
              >
                <span className="hidden sm:inline">Sign out</span>
              </Button>
            </>
          ) : (
            <>
              {/* Unauthenticated — open AuthModal */}
              <span className="text-xs text-slate-500 hidden sm:block">
                Sign in to connect
              </span>
              <Button
                variant="outline"
                size="sm"
                leftIcon={<LogIn className="h-3.5 w-3.5" />}
                onClick={() => setIsAuthModalOpen(true)}
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
              "flex items-center justify-center h-8 w-8 rounded-lg border",
              "border-slate-200 bg-slate-50 text-slate-600 hover:text-slate-900 hover:border-slate-300",
              "dark:border-slate-700/50 dark:bg-transparent dark:text-slate-400 dark:hover:text-slate-200 dark:hover:border-slate-600",
              "transition-all focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
            )}
            aria-label="GitHub"
          >
            <GitBranch className="h-3.5 w-3.5" aria-hidden="true" />
          </a>
        </div>
      </header>

      {/* Custom accessible authentication modal */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
      />
    </>
  );
}
