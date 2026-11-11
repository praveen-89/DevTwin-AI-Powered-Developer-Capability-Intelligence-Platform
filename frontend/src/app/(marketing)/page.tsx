import type { Metadata } from "next";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Reveal } from "@/components/marketing/reveal";
import { LandingPipeline } from "@/components/marketing/landing-pipeline";
import { HeroEntrance } from "@/components/marketing/hero-entrance";
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
      <section className="relative overflow-hidden px-5 pt-16 pb-14 md:px-8 md:pt-24 md:pb-20">
        <HeroEntrance>
          <div className="mx-auto max-w-3xl text-center">
            <span className="inline-flex items-center rounded-full border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-medium text-cyan-300">
              Developer Capability Intelligence
            </span>
            <h1 className="mt-5 text-3xl font-bold tracking-tight text-slate-100 md:text-5xl">
              An evolving, evidence-backed picture of what you actually build.
            </h1>
            <p className="mx-auto mt-5 max-w-xl text-base leading-relaxed text-slate-400 md:text-lg">
              DevTwin maintains an evolving representation of a developer&apos;s
              technical capabilities, engineering behaviors, and skill gaps —
              based on verifiable evidence pulled from your own repositories,
              not a resume or a quiz.
            </p>
            <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
              <Link href="/signup">
                <Button variant="primary" size="lg" leftIcon={<GitBranch className="h-4 w-4" />}>
                  Connect with GitHub
                </Button>
              </Link>
              <Link href="/how-it-works">
                <Button variant="outline" size="lg">
                  See how it works
                </Button>
              </Link>
            </div>
          </div>
        </HeroEntrance>
      </section>

      {/* Problem */}
      <section className="px-5 py-16 md:px-8">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-slate-100 md:text-3xl">
              Resumes and GitHub stats don&apos;t show how you build.
            </h2>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="mt-4 max-w-3xl text-base leading-relaxed text-slate-400">
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
                <div className="h-full rounded-xl border border-slate-800 bg-[#0f172a] p-5">
                  <item.icon className="h-5 w-5 text-slate-500" aria-hidden="true" />
                  <h3 className="mt-3 text-sm font-semibold text-slate-200">{item.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-500">{item.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="border-y border-slate-800/60 bg-[#0b1120] px-5 py-16 md:px-8">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-slate-100 md:text-3xl">
              The actual pipeline, not three generic steps.
            </h2>
            <p className="mt-3 max-w-2xl text-sm leading-relaxed text-slate-400">
              Every stage persists real artifacts — observations, evidence,
              capability snapshots — that the dashboard can trace back to.
            </p>
          </Reveal>
          <Reveal delay={0.15} className="mt-8">
            <LandingPipeline />
          </Reveal>
          <Reveal delay={0.2} className="mt-6">
            <Link href="/how-it-works" className="text-sm font-medium text-cyan-400 hover:text-cyan-300">
              Read the full breakdown of each stage →
            </Link>
          </Reveal>
        </div>
      </section>

      {/* What makes it different */}
      <section className="px-5 py-16 md:px-8">
        <div className="mx-auto max-w-5xl">
          <Reveal>
            <h2 className="text-2xl font-bold tracking-tight text-slate-100 md:text-3xl">
              What makes it different
            </h2>
          </Reveal>
          <div className="mt-8 grid gap-4 sm:grid-cols-3">
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
                <div className="h-full rounded-xl border border-slate-800 bg-[#0f172a] p-5">
                  <h3 className="text-sm font-semibold text-cyan-300">{item.title}</h3>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-400">{item.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
          <Reveal delay={0.4}>
            <p className="mt-6 max-w-2xl text-xs text-slate-500">
              DevTwin does not claim to be the only platform that does this — it
              is a deterministic, evidence-backed foundation (currently scoped
              to GitHub OAuth + repository analysis) built as a final-year
              engineering project.
            </p>
          </Reveal>
        </div>
      </section>

      {/* CTA */}
      <section className="px-5 py-16 md:px-8">
        <Reveal>
          <div className="mx-auto max-w-3xl rounded-2xl border border-cyan-500/20 bg-gradient-to-b from-cyan-500/10 to-transparent p-10 text-center">
            <h2 className="text-2xl font-bold tracking-tight text-slate-100">
              See your own evidence-backed capability profile.
            </h2>
            <p className="mx-auto mt-3 max-w-xl text-sm leading-relaxed text-slate-400">
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
