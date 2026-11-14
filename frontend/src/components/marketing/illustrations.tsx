/**
 * DevTwin Marketing — Inline SVG Illustrations
 *
 * Custom, on-brand technical illustrations (no external images/photos are
 * available in this environment, and abstract technical graphics suit an
 * evidence-first developer-intelligence product better than stock photos
 * anyway). Each one echoes a real part of the product:
 *
 *  - `GraphIllustration`      — abstract node/edge graph, echoes SkillGraph
 *  - `PipelineFlowIllustration` — layered stage flow, echoes the 7-stage pipeline
 *  - `EvidenceStackIllustration` — layered cards/documents, echoes Evidence
 *  - `RadarScoreIllustration` — radar/gauge motif, echoes capability scores
 *  - `AuthMotifIllustration`  — a quieter combined motif for the auth pages
 *
 * All use `currentColor` plus explicit light/dark text-color utilities on
 * their wrapping element so they stay on-palette (cyan/slate) in both
 * themes, and are purely decorative (`aria-hidden`).
 */

"use client";

import { motion, useReducedMotion } from "motion/react";

export function GraphIllustration({ className }: { className?: string }) {
  const reduceMotion = useReducedMotion();
  const nodes = [
    [60, 70], [180, 40], [300, 90], [220, 160], [90, 180], [340, 190], [150, 230],
  ];
  const edges = [
    [0, 1], [1, 2], [0, 4], [1, 3], [2, 3], [3, 5], [3, 6], [4, 6], [2, 5],
  ];
  return (
    <svg
      viewBox="0 0 400 260"
      className={className}
      aria-hidden="true"
      fill="none"
    >
      {edges.map(([a, b], i) => (
        <motion.line
          key={i}
          x1={nodes[a][0]}
          y1={nodes[a][1]}
          x2={nodes[b][0]}
          y2={nodes[b][1]}
          stroke="currentColor"
          strokeOpacity="0.25"
          strokeWidth="1.5"
          initial={reduceMotion ? undefined : { pathLength: 0, opacity: 0 }}
          animate={reduceMotion ? undefined : { pathLength: 1, opacity: 1 }}
          transition={{ duration: 1, delay: i * 0.08, ease: "easeOut" }}
        />
      ))}
      {nodes.map(([x, y], i) => (
        <motion.g
          key={i}
          initial={reduceMotion ? undefined : { opacity: 0, scale: 0.4 }}
          animate={reduceMotion ? undefined : { opacity: 1, scale: 1 }}
          transition={{ duration: 0.4, delay: 0.5 + i * 0.08, ease: "easeOut" }}
        >
          <circle cx={x} cy={y} r={i === 3 ? 10 : 6.5} fill="currentColor" fillOpacity={i === 3 ? 0.18 : 0.12} stroke="currentColor" strokeOpacity="0.6" strokeWidth="1.5" />
          <circle cx={x} cy={y} r={2.2} fill="currentColor" />
        </motion.g>
      ))}
    </svg>
  );
}

export function PipelineFlowIllustration({ className }: { className?: string }) {
  const stages = 5;
  const w = 400;
  const gap = w / stages;
  return (
    <svg viewBox="0 0 400 120" className={className} aria-hidden="true" fill="none">
      <line x1="20" y1="60" x2="380" y2="60" stroke="currentColor" strokeOpacity="0.2" strokeWidth="2" strokeDasharray="2 6" />
      {Array.from({ length: stages }).map((_, i) => {
        const x = 20 + i * (gap - 2) + 20;
        return (
          <g key={i}>
            <rect x={x - 22} y={30} width="44" height="60" rx="10" fill="currentColor" fillOpacity="0.08" stroke="currentColor" strokeOpacity="0.4" strokeWidth="1.5" />
            <circle cx={x} cy={60} r="5" fill="currentColor" fillOpacity="0.8" />
          </g>
        );
      })}
    </svg>
  );
}

export function EvidenceStackIllustration({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 220 180" className={className} aria-hidden="true" fill="none">
      {[0, 1, 2].map((i) => (
        <g key={i} transform={`translate(${i * 14}, ${i * 14})`}>
          <rect
            x="20"
            y="10"
            width="150"
            height="110"
            rx="12"
            fill="currentColor"
            fillOpacity={0.05 + i * 0.03}
            stroke="currentColor"
            strokeOpacity={0.35 - i * 0.05}
            strokeWidth="1.5"
          />
        </g>
      ))}
      <g transform="translate(28, 24)">
        <rect x="0" y="0" width="80" height="6" rx="3" fill="currentColor" fillOpacity="0.55" />
        <rect x="0" y="16" width="140" height="4" rx="2" fill="currentColor" fillOpacity="0.25" />
        <rect x="0" y="26" width="110" height="4" rx="2" fill="currentColor" fillOpacity="0.25" />
        <rect x="0" y="36" width="130" height="4" rx="2" fill="currentColor" fillOpacity="0.25" />
        <circle cx="150" cy="4" r="4" fill="currentColor" fillOpacity="0.7" />
      </g>
    </svg>
  );
}

export function RadarScoreIllustration({ className }: { className?: string }) {
  const rings = [1, 0.75, 0.5, 0.25];
  const center = 100;
  const points = [
    [100, 20], [165, 55], [172, 120], [120, 170], [55, 150], [32, 85],
  ];
  return (
    <svg viewBox="0 0 200 200" className={className} aria-hidden="true" fill="none">
      {rings.map((r) => (
        <circle key={r} cx={center} cy={center} r={80 * r} stroke="currentColor" strokeOpacity="0.15" strokeWidth="1" />
      ))}
      <polygon
        points={points.map((p) => p.join(",")).join(" ")}
        fill="currentColor"
        fillOpacity="0.12"
        stroke="currentColor"
        strokeOpacity="0.7"
        strokeWidth="1.5"
      />
      {points.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r="3.5" fill="currentColor" />
      ))}
    </svg>
  );
}

/** A quieter combined motif used behind/beside the login & signup form. */
export function AuthMotifIllustration({ className }: { className?: string }) {
  const nodes = [[40, 40], [140, 30], [220, 90], [150, 160], [50, 150], [20, 95]];
  const edges = [[0, 1], [1, 2], [2, 3], [3, 4], [4, 5], [5, 0], [0, 3]];
  return (
    <svg viewBox="0 0 240 200" className={className} aria-hidden="true" fill="none">
      {edges.map(([a, b], i) => (
        <line
          key={i}
          x1={nodes[a][0]}
          y1={nodes[a][1]}
          x2={nodes[b][0]}
          y2={nodes[b][1]}
          stroke="currentColor"
          strokeOpacity="0.18"
          strokeWidth="1.2"
        />
      ))}
      {nodes.map(([x, y], i) => (
        <circle key={i} cx={x} cy={y} r={i === 0 ? 7 : 4.5} fill="currentColor" fillOpacity="0.15" stroke="currentColor" strokeOpacity="0.5" strokeWidth="1.2" />
      ))}
    </svg>
  );
}
