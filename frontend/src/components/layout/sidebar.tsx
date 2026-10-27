"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  Activity,
  BarChart3,
  Code2,
  GitBranch,
  LayoutDashboard,
  Network,
  Server,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

interface NavItem {
  href: string;
  label: string;
  icon: React.ElementType;
  /** Whether this route has data-backed functionality yet */
  functional: boolean;
}

const NAV_ITEMS: NavItem[] = [
  { href: "/", label: "Overview", icon: LayoutDashboard, functional: true },
  { href: "/repositories", label: "Repositories", icon: Server, functional: true },
  { href: "/capabilities", label: "Capabilities", icon: BarChart3, functional: true },
  { href: "/coderisk", label: "CodeRisk", icon: Code2, functional: true },
  { href: "/skillgraph", label: "SkillGraph", icon: Network, functional: true },
  { href: "/evidence", label: "Evidence", icon: Activity, functional: true },
];

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
}

function WordMark({ collapsed }: { collapsed: boolean }) {
  return (
    <div
      className={cn(
        "flex items-center gap-2.5 px-4 py-4 border-b border-slate-800/60",
        collapsed ? "justify-center" : "justify-between"
      )}
    >
      <div className="flex items-center gap-2.5">
        {/* Logo mark */}
        <div
          className="flex-shrink-0 h-7 w-7 rounded-lg bg-cyan-500/15 border border-cyan-500/30 flex items-center justify-center"
          aria-hidden="true"
        >
          <GitBranch className="h-3.5 w-3.5 text-cyan-400" />
        </div>
        {!collapsed && (
          <span className="text-sm font-bold text-slate-100 tracking-tight select-none">
            DevTwin
          </span>
        )}
      </div>
    </div>
  );
}

function NavLink({
  item,
  collapsed,
  isActive,
}: {
  item: NavItem;
  collapsed: boolean;
  isActive: boolean;
}) {
  const Icon = item.icon;
  return (
    <Link
      href={item.href}
      title={collapsed ? item.label : undefined}
      className={cn(
        "group flex items-center gap-3 px-3 py-2 rounded-lg transition-all duration-150",
        "text-sm font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60",
        collapsed && "justify-center px-2",
        isActive
          ? "bg-cyan-500/12 text-cyan-400 border border-cyan-500/25"
          : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-transparent"
      )}
      aria-current={isActive ? "page" : undefined}
    >
      <Icon
        className={cn(
          "flex-shrink-0 transition-colors",
          collapsed ? "h-4.5 w-4.5" : "h-4 w-4",
          isActive ? "text-cyan-400" : "text-slate-500 group-hover:text-slate-300"
        )}
        aria-hidden="true"
      />
      {!collapsed && <span className="truncate">{item.label}</span>}
    </Link>
  );
}

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname();

  return (
    <aside
      className={cn(
        "flex flex-col h-full bg-[#0b1120] border-r border-slate-800/60 transition-all duration-200",
        collapsed ? "w-14" : "w-56"
      )}
      aria-label="Main navigation"
    >
      <WordMark collapsed={collapsed} />

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto px-2 py-3 space-y-0.5">
        {NAV_ITEMS.map((item) => {
          const isActive =
            item.href === "/" ? pathname === "/" : Boolean(pathname?.startsWith(item.href));
          return (
            <NavLink key={item.href} item={item} collapsed={collapsed} isActive={isActive} />
          );
        })}
      </nav>

      {/* Collapse toggle */}
      <div className="border-t border-slate-800/60 px-2 py-2">
        <button
          onClick={onToggle}
          className={cn(
            "w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-xs text-slate-500",
            "hover:text-slate-300 hover:bg-slate-800/50 transition-all focus-visible:outline-none",
            "focus-visible:ring-2 focus-visible:ring-cyan-500/60",
            collapsed && "justify-center"
          )}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          title={collapsed ? "Expand" : "Collapse"}
        >
          {collapsed ? (
            <ChevronRight className="h-4 w-4" aria-hidden="true" />
          ) : (
            <>
              <ChevronLeft className="h-4 w-4" aria-hidden="true" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  );
}
