import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";
import { AlertCircle, Database, FolderOpen, GitBranch, Inbox } from "lucide-react";

type EmptyStateVariant = "default" | "error" | "no-data" | "no-repos" | "no-github";

const presets: Record<
  EmptyStateVariant,
  { icon: LucideIcon; title: string; description: string }
> = {
  default: {
    icon: Inbox,
    title: "Nothing here yet",
    description: "There is no data to display for this section.",
  },
  error: {
    icon: AlertCircle,
    title: "Failed to load data",
    description:
      "The request could not be completed. Check that the backend is running and your session is valid.",
  },
  "no-data": {
    icon: Database,
    title: "No analysis data",
    description:
      "No analysis results are available for the selected repository and run.",
  },
  "no-repos": {
    icon: FolderOpen,
    title: "No repositories",
    description:
      "Connect GitHub and register a repository to start an analysis.",
  },
  "no-github": {
    icon: GitBranch,
    title: "GitHub not connected",
    description:
      "Connect your GitHub account to let DevTwin analyse your repositories.",
  },
};

interface EmptyStateProps {
  variant?: EmptyStateVariant;
  title?: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
  /** Override the preset icon */
  icon?: LucideIcon;
}

export function EmptyState({
  variant = "default",
  title,
  description,
  action,
  className,
  icon: IconOverride,
}: EmptyStateProps) {
  const preset = presets[variant];
  const Icon = IconOverride ?? preset.icon;
  const displayTitle = title ?? preset.title;
  const displayDesc = description ?? preset.description;

  return (
    <div
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 text-center",
        className
      )}
      role="status"
    >
      <div className="rounded-full bg-slate-800/60 border border-slate-700/50 p-4 mb-5">
        <Icon className="h-6 w-6 text-slate-400" aria-hidden="true" />
      </div>
      <h3 className="text-sm font-semibold text-slate-200 mb-1.5">{displayTitle}</h3>
      <p className="text-sm text-slate-400 max-w-xs leading-relaxed">{displayDesc}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

/** Inline error state for within a card */
export function InlineError({ message, className }: { message: string; className?: string }) {
  return (
    <div
      className={cn(
        "flex items-start gap-3 rounded-lg border border-red-500/20 bg-red-500/8 px-4 py-3",
        className
      )}
      role="alert"
    >
      <AlertCircle className="h-4 w-4 text-red-400 flex-shrink-0 mt-0.5" aria-hidden="true" />
      <p className="text-sm text-red-300">{message}</p>
    </div>
  );
}
