import { cn } from "@/lib/utils";

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  /** Use "line" for text lines, "rect" for blocks, "circle" for avatars */
  shape?: "line" | "rect" | "circle";
}

export function Skeleton({ shape = "rect", className, ...props }: SkeletonProps) {
  return (
    <div
      role="status"
      aria-label="Loading…"
      className={cn(
        "animate-pulse bg-slate-800/70",
        shape === "line" && "h-4 rounded-md",
        shape === "rect" && "rounded-xl",
        shape === "circle" && "rounded-full",
        className
      )}
      {...props}
    />
  );
}

/** A pre-built skeleton for a card with a header and a few body lines */
export function CardSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="rounded-xl border border-slate-800/60 bg-[#0f172a] overflow-hidden">
      <div className="px-5 py-4 border-b border-slate-800/60 flex items-center gap-3">
        <Skeleton shape="circle" className="h-5 w-5" />
        <Skeleton shape="line" className="w-32" />
      </div>
      <div className="px-5 py-4 space-y-3">
        {Array.from({ length: lines }).map((_, i) => (
          <Skeleton
            key={i}
            shape="line"
            className={i === lines - 1 ? "w-2/3" : "w-full"}
          />
        ))}
      </div>
    </div>
  );
}

/** Inline text-line skeleton that flows within paragraphs */
export function LineSkeleton({ className }: { className?: string }) {
  return <Skeleton shape="line" className={cn("w-24 inline-block align-middle", className)} />;
}
