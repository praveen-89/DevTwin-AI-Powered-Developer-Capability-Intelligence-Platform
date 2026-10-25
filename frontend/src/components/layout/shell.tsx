"use client";

import { useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { cn } from "@/lib/utils";

interface ShellProps {
  pageTitle: string;
  children: React.ReactNode;
  className?: string;
}

export function Shell({ pageTitle, children, className }: ShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  return (
    <div className="flex h-screen w-full overflow-hidden bg-[#090d16]">
      {/* Sidebar */}
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed((v) => !v)}
      />

      {/* Main content area */}
      <div className="flex flex-col flex-1 min-w-0 overflow-hidden">
        <Header pageTitle={pageTitle} />

        {/* Scrollable page content */}
        <main
          className={cn(
            "flex-1 overflow-y-auto overflow-x-hidden",
            "px-5 py-6 md:px-8 md:py-8",
            className
          )}
          id="main-content"
        >
          {children}
        </main>
      </div>
    </div>
  );
}

/** A standard page container with max-width */
export function PageContainer({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("mx-auto w-full max-w-6xl space-y-6", className)}>
      {children}
    </div>
  );
}

/** Standard page header with title, description, and optional actions */
export function PageHeading({
  title,
  description,
  actions,
  className,
}: {
  title: string;
  description?: string;
  actions?: React.ReactNode;
  className?: string;
}) {
  return (
    <div className={cn("flex items-start justify-between gap-4", className)}>
      <div className="space-y-1">
        <h2 className="text-lg font-bold text-slate-100 tracking-tight">{title}</h2>
        {description && (
          <p className="text-sm text-slate-400 leading-relaxed max-w-xl">{description}</p>
        )}
      </div>
      {actions && (
        <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>
      )}
    </div>
  );
}
