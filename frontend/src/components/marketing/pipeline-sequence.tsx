"use client";

/**
 * DevTwin Marketing — Animated Pipeline Sequence
 *
 * Renders the actual analysis pipeline (not a generic "3 easy steps" SaaS
 * graphic) as a sequence of stages. A highlight indicator advances through
 * the stages automatically using a shared `layoutId`, and the active
 * stage's detail crossfades in via `AnimatePresence`.
 *
 * When the visitor has `prefers-reduced-motion` set, auto-advancing stops
 * and the highlight/detail swap is instantaneous (no layout animation),
 * per Motion's `useReducedMotion`.
 */

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";
import type { LucideIcon } from "lucide-react";

export interface PipelineStage {
  icon: LucideIcon;
  label: string;
  description: string;
}

const STEP_INTERVAL_MS = 3200;

export function PipelineSequence({ stages }: { stages: PipelineStage[] }) {
  const reduceMotion = useReducedMotion();
  const [active, setActive] = useState(0);

  useEffect(() => {
    if (reduceMotion) return;
    const timer = window.setInterval(() => {
      setActive((i) => (i + 1) % stages.length);
    }, STEP_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [reduceMotion, stages.length]);

  return (
    <div className="space-y-8">
      {/* Stage rail */}
      <div
        className="flex flex-col gap-3 md:flex-row md:items-stretch md:gap-2"
        role="list"
        aria-label="DevTwin analysis pipeline stages"
      >
        {stages.map((stage, i) => {
          const Icon = stage.icon;
          const isActive = i === active;
          return (
            <button
              key={stage.label}
              type="button"
              role="listitem"
              onClick={() => setActive(i)}
              aria-current={isActive ? "step" : undefined}
              className={cn(
                "group relative flex flex-1 items-center gap-2.5 rounded-lg border px-3 py-3 text-left transition-colors",
                "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60",
                isActive
                  ? "border-cyan-500/40 bg-cyan-500/10"
                  : "border-slate-800 bg-slate-900/40 hover:border-slate-700"
              )}
            >
              {isActive && (
                <motion.div
                  layoutId="pipeline-highlight"
                  className="pointer-events-none absolute inset-0 rounded-lg border border-cyan-400/50"
                  transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 300, damping: 30 }}
                />
              )}
              <Icon
                className={cn(
                  "h-4 w-4 flex-shrink-0 relative z-10",
                  isActive ? "text-cyan-400" : "text-slate-500 group-hover:text-slate-300"
                )}
                aria-hidden="true"
              />
              <span
                className={cn(
                  "relative z-10 text-xs font-semibold tracking-tight",
                  isActive ? "text-cyan-300" : "text-slate-400"
                )}
              >
                {stage.label}
              </span>
            </button>
          );
        })}
      </div>

      {/* Active stage detail */}
      <div className="min-h-[72px] rounded-lg border border-slate-800 bg-slate-900/30 p-5">
        <AnimatePresence mode="wait">
          <motion.p
            key={active}
            initial={reduceMotion ? false : { opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduceMotion ? {} : { opacity: 0, y: -4 }}
            transition={{ duration: reduceMotion ? 0 : 0.25 }}
            className="text-sm leading-relaxed text-slate-300"
          >
            <span className="font-semibold text-slate-100">{stages[active].label}: </span>
            {stages[active].description}
          </motion.p>
        </AnimatePresence>
      </div>
    </div>
  );
}
