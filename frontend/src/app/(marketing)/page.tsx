import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/marketing/reveal";
import { LandingPipeline } from "@/components/marketing/landing-pipeline";
import { HeroEntrance } from "@/components/marketing/hero-entrance";
import { GlassCard } from "@/components/marketing/glass-card";
import {
  GraphIllustration,
  EvidenceStackIllustration,
  RadarScoreIllustration,
} from "@/components/marketing/illustrations";
import { LandingBannerVisual } from "@/components/layout/page-banner-illustrations";
import { Code2, FileSearch, GitBranch, ShieldQuestion } from "lucide-react";

export const metadata: Metadata = {
  title: "DevTwin — Evidence-Backed Developer Capability Intelligence",
  description:
    "DevTwin maintains an evolving representation of a developer's technical capabilities, engineering behaviors, and skill gaps based on verifiable repository evidence.",
};

export default function LandingPage() {
  return (
    <div>
      {/* Hero */}
      <section className="relative overflow-hidden px-3 pt-2 pb-8 sm:px-4 sm:pt-3 md:px-6 md:pt-3.5 md:pb-12">
        {/* Ambient glow + grid, light/dark aware */}
        <div className="pointer-events-none absolute inset-0 -z-10">
          <div className="absolute left-1/2 top-[-10%] h-[460px] w-[900px] -translate-x-1/2 rounded-full bg-cyan-400/15 blur-3xl dark:bg-cyan-500/10" />
          <div className="tech-grid absolute inset-0 opacity-[0.4] dark:opacity-100" />
        </div>

        <HeroEntrance>
          {/* Extended landscape container stretching left and right */}
          <div className="mx-auto w-full max-w-[1440px]">
            {/* Unified Landscape Hero Section Card - fully fits within viewport */}
            <div className="relative overflow-hidden rounded-2xl sm:rounded-3xl border border-slate-200 bg-gradient-to-b from-white via-slate-50/90 to-slate-100/70 p-4 sm:p-5 md:p-6 lg:px-10 lg:py-7 text-center shadow-sm transition-all duration-200 dark:border-slate-800 dark:bg-gradient-to-b dark:from-[#0f172a] dark:via-[#090d16] dark:to-[#0b1120] dark:shadow-none">
              
              {/* 1. First: "Developer Capability Intelligence" badge */}
              <div className="flex justify-center">
                <span className="inline-flex items-center gap-1.5 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3 py-0.5 text-[11px] font-semibold text-cyan-800 dark:text-cyan-300">
                  <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" aria-hidden="true" />
                  Developer Capability Intelligence
                </span>
              </div>

              {/* 2. After this: Generated image (seamless inside main hero card) */}
              <div className="mt-2 sm:mt-3 w-full">
                <LandingBannerVisual className="h-auto w-full" />
                <p className="mt-1 text-center text-[10px] sm:text-[11px] font-bold uppercase tracking-wider text-slate-600 dark:text-slate-400">
                  Continuous Intelligence Loop · Know · Build · Detect · Score · Improve · Re-Eval
                </p>
              </div>

              {/* 3. After this: "An evolving, evidence-backed picture of what you actually build." */}
              <h1 className="mx-auto mt-4 max-w-4xl text-xl font-extrabold tracking-tight text-slate-900 sm:text-2xl md:text-3xl lg:text-[34px] dark:text-slate-100 leading-snug">
                An evolving, evidence-backed picture of what you actually build.
              </h1>

              <p className="mx-auto mt-2 max-w-3xl text-xs sm:text-sm font-medium leading-relaxed text-slate-700 dark:text-slate-300">
                DevTwin maintains an evolving representation of a developer&apos;s
                technical capabilities, engineering behaviors, and skill gaps —
                based on verifiable evidence pulled from your own repositories,
                not a resume or a quiz.
              </p>

              {/* 4. Below this: The buttons */}
              <div className="mt-4 sm:mt-5 flex flex-wrap items-center justify-center gap-3">
                <Link href="/signup">
                  <Button variant="primary" size="md" leftIcon={<GitBranch className="h-4 w-4" />}>
                    Connect with GitHub
                  </Button>
                </Link>
                <Link href="/how-it-works">
                  <Button variant="outline" size="md">
                    See how it works
                  </Button>
                </Link>
              </div>

            </div>
          </div>
        </HeroEntrance>
      </section>

      {/* Problem */}
      <section className="px-5 py-16 md:px-8">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl dark:text-slate-100">
              Resumes and GitHub stats don&apos;t show how you build.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 max-w-3xl text-base leading-relaxed text-slate-700 dark:text-slate-300">
              Current methods for evaluating developer capability rely on static
              resumes, generic GitHub dashboards, or isolated LeetCode-style
              assessments. These fail to capture the true, evolving nature of a
              developer&apos;s technical knowledge and practical application.
              There is a massive gap between <em>claiming</em> knowledge and
              demonstrating safe, maintainable engineering behavior — and
              existing tools fail to map codebase risks directly back to
              developer growth opportunities.
            </p>
          </Reveal>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            {[
              { icon: FileSearch, title: "Resumes & dashboards", body: "Self-reported claims or star/line counts — neither verifies how you actually build." },
              { icon: ShieldQuestion, title: "Isolated assessments", body: "Multiple-choice quizzes test recall, not safe, maintainable engineering behavior." },
              { icon: Code2, title: "Disconnected risk", body: "Code risk findings rarely feed back into what they imply about a developer's growth." },
            ].map((item, i) => (
              <Reveal key={item.title} delay={0.1 * (i + 1)}>
                <GlassCard className="h-full p-5 hover:border-cyan-500/30 hover:-translate-y-0.5 transition-transform">
                  <item.icon className="h-5 w-5 text-slate-500 dark:text-slate-400" aria-hidden="true" />
                  <h3 className="mt-3 text-sm font-semibold text-slate-800 dark:text-slate-200">{item.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{item.body}</p>
                </GlassCard>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="relative overflow-hidden border-y border-slate-200 bg-slate-50 px-5 py-16 md:px-8 dark:border-slate-800/60 dark:bg-[#0b1120]">
        <div className="pointer-events-none absolute inset-0 -z-10 tech-grid opacity-[0.35] dark:opacity-100" />
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl dark:text-slate-100">
              The actual pipeline, not three generic steps.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Every stage persists real artifacts — observations, evidence,
              capability snapshots — that the dashboard can trace back to.
            </p>
          </Reveal>
          <Reveal delay={0.15} className="mt-8">
            <GlassCard className="p-5 md:p-6">
              <LandingPipeline />
            </GlassCard>
          </Reveal>
          <Reveal delay={0.2} className="mt-6">
            <Link href="/how-it-works" className="text-sm font-medium text-cyan-600 hover:text-cyan-700 dark:text-cyan-400 dark:hover:text-cyan-300">
              Read the full breakdown of each stage →
            </Link>
          </Reveal>
        </div>
      </section>

      {/* What makes it different */}
      <section className="px-5 py-16 md:px-8">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 md:text-3xl dark:text-slate-100">
              What makes it different
            </h2>
          </Reveal>
          <div className="mt-8 grid gap-6 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
            <Reveal>
              <GlassCard className="flex items-center justify-center p-6">
                <RadarScoreIllustration className="h-auto w-48 text-cyan-600 dark:text-cyan-400" />
              </GlassCard>
            </Reveal>
            <div className="grid gap-4 sm:grid-cols-3">
              {[
                {
                  title: "Evidence-first",
                  body: "No capability score exists without a traceable observation behind it. Every number can be clicked through to its source.",
                },
                {
                  title: "Explainable",
                  body: "The dashboard distinguishes a low capability score from low confidence — those are not the same thing.",
                },
                {
                  title: "Uncertainty-aware",
                  body: "A risk finding is negative evidence about engineering behavior, not a verdict on competence. Confidence is modeled explicitly.",
                },
              ].map((item, i) => (
                <Reveal key={item.title} delay={0.1 * (i + 1)}>
                  <GlassCard className="h-full p-5">
                    <h3 className="text-sm font-semibold text-cyan-700 dark:text-cyan-300">{item.title}</h3>
                    <p className="mt-1.5 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{item.body}</p>
                  </GlassCard>
                </Reveal>
              ))}
            </div>
          </div>
          <Reveal delay={0.4}>
            <p className="mt-6 max-w-2xl text-xs text-slate-500 dark:text-slate-500">
              DevTwin does not claim to be the only platform that does this — it
              is a deterministic, evidence-backed foundation (currently scoped
              to GitHub OAuth + repository analysis) built as a final-year
              engineering project.
            </p>
          </Reveal>
        </div>
      </section>

      {/* Evidence visual break */}
      <section className="px-5 py-10 md:px-8">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <GlassCard className="grid gap-6 p-6 md:grid-cols-[1fr_1.4fr] md:items-center md:p-8">
              <EvidenceStackIllustration className="h-auto w-full max-w-[220px] mx-auto text-cyan-600 dark:text-cyan-400" />
              <div>
                <h3 className="text-lg font-semibold text-slate-900 dark:text-slate-100">
                  Every score traces back to its evidence
                </h3>
                <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">
                  Observations are weighted by strength, directness, and
                  reliability, then aggregated with diminishing returns and
                  time-decay — nothing is a single opaque number.
                </p>
              </div>
            </GlassCard>
          </Reveal>
        </div>
      </section>

      {/* CTA */}
      <section className="px-5 py-16 md:px-8">
        <Reveal>
          <div className="mx-auto max-w-3xl rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-cyan-500/10 to-transparent p-10 text-center backdrop-blur-sm">
            <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-slate-100">
              See your own evidence-backed capability profile.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-slate-600 dark:text-slate-400">
              Connect a GitHub repository and DevTwin will build a SkillGraph,
              surface CodeRisk findings, and score your capabilities — with
              every score traceable to its evidence.
            </p>
            <div className="mt-6 flex justify-center">
              <Link href="/signup">
                <Button variant="primary" size="lg" leftIcon={<GitBranch className="h-4 w-4" />}>
                  Connect with GitHub
                </Button>
              </Link>
            </div>
          </div>
        </Reveal>
      </section>
    </div>
  );
}
