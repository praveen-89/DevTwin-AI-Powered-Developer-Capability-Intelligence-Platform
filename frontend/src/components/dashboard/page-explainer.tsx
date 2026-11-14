"use client";

import { useEffect, useState } from "react";
import { AnimatePresence, motion, useReducedMotion } from "motion/react";
import { ChevronDown, HelpCircle } from "lucide-react";
import { Card, CardBody } from "@/components/ui/card";

export interface GlossaryTerm {
  term: string;
  definition: string;
}

interface PageExplainerProps {
  /** Unique key for this page, used to remember expand/collapse state per page. */
  pageKey: string;
  /** 1-2 sentence plain-language summary of what this page shows and why it matters. */
  description: string;
  /** Every technical term/label/column visible on this page, defined in plain language. */
  terms: GlossaryTerm[];
  className?: string;
}

function readExpanded(pageKey: string): boolean {
  if (typeof window === "undefined") return true;
  try {
    const stored = window.localStorage.getItem(`devtwin_explainer_${pageKey}`);
    // First visit this session (no stored value) defaults to expanded.
    return stored === null ? true : stored === "1";
  } catch {
    return true;
  }
}

function persistExpanded(pageKey: string, expanded: boolean) {
  try {
    window.localStorage.setItem(`devtwin_explainer_${pageKey}`, expanded ? "1" : "0");
  } catch {
    // Storage unavailable — silently ignore, this is a per-viewer convenience only.
  }
}

export function PageExplainer({ pageKey, description, terms, className }: PageExplainerProps) {
  const reduceMotion = useReducedMotion();
  const [expanded, setExpanded] = useState(true);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setExpanded(readExpanded(pageKey));
    setHydrated(true);
  }, [pageKey]);

  function toggle() {
    const next = !expanded;
    setExpanded(next);
    persistExpanded(pageKey, next);
  }

  return (
    <Card className={className}>
      <button
        type="button"
        onClick={toggle}
        aria-expanded={expanded}
        className="flex w-full items-center justify-between gap-3 px-5 py-4 text-left"
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="rounded-lg bg-cyan-500/10 p-1.5 border border-cyan-500/20 flex-shrink-0">
            <HelpCircle className="h-4 w-4 text-cyan-400" aria-hidden="true" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold text-slate-100">What am I looking at?</p>
            {!expanded && (
              <p className="text-xs text-slate-500 truncate">{description}</p>
            )}
          </div>
        </div>
        <ChevronDown
          className={`h-4 w-4 text-slate-500 flex-shrink-0 transition-transform ${expanded ? "rotate-180" : ""}`}
          aria-hidden="true"
        />
      </button>

      <AnimatePresence initial={false}>
        {expanded && hydrated && (
          <motion.div
            initial={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={reduceMotion ? undefined : { height: 0, opacity: 0 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="overflow-hidden"
          >
            <CardBody className="pt-0 space-y-4">
              <p className="text-sm text-slate-400 leading-relaxed">{description}</p>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
                {terms.map((t) => (
                  <div
                    key={t.term}
                    className="rounded-lg border border-slate-800/60 bg-slate-900/40 px-3 py-2.5"
                  >
                    <p className="text-xs font-mono font-semibold text-cyan-400">{t.term}</p>
                    <p className="mt-1 text-xs text-slate-400 leading-relaxed">{t.definition}</p>
                  </div>
                ))}
              </div>
            </CardBody>
          </motion.div>
        )}
      </AnimatePresence>
    </Card>
  );
}
