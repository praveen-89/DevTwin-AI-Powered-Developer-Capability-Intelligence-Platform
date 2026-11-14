"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { Info } from "lucide-react";
import {
  OverviewBannerVisual,
  RepositoriesBannerVisual,
  CapabilitiesBannerVisual,
  CodeRiskBannerVisual,
  SkillGraphBannerVisual,
  EvidenceBannerVisual,
  PipelineBannerVisual,
  AboutBannerVisual,
  LandingBannerVisual,
} from "@/components/layout/page-banner-illustrations";

export interface HeroStat {
  label: string;
  value: string | number;
  variant?: "accent" | "success" | "warning" | "purple" | "muted";
}

export type BannerVisualType =
  | "overview"
  | "repositories"
  | "capabilities"
  | "coderisk"
  | "skillgraph"
  | "evidence"
  | "pipeline"
  | "about"
  | "landing";

export interface PageHeroBannerProps {
  badge: string;
  title: string;
  description: string;
  stats?: HeroStat[];
  actions?: React.ReactNode;
  visualType?: BannerVisualType;
  bannerSvgSrc?: string;
  className?: string;
}

const VISUAL_COMPONENTS: Record<BannerVisualType, React.ComponentType<{ className?: string }>> = {
  overview: OverviewBannerVisual,
  repositories: RepositoriesBannerVisual,
  capabilities: CapabilitiesBannerVisual,
  coderisk: CodeRiskBannerVisual,
  skillgraph: SkillGraphBannerVisual,
  evidence: EvidenceBannerVisual,
  pipeline: PipelineBannerVisual,
  about: AboutBannerVisual,
  landing: LandingBannerVisual,
};

export function PageHeroBanner({
  badge,
  title,
  description,
  stats,
  actions,
  visualType,
  bannerSvgSrc,
  className,
}: PageHeroBannerProps) {
  const VisualComponent = visualType ? VISUAL_COMPONENTS[visualType] : null;

  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-2xl sm:rounded-3xl border transition-all duration-200",
        // Theme-aware container: crisp white/slate in light mode, deep technical dark slate in dark mode
        "border-slate-200 bg-gradient-to-b from-white via-slate-50/90 to-slate-100/70 p-4 sm:p-5 md:p-6 shadow-sm",
        "dark:border-slate-800 dark:bg-gradient-to-b dark:from-[#0f172a] dark:via-[#090d16] dark:to-[#0b1120] dark:shadow-none",
        className
      )}
    >
      {/* Ambient background glow & tech grid pattern */}
      <div className="pointer-events-none absolute inset-0 -z-10 overflow-hidden" aria-hidden="true">
        <div className="absolute -right-20 -top-20 h-72 w-72 rounded-full bg-cyan-500/10 blur-3xl" />
        <div className="absolute -left-20 -bottom-20 h-72 w-72 rounded-full bg-emerald-500/10 blur-3xl" />
        <div className="tech-grid absolute inset-0 opacity-[0.4] dark:opacity-100" />
      </div>

      <div className="space-y-4">
        {/* 1. First: Badge & Stats Row */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="inline-flex w-fit items-center gap-2 rounded-full border border-cyan-500/40 bg-cyan-500/10 px-3.5 py-1 text-xs font-semibold text-cyan-800 dark:text-cyan-300">
            <span className="h-1.5 w-1.5 rounded-full bg-cyan-500 animate-pulse" aria-hidden="true" />
            <span className="uppercase tracking-wider text-[10px] sm:text-[11px]">{badge}</span>
          </div>

          {/* Optional stat indicators */}
          {stats && stats.length > 0 && (
            <div className="flex flex-wrap items-center gap-2">
              {stats.map((stat, i) => {
                let badgeClass = "border-slate-200 bg-white text-slate-800 dark:border-slate-800 dark:bg-slate-900/80 dark:text-slate-200";
                let valClass = "text-slate-900 dark:text-slate-100";

                if (stat.variant === "accent") {
                  badgeClass = "border-cyan-500/40 bg-cyan-500/10 text-cyan-800 dark:text-cyan-300";
                  valClass = "text-cyan-700 dark:text-cyan-400";
                } else if (stat.variant === "success") {
                  badgeClass = "border-emerald-500/40 bg-emerald-500/10 text-emerald-800 dark:text-emerald-300";
                  valClass = "text-emerald-700 dark:text-emerald-400";
                } else if (stat.variant === "warning") {
                  badgeClass = "border-amber-500/40 bg-amber-500/10 text-amber-800 dark:text-amber-300";
                  valClass = "text-amber-700 dark:text-amber-400";
                } else if (stat.variant === "purple") {
                  badgeClass = "border-purple-500/40 bg-purple-500/10 text-purple-800 dark:text-purple-300";
                  valClass = "text-purple-700 dark:text-purple-400";
                }

                return (
                  <div
                    key={i}
                    className={cn(
                      "inline-flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs shadow-2xs transition-colors",
                      badgeClass
                    )}
                  >
                    <span className="font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wide text-[10px]">
                      {stat.label}:
                    </span>
                    <span className={cn("font-mono font-bold", valClass)}>{stat.value}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* 2. After this: Generated image (seamless inside main hero card) */}
        <div className="w-full">
          {VisualComponent ? (
            <div className="w-full">
              <VisualComponent className="w-full" />
            </div>
          ) : bannerSvgSrc ? (
            <div className="w-full">
              {/* Standalone SVG image with dark/light auto-switching */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={bannerSvgSrc}
                alt={`${title} banner`}
                className="w-full h-auto rounded-lg"
                loading="eager"
              />
            </div>
          ) : null}
        </div>

        {/* 3. After this: Title & Description */}
        <div className="space-y-2.5">
          <h1 className="text-2xl sm:text-3xl lg:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100">
            {title}
          </h1>

          {description && (
            <p className="max-w-3xl text-sm sm:text-base font-medium leading-relaxed text-slate-700 dark:text-slate-300">
              {description}
            </p>
          )}
        </div>

        {/* 4. Below this: Buttons / Actions */}
        {actions && (
          <div className="flex flex-wrap items-center gap-3 pt-1">
            {actions}
          </div>
        )}
      </div>
    </div>
  );
}

