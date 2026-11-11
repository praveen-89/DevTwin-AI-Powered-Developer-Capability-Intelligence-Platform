"use client";

/**
 * Client-side wrapper around PipelineSequence for the landing page.
 *
 * The stage list (which holds Lucide icon *component references*, not
 * JSX) must be constructed inside a Client Component. Passing component
 * references as a prop value across the Server -> Client boundary from
 * page.tsx (a Server Component, since it also exports `metadata`) is
 * rejected by Next.js's RSC serialization — hence this small wrapper.
 */

import { PipelineSequence } from "@/components/marketing/pipeline-sequence";
import { Activity, BarChart3, GitBranch, LayoutDashboard, Network, Server } from "lucide-react";

const PIPELINE_STAGES = [
  { icon: GitBranch, label: "GitHub Connect", description: "Connect GitHub via OAuth and select the repositories DevTwin should analyse." },
  { icon: Server, label: "Repository Analysis", description: "Repositories are safely mined for languages, dependency manifests, and code structure." },
  { icon: Network, label: "SkillGraph & CodeRisk", description: "Observations are mapped onto a skill taxonomy, and static rules flag engineering risk signals." },
  { icon: Activity, label: "Evidence", description: "Raw observations become contextualized evidence with strength, directness, and polarity." },
  { icon: BarChart3, label: "Capability Scores", description: "Evidence aggregates into capability scores and confidence metrics per skill." },
  { icon: LayoutDashboard, label: "Dashboard", description: "Every score traces back to its source evidence, with click-through provenance." },
];

export function LandingPipeline() {
  return <PipelineSequence stages={PIPELINE_STAGES} />;
}
