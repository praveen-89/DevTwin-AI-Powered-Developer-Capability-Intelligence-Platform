import { cn } from "@/lib/utils";
import { CheckCircle2, Circle, AlertCircle, Loader2 } from "lucide-react";
import type { AnalysisRunStatus } from "@/types/api";

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

function StagePill({ label, description, state, isLast }: StagePillProps) {
  return (
    <li className="flex-1 min-w-0">
      <div className="flex items-center gap-2">
        {/* Icon */}
        <span
          className={cn(
            "flex-shrink-0 flex h-6 w-6 items-center justify-center rounded-full border transition-all",
            state === "done" && "bg-emerald-500/20 border-emerald-500/50",
            state === "active" && "bg-cyan-500/20 border-cyan-500/60",
            state === "failed" && "bg-red-500/20 border-red-500/50",
            state === "pending" && "bg-slate-800 border-slate-700"
          )}
          aria-hidden="true"
        >
          {state === "done" && (
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
          )}
          {state === "active" && (
            <Loader2 className="h-3.5 w-3.5 text-cyan-400 animate-spin" />
          )}
          {state === "failed" && (
            <AlertCircle className="h-3.5 w-3.5 text-red-400" />
          )}
          {state === "pending" && (
            <Circle className="h-3 w-3 text-slate-600" />
          )}
        </span>

        {/* Connector line */}
        {!isLast && (
          <div
            className={cn(
              "flex-1 h-px",
              state === "done" ? "bg-emerald-500/40" : "bg-slate-800"
            )}
            aria-hidden="true"
          />
        )}
      </div>

      {/* Stage label */}
      <div className="mt-2 px-0.5">
        <p
          className={cn(
            "text-xs font-medium tracking-wide",
            state === "done" && "text-emerald-400",
            state === "active" && "text-cyan-400",
            state === "failed" && "text-red-400",
            state === "pending" && "text-slate-600"
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

interface StageStepperProps {
  currentStatus: AnalysisRunStatus;
  className?: string;
}

export function StageStepper({ currentStatus, className }: StageStepperProps) {
  const isFailed = currentStatus === "FAILED";
  const currentIdx = isFailed ? -1 : getStageIndex(currentStatus);

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
        <p className="mt-3 text-xs text-red-400 bg-red-500/8 border border-red-500/20 rounded-lg px-3 py-2">
          Analysis failed. Check the job details and retry.
        </p>
      )}
    </div>
  );
}
