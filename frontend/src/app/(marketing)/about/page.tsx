import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/marketing/reveal";
import { GlassCard } from "@/components/marketing/glass-card";
import { AboutBannerVisual } from "@/components/layout/page-banner-illustrations";
import { GitBranch, Compass, Info } from "lucide-react";

export const metadata: Metadata = {
  title: "About | DevTwin",
  description: "Project context for DevTwin, an AI-powered Developer Capability Intelligence Platform.",
};

export default function AboutPage() {
  return (
    <div className="relative overflow-hidden px-3 pt-2 pb-8 sm:px-4 sm:pt-3 md:px-6 md:pt-3.5 md:pb-12">
      {/* Background ambient lighting */}
      <div className="pointer-events-none absolute inset-0 -z-10">
        <div className="absolute right-[-10%] top-10 h-[420px] w-[420px] rounded-full bg-cyan-400/10 blur-3xl dark:bg-cyan-500/10" />
        <div className="tech-grid absolute inset-0 opacity-[0.4] dark:opacity-100" />
      </div>

      <div className="mx-auto w-full max-w-[1440px] space-y-8">
        {/* 1. Full-width Unified Landscape Hero Section Card */}
        <section className="relative overflow-hidden rounded-2xl sm:rounded-3xl border border-slate-200 bg-gradient-to-b from-white via-slate-50/90 to-slate-100/70 p-4 sm:p-5 md:p-6 lg:px-10 lg:py-7 text-center shadow-sm transition-all duration-200 dark:border-slate-800 dark:bg-gradient-to-b dark:from-[#0f172a] dark:via-[#090d16] dark:to-[#0b1120] dark:shadow-none">
          {/* 1. First: Badge */}
          <div className="flex justify-center">
            <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3 py-0.5 text-[11px] font-semibold text-cyan-800 dark:text-cyan-300">
              <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" aria-hidden="true" />
              Project Background & Architecture
            </span>
          </div>

          {/* 2. After this: Generated image (seamless inside main hero card) */}
          <div className="mt-2 sm:mt-3 w-full">
            <AboutBannerVisual className="h-auto w-full" />
            <p className="mt-1 text-center text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
              Evidence-Backed Ground Truth vs Unverified Claims
            </p>
          </div>

          {/* 3. After this: Title */}
          <h1 className="mx-auto mt-4 max-w-4xl text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl md:text-3xl lg:text-[34px] dark:text-slate-100 leading-snug">
            About DevTwin
          </h1>

          <p className="mx-auto mt-2 max-w-3xl text-xs sm:text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">
            An engineering intelligence platform designed to replace unverified resumes with verifiable repository telemetry and capability models.
          </p>

          {/* 4. Below this: Buttons */}
          <div className="mt-4 sm:mt-5 flex flex-wrap items-center justify-center gap-3">
            <Link href="/login">
              <Button variant="primary" size="md" leftIcon={<GitBranch className="h-4 w-4" />}>
                Get Started
              </Button>
            </Link>
            <Link href="/how-it-works">
              <Button variant="outline" size="md" leftIcon={<Compass className="h-4 w-4" />}>
                See How It Works
              </Button>
            </Link>
          </div>
        </section>

        {/* 2. Content written AFTER the Hero Section in clear, high-contrast sections */}
        <div className="space-y-8">
          <Reveal>
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900/60">
              <div className="flex items-start gap-3">
                <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-cyan-500/15 text-cyan-700 dark:bg-cyan-500/25 dark:text-cyan-400">
                  <Info className="h-4 w-4" />
                </div>
                <div>
                  <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-700 dark:text-cyan-400">
                    Project Context
                  </h2>
                  <p className="mt-2 text-base font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                    DevTwin is a final-year engineering project: a full-stack
                    implementation of an AI-powered Developer Capability
                    Intelligence Platform. It is built to answer a concrete
                    question — can heterogeneous evidence extracted from GitHub
                    activity and software repositories be transformed into an
                    explainable, evidence-backed representation of a developer&apos;s
                    technical capabilities and engineering characteristics?
                  </p>
                </div>
              </div>
            </div>
          </Reveal>

          <Reveal delay={0.05}>
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900/60">
              <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-700 dark:text-cyan-400">
                Mission
              </h2>
              <p className="mt-2 text-base font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                To eliminate the guesswork in developer capability assessment by
                replacing static resumes and generic test scores with
                continuous, evidence-backed engineering intelligence.
              </p>
            </div>
          </Reveal>

          <Reveal delay={0.1}>
            <GlassCard className="p-6">
              <h2 className="text-xs font-bold uppercase tracking-wider text-rose-600 dark:text-rose-400">
                What this project is not
              </h2>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                <li>A generic chatbot or ChatGPT clone.</li>
                <li>A generic Learning Management System.</li>
                <li>A resume parser or text analyzer.</li>
                <li>A generic GitHub statistics dashboard (counting stars or lines of code).</li>
                <li>A generic code reviewer or pull request summarizer.</li>
                <li>A multiple-choice skill assessment platform.</li>
                <li>An autonomous coding agent that writes code on a user&apos;s behalf.</li>
              </ul>
            </GlassCard>
          </Reveal>

          <Reveal delay={0.15}>
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs dark:border-slate-800 dark:bg-slate-900/60">
              <h2 className="text-xs font-bold uppercase tracking-wider text-cyan-700 dark:text-cyan-400">
                Current Scope
              </h2>
              <p className="mt-2 text-base font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                The current (Minor-project) scope covers GitHub OAuth +
                repository selection, through repository mining, SkillGraph and
                CodeRisk analysis, the evidence engine, and the capability
                model, surfaced on an interactive dashboard. A future, larger
                scope (&quot;StudyTwin&quot;) is intended to close the loop with
                personalized learning, knowledge tracing, and outcome
                measurement — that part is not implemented yet.
              </p>
            </div>
          </Reveal>
        </div>
      </div>
    </div>
  );
}
