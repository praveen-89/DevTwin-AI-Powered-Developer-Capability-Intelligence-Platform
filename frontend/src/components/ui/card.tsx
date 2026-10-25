import { cn } from "@/lib/utils";

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
  accentBorder?: boolean;
}

export function Card({
  elevated = false,
  accentBorder = false,
  className,
  children,
  ...props
}: CardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border",
        elevated
          ? "bg-[#162036] border-slate-600/40"
          : "bg-[#0f172a] border-slate-800/60",
        accentBorder && "border-cyan-500/30",
        className
      )}
      {...props}
    >
      {children}
    </div>
  );
}

export type CardHeaderProps = React.HTMLAttributes<HTMLDivElement>;

export function CardHeader({ className, children, ...props }: CardHeaderProps) {
  return (
    <div
      className={cn("flex items-center justify-between px-5 py-4 border-b border-slate-800/60", className)}
      {...props}
    >
      {children}
    </div>
  );
}

interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  as?: "h1" | "h2" | "h3" | "h4";
}

export function CardTitle({
  as: Tag = "h3",
  className,
  children,
  ...props
}: CardTitleProps) {
  return (
    <Tag
      className={cn("text-sm font-semibold text-slate-100 tracking-tight", className)}
      {...props}
    >
      {children}
    </Tag>
  );
}

export type CardBodyProps = React.HTMLAttributes<HTMLDivElement>;

export function CardBody({ className, children, ...props }: CardBodyProps) {
  return (
    <div className={cn("px-5 py-4", className)} {...props}>
      {children}
    </div>
  );
}

export type CardFooterProps = React.HTMLAttributes<HTMLDivElement>;

export function CardFooter({ className, children, ...props }: CardFooterProps) {
  return (
    <div
      className={cn("px-5 py-3 border-t border-slate-800/60 bg-slate-900/30", className)}
      {...props}
    >
      {children}
    </div>
  );
}
