import { cn } from "@/lib/utils";

type BadgeVariant =
  | "default"
  | "accent"
  | "success"
  | "warning"
  | "danger"
  | "info"
  | "muted"
  | "critical"
  | "high"
  | "medium"
  | "low";

interface BadgeProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: BadgeVariant;
  dot?: boolean;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: "bg-slate-500/15 text-slate-300 border-slate-500/30",
  accent: "bg-cyan-500/15 text-cyan-400 border-cyan-500/30",
  success: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  warning: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  danger: "bg-red-500/15 text-red-400 border-red-500/30",
  info: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  muted: "bg-slate-800/60 text-slate-400 border-slate-700/50",
  critical: "bg-red-500/15 text-red-400 border-red-500/30",
  high: "bg-orange-500/15 text-orange-400 border-orange-500/30",
  medium: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  low: "bg-blue-500/15 text-blue-400 border-blue-500/30",
};

const dotStyles: Record<BadgeVariant, string> = {
  default: "bg-slate-400",
  accent: "bg-cyan-400",
  success: "bg-emerald-400",
  warning: "bg-amber-400",
  danger: "bg-red-400",
  info: "bg-blue-400",
  muted: "bg-slate-500",
  critical: "bg-red-400",
  high: "bg-orange-400",
  medium: "bg-amber-400",
  low: "bg-blue-400",
};

export function Badge({
  variant = "default",
  dot = false,
  children,
  className,
  ...props
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5",
        "text-xs font-medium font-mono tracking-wide",
        variantStyles[variant],
        className
      )}
      {...props}
    >
      {dot && (
        <span
          className={cn("h-1.5 w-1.5 rounded-full flex-shrink-0", dotStyles[variant])}
          aria-hidden="true"
        />
      )}
      {children}
    </span>
  );
}

/** Convenience component: maps a severity string to a Badge */
export function SeverityBadge({
  severity,
  className,
}: {
  severity: string;
  className?: string;
}) {
  const normalized = severity.toUpperCase() as BadgeVariant;
  const variant = (["CRITICAL", "HIGH", "MEDIUM", "LOW"].includes(normalized)
    ? normalized.toLowerCase()
    : "muted") as BadgeVariant;
  return (
    <Badge variant={variant} dot className={className}>
      {severity}
    </Badge>
  );
}

/** Maps a confidence number (0–1) to an appropriate badge */
export function ConfidenceBadge({
  confidence,
  className,
}: {
  confidence: number;
  className?: string;
}) {
  if (confidence >= 0.75)
    return (
      <Badge variant="success" className={className}>
        High confidence
      </Badge>
    );
  if (confidence >= 0.4)
    return (
      <Badge variant="warning" className={className}>
        Moderate
      </Badge>
    );
  return (
    <Badge variant="accent" className={className}>
      Emerging
    </Badge>
  );
}

/** Maps an AnalysisRunStatus to an appropriate badge */
export function StatusBadge({
  status,
  className,
}: {
  status: string;
  className?: string;
}) {
  const map: Record<string, BadgeVariant> = {
    COMPLETED: "success",
    FAILED: "danger",
    PROCESSING: "accent",
    QUEUED: "muted",
    FETCHING: "accent",
    MINING: "accent",
    SKILL_GRAPH: "accent",
    CODE_RISK: "accent",
    CAPABILITY: "accent",
  };
  return (
    <Badge variant={map[status] ?? "muted"} dot className={className}>
      {status}
    </Badge>
  );
}
