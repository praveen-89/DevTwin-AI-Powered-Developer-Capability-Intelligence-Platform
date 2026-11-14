import type { Metadata } from "next";
import Link from "next/link";
import { Reveal } from "@/components/marketing/reveal";
import { Button } from "@/components/ui/button";
import { GlassCard } from "@/components/marketing/glass-card";
import { PipelineBannerVisual } from "@/components/layout/page-banner-illustrations";
import { StepCardStack } from "@/components/marketing/step-card-stack";
import { GitBranch } from "lucide-react";

export const metadata: Metadata = {
  title: "How It Works | DevTwin",
  description:
    "A plain-language walkthrough of DevTwin's analysis pipeline: GitHub integration, repository mining, SkillGraph, Evidence, the Capability Model, CodeRisk, and the dashboard.",
};

// Stage content (GitHub integration, mining, SkillGraph, Evidence,
// Capability Model, CodeRisk, Dashboard) now lives in
// step-card-stack.tsx's PIPELINE_STEPS — see that file's comment for why
// it couldn't stay here (Lucide icon refs crossing the Server/Client
// Component boundary breaks Next.js 16 RSC serialization).

export default function HowItWorksPage() {
  return (
    <div className="relative overflow-hidden px-3 pt-2 pb-8 sm:px-4 sm:pt-3 md:px-6 md:pt-3.5 md:pb-12">
      <div className="pointer-events-none absolute inset-0 -z-10 tech-grid opacity-[0.35] dark:opacity-100" />

      <div className="mx-auto w-full max-w-[1440px] space-y-8">
        {/* 1. Full-width Unified Landscape Hero Section Card */}
        <section className="relative overflow-hidden rounded-2xl sm:rounded-3xl border border-slate-200 bg-gradient-to-b from-white via-slate-50/90 to-slate-100/70 p-4 sm:p-5 md:p-6 lg:px-10 lg:py-7 text-center shadow-sm transition-all duration-200 dark:border-slate-800 dark:bg-gradient-to-b dark:from-[#0f172a] dark:via-[#090d16] dark:to-[#0b1120] dark:shadow-none">
          {/* 1. First: Badge */}
          <div className="flex justify-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3 py-0.5 text-[11px] font-semibold text-cyan-800 dark:text-cyan-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" aria-hidden="true" />
              8-Stage Deterministic Pipeline
            </span>
          </div>

          {/* 2. After this: Generated image (seamless inside main hero card) */}
          <div className="mt-2 sm:mt-3 w-full">
            <PipelineBannerVisual className="h-auto w-full" />
          </div>

          {/* 3. After this: Title */}
          <h1 className="mx-auto mt-4 max-w-4xl text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl md:text-3xl lg:text-[34px] dark:text-slate-100 leading-snug">
            How DevTwin turns a repository into a capability score
          </h1>

          <p className="mx-auto mt-2 max-w-3xl text-xs sm:text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">
            Seven deterministic stages, each persisting real artifacts you can trace back through — no step is a black box.
          </p>

          {/* 4. Below this: Buttons */}
          <div className="mt-4 sm:mt-5 flex flex-wrap items-center justify-center gap-3">
            <Link href="/login">
              <Button variant="primary" size="md" leftIcon={<GitBranch className="h-4 w-4" />}>
                Get Started
              </Button>
            </Link>
            <Link href="/dashboard">
              <Button variant="outline" size="md">
                View Live Dashboard
              </Button>
            </Link>
          </div>
        </section>

        {/* Pipeline Step Card Stack */}
        <div className="pt-2">
          <StepCardStack />
        </div>

        {/* Bottom CTA Card */}
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-xs dark:border-slate-800 dark:bg-slate-900/60">
          <p className="text-base font-semibold text-slate-800 dark:text-slate-200">
            Ready to see this run against your own repositories?
          </p>
          <div className="mt-4 flex justify-center">
            <Link href="/login">
              <Button variant="primary" size="md" leftIcon={<GitBranch className="h-4 w-4" />}>
                Get Started
              </Button>
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
}
