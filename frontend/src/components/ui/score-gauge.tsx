"use client";

import { cn, formatScore } from "@/lib/utils";
import { motion, useReducedMotion } from "motion/react";
import { AnimatedNumber } from "@/components/ui/animated-number";

interface ScoreGaugeProps {
  /** 0.0 – 1.0 normalized score */
  score: number;
  /** 0.0 – 1.0 confidence */
  confidence: number;
  label: string;
  /** Optional sub-label (e.g. domain or target type) */
  sublabel?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
}

function getScoreColor(score: number): string {
  if (score >= 0.75) return "bg-emerald-400";
  if (score >= 0.5) return "bg-cyan-400";
  if (score >= 0.25) return "bg-amber-400";
  return "bg-slate-500";
}

function getConfidenceWidth(confidence: number): string {
  return `${Math.round(confidence * 100)}%`;
}

export function ScoreGauge({
  score,
  confidence,
  label,
  sublabel,
  size = "md",
  className,
}: ScoreGaugeProps) {
  const reduceMotion = useReducedMotion();
  const pct = Math.max(0, Math.min(1, score));
  const conf = Math.max(0, Math.min(1, confidence));
  const barColor = getScoreColor(pct);
  const scorePct = Math.round(pct * 100);

  return (
    <div className={cn("space-y-1.5", className)}>
      <div className="flex items-baseline justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p
            className={cn(
              "font-medium text-slate-200 truncate",
              size === "sm" && "text-xs",
              size === "md" && "text-sm",
              size === "lg" && "text-base"
            )}
          >
            {label}
          </p>
          {sublabel && (
            <p className="text-xs text-slate-500 truncate font-mono">{sublabel}</p>
          )}
        </div>
        {/* Score number tweens between values rather than snapping */}
        <AnimatedNumber
          value={pct}
          format={formatScore}
          className={cn(
            "flex-shrink-0 font-mono font-semibold tabular-nums",
            size === "sm" && "text-sm",
            size === "md" && "text-base",
            size === "lg" && "text-xl",
            pct >= 0.75
              ? "text-emerald-400"
              : pct >= 0.5
              ? "text-cyan-400"
              : pct >= 0.25
              ? "text-amber-400"
              : "text-slate-400"
          )}
        />
      </div>

      {/* Score bar */}
      <div
        className="h-1.5 w-full rounded-full bg-slate-800 overflow-hidden"
        role="progressbar"
        aria-valuenow={scorePct}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label={`Capability score: ${formatScore(pct)}`}
      >
        {reduceMotion ? (
          <div
            className={cn("h-full rounded-full", barColor)}
            style={{ width: `${scorePct}%` }}
          />
        ) : (
          <motion.div
            className={cn("h-full rounded-full", barColor)}
            initial={false}
            animate={{ width: `${scorePct}%` }}
            transition={{ duration: 0.6, ease: "easeOut" }}
          />
        )}
      </div>

      {/* Confidence indicator */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-0.5 bg-slate-800/80 rounded-full overflow-hidden">
          {reduceMotion ? (
            <div
              className="h-full bg-slate-600 rounded-full"
              style={{ width: getConfidenceWidth(conf) }}
              aria-hidden="true"
            />
          ) : (
            <motion.div
              className="h-full bg-slate-600 rounded-full"
              initial={false}
              animate={{ width: getConfidenceWidth(conf) }}
              transition={{ duration: 0.6, ease: "easeOut" }}
              aria-hidden="true"
            />
          )}
        </div>
        <AnimatedNumber
          value={conf}
          format={(v) => `${Math.round(v * 100)}% conf.`}
          className="text-xs text-slate-500 font-mono flex-shrink-0 tabular-nums"
        />
      </div>
    </div>
  );
}

/** Compact numeric score pill used in tables */
export function ScorePill({ score, className }: { score: number; className?: string }) {
  const pct = Math.max(0, Math.min(1, score));
  return (
    <span
      className={cn(
        "inline-block font-mono text-xs font-semibold tabular-nums",
        pct >= 0.75 ? "text-emerald-400" : pct >= 0.5 ? "text-cyan-400" : pct >= 0.25 ? "text-amber-400" : "text-slate-400",
        className
      )}
    >
      {formatScore(pct)}
    </span>
  );
}
