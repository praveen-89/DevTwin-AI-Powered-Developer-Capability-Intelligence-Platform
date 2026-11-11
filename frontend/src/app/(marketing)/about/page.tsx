import type { Metadata } from "next";
import { Reveal } from "@/components/marketing/reveal";

export const metadata: Metadata = {
  title: "About | DevTwin",
  description: "Project context for DevTwin, an AI-powered Developer Capability Intelligence Platform.",
};

export default function AboutPage() {
  return (
    <div className="px-5 py-14 md:px-8 md:py-20">
      <div className="mx-auto max-w-2xl space-y-10">
        <Reveal>
          <h1 className="text-3xl font-bold tracking-tight text-slate-100 md:text-4xl">
            About DevTwin
          </h1>
        </Reveal>

        <Reveal delay={0.05}>
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
              Project context
            </h2>
            <p className="text-sm leading-relaxed text-slate-400">
              DevTwin is a final-year engineering project: a full-stack
              implementation of an AI-powered Developer Capability
              Intelligence Platform. It is built to answer a concrete
              question — can heterogeneous evidence extracted from GitHub
              activity and software repositories be transformed into an
              explainable, evidence-backed representation of a developer&apos;s
              technical capabilities and engineering characteristics?
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.1}>
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
              Mission
            </h2>
            <p className="text-sm leading-relaxed text-slate-400">
              To eliminate the guesswork in developer capability assessment by
              replacing static resumes and generic test scores with
              continuous, evidence-backed engineering intelligence.
            </p>
          </div>
        </Reveal>

        <Reveal delay={0.15}>
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
              What this project is not
            </h2>
            <ul className="list-disc space-y-1.5 pl-5 text-sm leading-relaxed text-slate-400">
              <li>A generic chatbot or ChatGPT clone.</li>
              <li>A generic Learning Management System.</li>
              <li>A resume parser or text analyzer.</li>
              <li>A generic GitHub statistics dashboard (counting stars or lines of code).</li>
              <li>A generic code reviewer or pull request summarizer.</li>
              <li>A multiple-choice skill assessment platform.</li>
              <li>An autonomous coding agent that writes code on a user&apos;s behalf.</li>
            </ul>
          </div>
        </Reveal>

        <Reveal delay={0.2}>
          <div className="space-y-3">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-cyan-400">
              Current scope
            </h2>
            <p className="text-sm leading-relaxed text-slate-400">
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
  );
}
