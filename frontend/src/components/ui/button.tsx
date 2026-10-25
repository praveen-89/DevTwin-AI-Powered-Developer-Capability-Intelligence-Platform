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
    "bg-slate-700/60 hover:bg-slate-700 text-slate-200 border-slate-600/50 hover:border-slate-500 focus-visible:ring-slate-400",
  ghost:
    "bg-transparent hover:bg-slate-800/60 text-slate-300 border-transparent hover:text-slate-100 focus-visible:ring-slate-400",
  danger:
    "bg-red-500/15 hover:bg-red-500/25 text-red-400 border-red-500/30 hover:border-red-400/50 focus-visible:ring-red-400",
  outline:
    "bg-transparent border-slate-600/50 text-slate-300 hover:border-cyan-500/60 hover:text-cyan-400 focus-visible:ring-cyan-400",
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
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-[#090d16]",
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
