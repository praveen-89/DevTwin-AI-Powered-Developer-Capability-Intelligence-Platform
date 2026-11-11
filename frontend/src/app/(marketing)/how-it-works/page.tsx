import type { Metadata } from "next";
import Link from "next/link";
import { Reveal } from "@/components/marketing/reveal";
import { Button } from "@/components/ui/button";
import {
  Activity,
  BarChart3,
  Code2,
  GitBranch,
  LayoutDashboard,
  Network,
  Server,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

export const metadata: Metadata = {
  title: "How It Works | DevTwin",
  description:
    "A plain-language walkthrough of DevTwin's analysis pipeline: GitHub integration, repository mining, SkillGraph, Evidence, the Capability Model, CodeRisk, and the dashboard.",
};

interface Stage {
  icon: LucideIcon;
  title: string;
  body: string[];
}

// Order matches the task brief's expanded breakdown: GitHub integration,
// mining, SkillGraph, Evidence, Capability Model, CodeRisk, Dashboard.
const STAGES: Stage[] = [
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

export default function HowItWorksPage() {
  return (
    <div className="px-5 py-14 md:px-8 md:py-20">
      <div className="mx-auto max-w-3xl">
        <Reveal>
          <h1 className="text-3xl font-bold tracking-tight text-slate-100 md:text-4xl">
            How DevTwin turns a repository into a capability score
          </h1>
          <p className="mt-4 text-base leading-relaxed text-slate-400">
            Seven deterministic stages, each persisting real artifacts you can
            trace back through — no step is a black box.
          </p>
        </Reveal>
      </div>

      <div className="mx-auto mt-14 max-w-3xl space-y-14">
        {STAGES.map((stage, i) => {
          const Icon = stage.icon;
          return (
            <Reveal key={stage.title} delay={Math.min(i * 0.05, 0.3)}>
              <div className="flex gap-4">
                <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg border border-cyan-500/30 bg-cyan-500/10">
                  <Icon className="h-4.5 w-4.5 text-cyan-400" aria-hidden="true" />
                </div>
                <div className="space-y-2.5">
                  <h2 className="text-lg font-semibold text-slate-100">{stage.title}</h2>
                  {stage.body.map((p, pi) => (
                    <p key={pi} className="text-sm leading-relaxed text-slate-400">
                      {p}
                    </p>
                  ))}
                </div>
              </div>
            </Reveal>
          );
        })}
      </div>

      <Reveal delay={0.1}>
        <div className="mx-auto mt-16 max-w-3xl rounded-xl border border-slate-800 bg-[#0f172a] p-6 text-center">
          <p className="text-sm text-slate-400">
            Ready to see this run against your own repositories?
          </p>
          <div className="mt-4 flex justify-center">
            <Link href="/signup">
              <Button variant="primary" size="md" leftIcon={<GitBranch className="h-4 w-4" />}>
                Connect with GitHub
              </Button>
            </Link>
          </div>
        </div>
      </Reveal>
    </div>
  );
}
