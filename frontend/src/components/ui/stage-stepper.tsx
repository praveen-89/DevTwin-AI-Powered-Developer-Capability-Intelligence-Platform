"use client";

/**
 * DevTwin — Analysis Pipeline Stage Stepper
 *
 * Visualizes real async pipeline state (the actual `AnalysisRunStatus`
 * enum from the backend — see `src/types/api.ts`). When a stage completes
 * and the next one becomes active, the icon morphs (via AnimatePresence)
 * rather than instantly swapping, and the connector line's fill color
 * transitions smoothly rather than snapping.
 *
 * Respects `prefers-reduced-motion`: when reduced motion is requested, this
 * renders the original static markup with no animation at all.
 */

import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, AlertCircle, Loader2 } from "lucide-react";
import type { AnalysisRunStatus } from "@/types/api";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";

const PIPELINE_STAGES: { status: AnalysisRunStatus; label: string; description: string }[] = [
  { status: "QUEUED", label: "Queued", description: "Job accepted and waiting for a worker" },
  { status: "FETCHING", label: "Fetching", description: "Cloning or updating the repository" },
  { status: "MINING", label: "Mining", description: "Extracting commits, files, and patterns" },
  { status: "SKILL_GRAPH", label: "Skill Graph", description: "Building skill and technology graph" },
  { status: "CODE_RISK", label: "CodeRisk", description: "Running static risk analysis" },
  { status: "CAPABILITY", label: "Capability", description: "Scoring developer capabilities" },
  { status: "COMPLETED", label: "Completed", description: "Analysis finished successfully" },
];

const STATUS_ORDER: AnalysisRunStatus[] = [
  "QUEUED",
  "FETCHING",
  "MINING",
  "SKILL_GRAPH",
  "CODE_RISK",
  "CAPABILITY",
  "COMPLETED",
];

function getStageIndex(status: AnalysisRunStatus): number {
  return STATUS_ORDER.indexOf(status);
}

interface StagePillProps {
  label: string;
  description: string;
  state: "done" | "active" | "pending" | "failed";
  isLast: boolean;
}

const ICON_BY_STATE: Record<StagePillProps["state"], React.ReactNode> = {
  done: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
  active: <Loader2 className="h-3.5 w-3.5 text-cyan-400 animate-spin" />,
  failed: <AlertCircle className="h-3.5 w-3.5 text-red-400" />,
  pending: <Circle className="h-3 w-3 text-slate-400 dark:text-slate-600" />,
};

function StagePillStatic({ label, description, state, isLast }: StagePillProps) {
  return (
    <li className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        <span
          className={cn(
            "flex-shrink-0 flex h-6 w-6 items-center justify-center rounded-full border transition-all",
            state === "done" && "bg-emerald-500/20 border-emerald-500/50",
            state === "active" && "bg-cyan-500/20 border-cyan-500/60",
            state === "failed" && "bg-red-500/20 border-red-500/50",
            state === "pending" && "bg-slate-100 border-slate-300 dark:bg-slate-800 dark:border-slate-700"
          )}
          aria-hidden="true"
        >
          {ICON_BY_STATE[state]}
        </span>

        {!isLast && (
          <div
            className={cn(
              "flex-1 h-px",
              state === "done" ? "bg-emerald-500/40" : "bg-slate-200 dark:bg-slate-800"
            )}
            aria-hidden="true"
          />
        )}
      </div>

      <div className="mt-2 px-0.5">
        <p
          className={cn(
            "text-xs font-medium tracking-wide",
            state === "done" && "text-emerald-600 dark:text-emerald-400",
            state === "active" && "text-cyan-600 dark:text-cyan-400",
            state === "failed" && "text-red-600 dark:text-red-400",
            state === "pending" && "text-slate-400 dark:text-slate-600"
          )}
        >
          {label}
        </p>
        <p className="text-xs text-slate-500 mt-0.5 hidden sm:block leading-tight">
          {description}
        </p>
      </div>
    </li>
  );
}

function StagePillAnimated({ label, description, state, isLast }: StagePillProps) {
  return (
    <li className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        {/* Icon — morphs via AnimatePresence rather than swapping instantly */}
        <motion.span
          layout
          className={cn(
            "relative flex-shrink-0 flex h-6 w-6 items-center justify-center rounded-full border overflow-hidden",
            state === "done" && "bg-emerald-500/20 border-emerald-500/50",
            state === "active" && "bg-cyan-500/20 border-cyan-500/60",
            state === "failed" && "bg-red-500/20 border-red-500/50",
            state === "pending" && "bg-slate-100 border-slate-300 dark:bg-slate-800 dark:border-slate-700"
          )}
          animate={{
            borderColor:
              state === "done"
                ? "rgba(16,185,129,0.5)"
                : state === "active"
                ? "rgba(6,182,212,0.6)"
                : state === "failed"
                ? "rgba(239,68,68,0.5)"
                : "rgba(51,65,85,1)",
          }}
          transition={{ duration: 0.35, ease: "easeOut" }}
          aria-hidden="true"
        >
          <AnimatePresence mode="wait" initial={false}>
            <motion.span
              key={state}
              initial={{ scale: 0.4, opacity: 0, rotate: -45 }}
              animate={{ scale: 1, opacity: 1, rotate: 0 }}
              exit={{ scale: 0.4, opacity: 0, rotate: 45 }}
              transition={{ duration: 0.25, ease: "easeOut" }}
              className="flex items-center justify-center"
            >
              {ICON_BY_STATE[state]}
            </motion.span>
          </AnimatePresence>
        </motion.span>

        {/* Connector line — fill color morphs smoothly as the stage completes */}
        {!isLast && (
          <motion.div
            className="flex-1 h-px"
            initial={false}
            animate={{
              backgroundColor: state === "done" ? "rgba(16,185,129,0.4)" : "rgba(30,41,59,1)",
            }}
            transition={{ duration: 0.4, ease: "easeOut" }}
            aria-hidden="true"
          />
        )}
      </div>

      <motion.div layout className="mt-2 px-0.5">
        <motion.p
          className="text-xs font-medium tracking-wide"
          initial={false}
          animate={{
            color:
              state === "done"
                ? "#34d399"
                : state === "active"
                ? "#22d3ee"
                : state === "failed"
                ? "#f87171"
                : "#475569",
          }}
          transition={{ duration: 0.35, ease: "easeOut" }}
        >
          {label}
        </motion.p>
        <p className="text-xs text-slate-500 mt-0.5 hidden sm:block leading-tight">
          {description}
        </p>
      </motion.div>
    </li>
  );
}

interface StageStepperProps {
  currentStatus: AnalysisRunStatus;
  className?: string;
}

export function StageStepper({ currentStatus, className }: StageStepperProps) {
  const reduceMotion = useReducedMotion();
  const isFailed = currentStatus === "FAILED";
  const currentIdx = isFailed ? -1 : getStageIndex(currentStatus);

  const StagePill = reduceMotion ? StagePillStatic : StagePillAnimated;

  return (
    <div className={cn("w-full", className)} aria-label="Analysis pipeline stages">
      <ol className="flex items-start gap-1" role="list">
        {PIPELINE_STAGES.map((stage, idx) => {
          let state: StagePillProps["state"];
          if (isFailed) {
            state = "failed";
          } else if (idx < currentIdx) {
            state = "done";
          } else if (idx === currentIdx) {
            state = currentStatus === "COMPLETED" ? "done" : "active";
          } else {
            state = "pending";
          }

          return (
            <StagePill
              key={stage.status}
              label={stage.label}
              description={stage.description}
              state={state}
              isLast={idx === PIPELINE_STAGES.length - 1}
            />
          );
        })}
      </ol>

      {isFailed && (
        <p className="mt-3 text-xs text-red-700 dark:text-red-400 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2">
          Analysis failed. Check the job details and retry.
        </p>
      )}
    </div>
  );
}
