import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger" | "outline";
type ButtonSize = "sm" | "md" | "lg";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
}

const variantStyles: Record<ButtonVariant, string> = {
  primary:
    "bg-cyan-500 hover:bg-cyan-400 text-slate-950 font-semibold border-transparent focus-visible:ring-cyan-400",
  secondary:
    "bg-slate-100 hover:bg-slate-200 text-slate-800 border-slate-300/80 hover:border-slate-400 focus-visible:ring-slate-400 dark:bg-slate-700/60 dark:hover:bg-slate-700 dark:text-slate-200 dark:border-slate-600/50 dark:hover:border-slate-500",
  ghost:
    "bg-transparent hover:bg-slate-100 text-slate-600 hover:text-slate-900 border-transparent focus-visible:ring-slate-400 dark:hover:bg-slate-800/60 dark:text-slate-300 dark:hover:text-slate-100",
  danger:
    "bg-red-500/10 hover:bg-red-500/20 text-red-600 border-red-500/30 hover:border-red-500/50 focus-visible:ring-red-400 dark:bg-red-500/15 dark:hover:bg-red-500/25 dark:text-red-400 dark:hover:border-red-400/50",
  outline:
    "bg-transparent border-slate-300/80 text-slate-600 hover:border-cyan-500/60 hover:text-cyan-600 focus-visible:ring-cyan-400 dark:border-slate-600/50 dark:text-slate-300 dark:hover:text-cyan-400",
};

const sizeStyles: Record<ButtonSize, string> = {
  sm: "h-7 px-2.5 text-xs gap-1.5",
  md: "h-9 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-sm gap-2",
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  disabled,
  leftIcon,
  rightIcon,
  className,
  children,
  ...props
}: ButtonProps) {
  const isDisabled = disabled || loading;
  return (
    <button
      disabled={isDisabled}
      className={cn(
        "inline-flex items-center justify-center whitespace-nowrap",
        "rounded-lg border transition-all duration-150",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-[#090d16]",
        "disabled:opacity-50 disabled:pointer-events-none",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
      {...props}
    >
      {loading ? (
        <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
      ) : leftIcon ? (
        <span className="flex-shrink-0" aria-hidden="true">
          {leftIcon}
        </span>
      ) : null}
      {children}
      {rightIcon && !loading && (
        <span className="flex-shrink-0" aria-hidden="true">
          {rightIcon}
        </span>
      )}
    </button>
  );
}
