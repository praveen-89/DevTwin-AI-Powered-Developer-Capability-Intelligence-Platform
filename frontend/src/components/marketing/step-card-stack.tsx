"use client";

/**
 * DevTwin Marketing — Step Card Stack
 *
 * Renders the pipeline stages as an actual hand of playing cards: solid,
 * opaque card faces (not glassmorphic — a real card isn't see-through)
 * fanned out from a single pivot at the bottom, each with a corner index
 * (step number) and a big central icon standing in for a suit pip.
 * Tapping the front card deals it to the back of the stack and brings the
 * next stage's card to the front, in step order ("one on one"). Any
 * visible card in the fan can also be tapped directly to jump straight to
 * that stage, and Prev/Next controls + dots give a non-tap way to move
 * through the same sequence.
 *
 * Cards behind the front one are fully opaque (never faded/translucent)
 * so a covered card's content is hidden purely by being physically
 * stacked underneath, exactly like real cards — not by opacity blending.
 * Cards beyond the visible fan depth are opacity:0 (off, not dimmed) so
 * they don't bleed through either. All seven cards' full text content
 * stays in the DOM at all times (the fan is a pure transform via Motion's
 * `animate`, not conditional rendering); only the front card is exposed
 * to screen readers, with a live region announcing the current step.
 */

import { useState } from "react";
import { motion, useReducedMotion } from "motion/react";
import {
  Activity,
  BarChart3,
  ChevronLeft,
  ChevronRight,
  Code2,
  GitBranch,
  LayoutDashboard,
  Network,
  Server,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/utils";

export interface StepCardData {
  icon: LucideIcon;
  title: string;
  body: string[];
}

// Defined here, not in the (server) page component, because a Lucide icon
// is a function/component reference — passing it from a Server Component
// into this Client Component as a prop breaks Next.js 16's RSC
// serialization ("Functions cannot be passed directly to Client
// Components"). Same pitfall, same fix, as landing-pipeline.tsx.
export const PIPELINE_STEPS: StepCardData[] = [
  {
    icon: GitBranch,
    title: "1. GitHub Integration",
    body: [
      "You connect your GitHub account through GitHub's own OAuth and App installation flow and choose which repositories DevTwin may read.",
      "DevTwin never stores a plaintext GitHub access token — installation tokens are short-lived and scoped to what analysis actually needs.",
    ],
  },
  {
    icon: Server,
    title: "2. Repository Mining",
    body: [
      "A background worker safely streams the repository contents, skipping directories like .git, node_modules, and virtual environments.",
      "It detects languages, extracts dependency manifests (package.json, requirements.txt, Cargo.toml, …), and parses Python source with an AST to find classes, functions, and async usage.",
    ],
  },
  {
    icon: Network,
    title: "3. SkillGraph",
    body: [
      "Raw mining observations — a language used, a dependency declared, a construct written — are mapped onto a skill taxonomy of technologies and underlying concepts.",
      "Ungrounded packages (ones DevTwin doesn't yet have a taxonomy mapping for) are tracked rather than silently dropped, and duplicate observations are deduplicated before persistence.",
    ],
  },
  {
    icon: Activity,
    title: "4. Evidence",
    body: [
      "Observations alone aren't evidence. The evidence engine contextualizes each one with a strength (0–1), a directness and reliability weighting, and a polarity from -1 (negative) to +1 (positive).",
      "This is where a CodeRisk finding, like a hardcoded secret, becomes negative evidence for a specific capability (e.g. Security) rather than a blanket verdict.",
    ],
  },
  {
    icon: BarChart3,
    title: "5. Capability Model",
    body: [
      "Evidence for a given skill is aggregated with diminishing returns per additional item and a sigmoid non-linear saturation, so no single piece of evidence can dominate the score.",
      "Older evidence decays on a half-life, and every computed state is appended to an immutable capability history — nothing is overwritten.",
      "The UI explicitly separates a low capability score from low confidence; they are tracked as two different numbers, not conflated into one.",
    ],
  },
  {
    icon: Code2,
    title: "6. CodeRisk",
    body: [
      "A set of deterministic static-analysis rules — covering security, reliability, maintainability, and testing signals — scans mined code for risk findings.",
      "Per the Capability Model Principle (Risk ≠ Competence), a risk finding is processed as evidence about engineering behavior in context, weighed against positive evidence — not direct proof of incompetence.",
    ],
  },
  {
    icon: LayoutDashboard,
    title: "7. Dashboard",
    body: [
      "The dashboard surfaces GitHub connection status, repository analysis progress, capability scores with confidence, SkillGraph exploration, CodeRisk findings, and the underlying Evidence — each with click-through provenance back to its source.",
      "Nothing displayed is fabricated or estimated outside of what the pipeline actually computed and persisted.",
    ],
  },
];

// How many cards behind the front one are visibly fanned out before they're
// switched off entirely (still present in the DOM, just opacity: 0 — never
// faded/translucent, since a real card's face is always fully opaque).
const VISIBLE_FAN_DEPTH = 4;

function depthStyle(depth: number, reduceMotion: boolean | null) {
  if (depth === 0) {
    // Pulled forward and lifted, like a card drawn out of the hand to read.
    return { x: 0, y: -14, rotate: 0, scale: 1.04, opacity: 1 };
  }
  if (depth > VISIBLE_FAN_DEPTH) {
    return { x: 0, y: 0, rotate: 0, scale: 0.94, opacity: 0 };
  }
  if (reduceMotion) {
    // Keep the "stacked hand" read without spatial motion/rotation.
    return { x: 0, y: depth * 2, rotate: 0, scale: 1 - depth * 0.015, opacity: 1 };
  }
  const direction = depth % 2 === 0 ? 1 : -1;
  return {
    // Fanned from a pivot at the base of the card (transformOrigin below),
    // so rotation alone — plus a small arc offset — reads as a hand fan.
    x: direction * depth * 15,
    y: depth * 3,
    rotate: direction * (depth * 6 + 3),
    scale: 1 - depth * 0.03,
    opacity: 1,
  };
}

export function StepCardStack({ steps = PIPELINE_STEPS }: { steps?: StepCardData[] }) {
  const [index, setIndex] = useState(0);
  const reduceMotion = useReducedMotion();
  const total = steps.length;

  const goTo = (i: number) => setIndex(((i % total) + total) % total);
  const goNext = () => goTo(index + 1);
  const goPrev = () => goTo(index - 1);

  return (
    <div>
      <div className="relative mx-auto flex h-[26rem] max-w-2xl items-end justify-center sm:h-[28rem]">
        {steps.map((step, i) => {
          const depth = (i - index + total) % total;
          const isActive = depth === 0;
          const isInteractive = depth <= VISIBLE_FAN_DEPTH;
          const style = depthStyle(depth, reduceMotion);
          const Icon = step.icon;
          const stepNumber = i + 1;

          return (
            <motion.div
              key={step.title}
              className={cn(
                "absolute bottom-0 h-[24rem] w-56 sm:h-[26rem] sm:w-64",
                isInteractive ? "cursor-pointer" : "pointer-events-none"
              )}
              style={{ zIndex: total - depth, transformOrigin: "50% 100%" }}
              animate={style}
              transition={
                reduceMotion
                  ? { duration: 0.15 }
                  : { type: "spring", stiffness: 260, damping: 26 }
              }
              role="button"
              tabIndex={isInteractive ? 0 : -1}
              aria-hidden={!isActive}
              aria-label={isActive ? undefined : `Jump to step: ${step.title}`}
              onClick={() => (isActive ? goNext() : goTo(i))}
              onKeyDown={(e) => {
                if (!isInteractive) return;
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  isActive ? goNext() : goTo(i);
                }
              }}
            >
              {/* Real playing-card face: solid/opaque, never translucent. */}
              <div
                className={cn(
                  "relative flex h-full w-full flex-col rounded-2xl border-2 p-3.5 shadow-xl select-none sm:p-4",
                  "border-slate-300 bg-white shadow-slate-900/20",
                  "dark:border-slate-600 dark:bg-slate-800 dark:shadow-black/50",
                  isActive && "ring-2 ring-cyan-500/50"
                )}
              >
                {/* Top-left corner index */}
                <div className="flex flex-col items-center leading-none text-cyan-600 dark:text-cyan-400">
                  <span className="text-lg font-bold">{stepNumber}</span>
                  <Icon className="mt-0.5 h-3.5 w-3.5" aria-hidden="true" />
                </div>

                {/* Center "suit" icon + content */}
                <div className="flex flex-1 flex-col items-center gap-2 overflow-hidden px-1 pt-1 text-center">
                  <Icon className="h-10 w-10 flex-shrink-0 text-cyan-500/70 dark:text-cyan-400/70" aria-hidden="true" />
                  <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                    {step.title}
                  </h3>
                  <div className="w-full flex-1 space-y-1.5 overflow-y-auto">
                    {step.body.map((p, pi) => (
                      <p key={pi} className="text-[11px] leading-snug text-slate-600 dark:text-slate-400">
                        {p}
                      </p>
                    ))}
                  </div>
                </div>

                {/* Bottom-right corner index, mirrored like a real card */}
                <div className="flex rotate-180 flex-col items-center self-end leading-none text-cyan-600 dark:text-cyan-400">
                  <span className="text-lg font-bold">{stepNumber}</span>
                  <Icon className="mt-0.5 h-3.5 w-3.5" aria-hidden="true" />
                </div>
              </div>
            </motion.div>
          );
        })}
      </div>

      {/* Controls: prev/next + dots + live step counter */}
      <div className="mt-6 flex items-center justify-center gap-4">
        <button
          type="button"
          onClick={goPrev}
          aria-label="Previous step"
          className="rounded-full border border-slate-300/70 p-2 text-slate-500 transition-colors hover:border-cyan-500/50 hover:text-cyan-600 dark:border-slate-700 dark:text-slate-400 dark:hover:text-cyan-400"
        >
          <ChevronLeft className="h-4 w-4" aria-hidden="true" />
        </button>

        <div className="flex items-center gap-1.5" role="tablist" aria-label="Pipeline stages">
          {steps.map((step, i) => (
            <button
              key={step.title}
              type="button"
              role="tab"
              aria-selected={i === index}
              aria-label={`Go to step ${i + 1}: ${step.title}`}
              onClick={() => goTo(i)}
              className={cn(
                "h-1.5 rounded-full transition-all",
                i === index
                  ? "w-5 bg-cyan-500"
                  : "w-1.5 bg-slate-300 hover:bg-slate-400 dark:bg-slate-700 dark:hover:bg-slate-600"
              )}
            />
          ))}
        </div>

        <button
          type="button"
          onClick={goNext}
          aria-label="Next step"
          className="rounded-full border border-slate-300/70 p-2 text-slate-500 transition-colors hover:border-cyan-500/50 hover:text-cyan-600 dark:border-slate-700 dark:text-slate-400 dark:hover:text-cyan-400"
        >
          <ChevronRight className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>

      <p className="mt-3 text-center text-xs text-slate-500 dark:text-slate-500" aria-live="polite">
        Step {index + 1} of {total} — tap the card to deal the next one
      </p>
    </div>
  );
}
