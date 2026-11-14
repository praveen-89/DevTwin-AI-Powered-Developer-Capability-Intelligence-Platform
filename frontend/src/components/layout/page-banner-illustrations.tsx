"use client";

import { motion, useReducedMotion } from "motion/react";
import { cn } from "@/lib/utils";

interface BannerVisualProps {
  className?: string;
}

/**
 * 1. Overview Banner Visual
 * Digital Twin core telemetry with pulse rings, score gauge (0.84),
 * confidence readout (0.92), and linked intelligence nodes.
 */
export function OverviewBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <radialGradient id="overviewGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
          </radialGradient>
          <linearGradient id="cyanEmeraldGrad" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="100%" stopColor="#10b981" />
          </linearGradient>
          <linearGradient id="purpleCyanGrad" x1="0%" y1="100%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#a855f7" />
            <stop offset="100%" stopColor="#06b6d4" />
          </linearGradient>
        </defs>

        {/* Ambient background glow circle */}
        <circle cx="260" cy="140" r="120" fill="url(#overviewGlow)" />

        {/* Outer orbital radar rings */}
        <circle
          cx="260"
          cy="140"
          r="110"
          className="stroke-slate-300 dark:stroke-slate-700/60"
          strokeWidth="1"
          strokeDasharray="4 4"
        />
        <circle
          cx="260"
          cy="140"
          r="75"
          className="stroke-cyan-500/40 dark:stroke-cyan-400/30"
          strokeWidth="1.5"
        />
        <circle
          cx="260"
          cy="140"
          r="40"
          className="stroke-slate-300 dark:stroke-slate-700"
          strokeWidth="1"
        />

        {/* Scanning radar sweep line */}
        <motion.line
          x1="260"
          y1="140"
          x2="365"
          y2="140"
          stroke="#06b6d4"
          strokeWidth="2"
          strokeLinecap="round"
          className="opacity-70 origin-[260px_140px]"
          animate={reduceMotion ? undefined : { rotate: 360 }}
          transition={{ repeat: Infinity, duration: 8, ease: "linear" }}
        />

        {/* Pulsing radar echo wave */}
        <motion.circle
          cx="260"
          cy="140"
          className="stroke-cyan-500/40"
          strokeWidth="1.5"
          fill="none"
          animate={reduceMotion ? undefined : { r: [45, 110], opacity: [0.7, 0] }}
          transition={{ repeat: Infinity, duration: 3.5, ease: "easeOut" }}
        />

        {/* Connected Node links */}
        <line x1="260" y1="140" x2="120" y2="65" className="stroke-cyan-500/50 dark:stroke-cyan-400/40" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="260" y1="140" x2="400" y2="65" className="stroke-emerald-500/50 dark:stroke-emerald-400/40" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="260" y1="140" x2="110" y2="210" className="stroke-purple-500/50 dark:stroke-purple-400/40" strokeWidth="1.5" strokeDasharray="3 3" />
        <line x1="260" y1="140" x2="410" y2="210" className="stroke-amber-500/50 dark:stroke-amber-400/40" strokeWidth="1.5" strokeDasharray="3 3" />

        {/* Central Core: Digital Twin Engine with subtle pulse */}
        <motion.circle
          cx="260"
          cy="140"
          r="26"
          className="fill-white dark:fill-slate-900 stroke-cyan-500"
          strokeWidth="3"
          animate={reduceMotion ? undefined : { scale: [1, 1.04, 1] }}
          transition={{ repeat: Infinity, duration: 2.5, ease: "easeInOut" }}
          style={{ transformOrigin: "260px 140px" }}
        />
        <circle cx="260" cy="140" r="16" fill="url(#cyanEmeraldGrad)" className="opacity-90" />
        <text x="260" y="144" textAnchor="middle" className="fill-white font-mono text-[9px] font-bold tracking-wider">TWIN</text>

        {/* Node 1: Top-Left (Capability Score) */}
        <g transform="translate(70, 40)">
          <rect width="105" height="46" rx="8" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
          <circle cx="16" cy="23" r="5" fill="#06b6d4" />
          <text x="28" y="19" className="fill-slate-700 dark:fill-slate-300 font-sans text-[10px] uppercase font-bold">Capability</text>
          <text x="28" y="36" className="fill-slate-900 dark:fill-slate-100 font-mono text-[14px] font-extrabold">0.84 <tspan className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">High</tspan></text>
        </g>

        {/* Node 2: Top-Right (Confidence) */}
        <g transform="translate(345, 40)">
          <rect width="110" height="46" rx="8" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
          <circle cx="16" cy="23" r="5" fill="#10b981" />
          <text x="28" y="19" className="fill-slate-700 dark:fill-slate-300 font-sans text-[10px] uppercase font-bold">Confidence</text>
          <text x="28" y="36" className="fill-slate-900 dark:fill-slate-100 font-mono text-[14px] font-extrabold">0.92 <tspan className="text-[10px] font-semibold text-cyan-600 dark:text-cyan-400">92%</tspan></text>
        </g>

        {/* Node 3: Bottom-Left (Evidence Records) */}
        <g transform="translate(60, 185)">
          <rect width="105" height="46" rx="8" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
          <circle cx="16" cy="23" r="5" fill="#a855f7" />
          <text x="28" y="19" className="fill-slate-700 dark:fill-slate-300 font-sans text-[10px] uppercase font-bold">Evidence</text>
          <text x="28" y="36" className="fill-slate-900 dark:fill-slate-100 font-mono text-[14px] font-extrabold">86 <tspan className="text-[10px] font-medium text-slate-600 dark:text-slate-400">Items</tspan></text>
        </g>

        {/* Node 4: Bottom-Right (CodeRisk Health) */}
        <g transform="translate(355, 185)">
          <rect width="105" height="46" rx="8" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
          <circle cx="16" cy="23" r="5" fill="#f59e0b" />
          <text x="28" y="19" className="fill-slate-700 dark:fill-slate-300 font-sans text-[10px] uppercase font-bold">Risk Findings</text>
          <text x="28" y="36" className="fill-slate-900 dark:fill-slate-100 font-mono text-[14px] font-extrabold">1 <tspan className="text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">Low</tspan></text>
        </g>
      </svg>
    </div>
  );
}

/**
 * 2. Repositories Banner Visual
 * Git tree commit topology, multi-branch parsing, manifest symbols,
 * and secure tarball streaming pipeline.
 */
export function RepositoriesBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="repoBranchGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#06b6d4" />
            <stop offset="50%" stopColor="#10b981" />
            <stop offset="100%" stopColor="#3b82f6" />
          </linearGradient>
        </defs>

        {/* Git Branch Lines */}
        <path
          d="M 60 140 L 460 140"
          className="stroke-slate-300 dark:stroke-slate-700"
          strokeWidth="3"
        />
        <path
          d="M 140 140 C 180 140 190 80 240 80 L 420 80"
          className="stroke-cyan-500"
          strokeWidth="2.5"
          strokeDasharray="5 3"
        />
        <path
          d="M 200 140 C 240 140 250 200 300 200 L 440 200"
          className="stroke-purple-500"
          strokeWidth="2.5"
        />

        {/* Commit Nodes on Main Branch */}
        <circle cx="90" cy="140" r="8" className="fill-white dark:fill-slate-900 stroke-slate-400 dark:stroke-slate-500" strokeWidth="2.5" />
        <circle cx="160" cy="140" r="8" className="fill-cyan-500 stroke-white dark:stroke-slate-900" strokeWidth="2.5" />
        <circle cx="280" cy="140" r="8" className="fill-emerald-500 stroke-white dark:stroke-slate-900" strokeWidth="2.5" />
        <circle cx="380" cy="140" r="10" className="fill-white dark:fill-slate-900 stroke-cyan-500" strokeWidth="3" />
        <circle cx="380" cy="140" r="4" fill="#06b6d4" />

        {/* Main branch traveling commit photon */}
        {!reduceMotion && (
          <motion.circle
            cy="140"
            r="4.5"
            className="fill-cyan-400"
            animate={{ cx: [60, 160, 280, 380, 460], opacity: [0, 1, 1, 1, 0] }}
            transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
          />
        )}

        {/* Feature Branch Commits */}
        <circle cx="270" cy="80" r="7" className="fill-cyan-500 stroke-white dark:stroke-slate-900" strokeWidth="2" />
        <circle cx="350" cy="80" r="7" className="fill-cyan-400 stroke-white dark:stroke-slate-900" strokeWidth="2" />

        {/* Analysis Branch Commits */}
        <circle cx="330" cy="200" r="7" className="fill-purple-500 stroke-white dark:stroke-slate-900" strokeWidth="2" />
        <circle cx="410" cy="200" r="7" className="fill-purple-400 stroke-white dark:stroke-slate-900" strokeWidth="2" />

        {/* Floating Commit Callout with subtle hover motion */}
        <motion.g
          transform="translate(195, 25)"
          animate={reduceMotion ? undefined : { y: [0, -3, 0] }}
          transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
        >
          <rect width="140" height="42" rx="6" className="fill-white dark:fill-slate-900 stroke-cyan-500/50" strokeWidth="1.5" />
          <text x="12" y="18" className="fill-slate-700 dark:fill-slate-300 font-mono text-[9px] font-bold">COMMIT SHA: 07633b4</text>
          <text x="12" y="32" className="fill-slate-900 dark:fill-slate-100 font-sans text-[11px] font-bold">Python AST Parsed</text>
        </motion.g>

        {/* Technology Language Badges */}
        <g transform="translate(50, 225)">
          <rect width="70" height="26" rx="13" className="fill-cyan-500/15 stroke-cyan-500/40" strokeWidth="1" />
          <text x="35" y="17" textAnchor="middle" className="fill-cyan-700 dark:fill-cyan-400 font-mono text-[10px] font-bold">Python</text>
        </g>
        <g transform="translate(130, 225)">
          <rect width="88" height="26" rx="13" className="fill-emerald-500/15 stroke-emerald-500/40" strokeWidth="1" />
          <text x="44" y="17" textAnchor="middle" className="fill-emerald-700 dark:fill-emerald-400 font-mono text-[10px] font-bold">TypeScript</text>
        </g>
        <g transform="translate(228, 225)">
          <rect width="64" height="26" rx="13" className="fill-purple-500/15 stroke-purple-500/40" strokeWidth="1" />
          <text x="32" y="17" textAnchor="middle" className="fill-purple-700 dark:fill-purple-400 font-mono text-[10px] font-bold">Rust</text>
        </g>
        <g transform="translate(302, 225)">
          <rect width="110" height="26" rx="13" className="fill-slate-500/15 stroke-slate-400 dark:stroke-slate-600" strokeWidth="1" />
          <text x="55" y="17" textAnchor="middle" className="fill-slate-700 dark:fill-slate-300 font-mono text-[10px] font-bold">package.json</text>
        </g>
      </svg>
    </div>
  );
}

/**
 * 3. Capabilities Banner Visual
 * Sigmoid mathematical capability curve, uncertainty-aware confidence interval,
 * and multi-target radar polygon.
 */
export function CapabilitiesBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <linearGradient id="curveFillGrad" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#06b6d4" stopOpacity="0" />
          </linearGradient>
          <linearGradient id="confidenceBand" x1="0%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.05" />
          </linearGradient>
        </defs>

        {/* Mathematical coordinate axes */}
        <line x1="70" y1="220" x2="460" y2="220" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
        <line x1="70" y1="220" x2="70" y2="35" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />

        {/* Y-axis score markings */}
        <text x="50" y="45" className="fill-slate-600 dark:fill-slate-400 font-mono text-[10px] font-semibold">1.0</text>
        <text x="50" y="132" className="fill-slate-600 dark:fill-slate-400 font-mono text-[10px] font-semibold">0.5</text>
        <text x="50" y="224" className="fill-slate-600 dark:fill-slate-400 font-mono text-[10px] font-semibold">0.0</text>

        {/* Gridlines */}
        <line x1="70" y1="130" x2="460" y2="130" className="stroke-slate-200 dark:stroke-slate-800" strokeWidth="1" strokeDasharray="4 4" />
        <line x1="70" y1="40" x2="460" y2="40" className="stroke-slate-200 dark:stroke-slate-800" strokeWidth="1" strokeDasharray="4 4" />

        {/* Uncertainty Confidence Band (Upper and lower limits) */}
        <path
          d="M 70 210 Q 180 195 240 115 T 450 60 L 450 95 Q 340 140 240 155 T 70 220 Z"
          fill="url(#confidenceBand)"
        />

        {/* Sigmoid Area Fill */}
        <path
          d="M 70 215 Q 180 205 240 130 T 450 65 L 450 220 L 70 220 Z"
          fill="url(#curveFillGrad)"
        />

        {/* Main Sigmoid Score Curve */}
        <path
          d="M 70 215 Q 180 205 240 130 T 450 65"
          stroke="#06b6d4"
          strokeWidth="3.5"
          strokeLinecap="round"
        />

        {/* Formula Badge */}
        <g transform="translate(130, 15)">
          <rect width="250" height="34" rx="6" className="fill-white dark:fill-slate-900 stroke-cyan-500/50" strokeWidth="1.5" />
          <text x="125" y="22" textAnchor="middle" className="fill-cyan-700 dark:fill-cyan-300 font-mono text-[11px] font-bold">
            Score = clamp(σ(Σ w_i / 3.0), 0.01, 0.99)
          </text>
        </g>

        {/* Sample Point Markers on Curve with active beacon pulse */}
        <circle cx="160" cy="195" r="5" className="fill-white dark:fill-slate-900 stroke-cyan-500" strokeWidth="2.5" />
        <motion.circle
          cx="240"
          cy="130"
          className="stroke-emerald-400"
          strokeWidth="1.5"
          fill="none"
          animate={reduceMotion ? undefined : { r: [6, 17], opacity: [0.8, 0] }}
          transition={{ repeat: Infinity, duration: 2.2, ease: "easeOut" }}
        />
        <circle cx="240" cy="130" r="6" className="fill-emerald-500 stroke-white dark:stroke-slate-900" strokeWidth="2.5" />
        <circle cx="360" cy="80" r="7" className="fill-cyan-500 stroke-white dark:stroke-slate-900" strokeWidth="2.5" />

        {/* Data Callout */}
        <g transform="translate(290, 100)">
          <rect width="145" height="44" rx="6" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
          <text x="12" y="18" className="fill-slate-700 dark:fill-slate-300 font-sans text-[9px] uppercase font-bold">Backend Dev</text>
          <text x="12" y="34" className="fill-emerald-600 dark:fill-emerald-400 font-mono text-[12px] font-extrabold">0.89 (High Conf)</text>
        </g>
      </svg>
    </div>
  );
}

/**
 * 4. CodeRisk Banner Visual
 * Engineering risk shield matrix with 4 static rule categories
 * (Security, Reliability, Maintainability, Testing) and severity badges.
 */
export function CodeRiskBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Animated Scanner Beam line down the shield */}
        {!reduceMotion && (
          <motion.line
            x1="180"
            x2="340"
            stroke="#06b6d4"
            strokeWidth="1.5"
            strokeLinecap="round"
            className="opacity-70"
            animate={{ y1: [40, 220, 40], y2: [40, 220, 40], opacity: [0, 0.7, 0] }}
            transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
          />
        )}

        {/* Central Shield Outline */}
        <path
          d="M 260 30 L 370 65 C 370 160 260 240 260 240 C 260 240 150 160 150 65 Z"
          className="fill-cyan-500/10 stroke-cyan-500/40"
          strokeWidth="2"
        />

        {/* Inner Shield Divider */}
        <line x1="260" y1="35" x2="260" y2="235" className="stroke-cyan-500/25" strokeWidth="1.5" strokeDasharray="4 4" />
        <line x1="165" y1="120" x2="355" y2="120" className="stroke-cyan-500/25" strokeWidth="1.5" strokeDasharray="4 4" />

        {/* 4 Category Quadrants Inside Shield */}
        <text x="210" y="95" textAnchor="middle" className="fill-rose-600 dark:fill-rose-400 font-mono text-[11px] font-bold">SEC</text>
        <text x="310" y="95" textAnchor="middle" className="fill-amber-600 dark:fill-amber-400 font-mono text-[11px] font-bold">REL</text>
        <text x="210" y="165" textAnchor="middle" className="fill-cyan-700 dark:fill-cyan-400 font-mono text-[11px] font-bold">MAINT</text>
        <text x="310" y="165" textAnchor="middle" className="fill-emerald-700 dark:fill-emerald-400 font-mono text-[11px] font-bold">TEST</text>

        {/* Floating Callout: SEC-001 (Secret Redaction) */}
        <g transform="translate(40, 45)">
          <rect width="140" height="48" rx="8" className="fill-white dark:fill-slate-900 stroke-rose-500/50" strokeWidth="1.5" />
          <text x="12" y="20" className="fill-rose-700 dark:fill-rose-400 font-mono text-[10px] font-bold">SEC-001 Secret Guard</text>
          <text x="12" y="36" className="fill-slate-700 dark:fill-slate-300 font-mono text-[9px] font-medium">Token auto-redacted</text>
        </g>

        {/* Floating Callout: Rule SEC-002 (Subprocess AST) */}
        <g transform="translate(340, 45)">
          <rect width="140" height="48" rx="8" className="fill-white dark:fill-slate-900 stroke-amber-500/50" strokeWidth="1.5" />
          <text x="12" y="20" className="fill-amber-700 dark:fill-amber-400 font-mono text-[10px] font-bold">SEC-002 AST Scan</text>
          <text x="12" y="36" className="fill-slate-700 dark:fill-slate-300 font-mono text-[9px] font-medium">shell=True safe check</text>
        </g>

        {/* Golden Rule Pill: Risk ≠ Competence */}
        <g transform="translate(160, 245)">
          <rect width="200" height="28" rx="14" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
          <text x="100" y="18" textAnchor="middle" className="fill-slate-900 dark:fill-slate-100 font-sans text-[11px] font-bold">
            Principle: Risk ≠ Competence
          </text>
        </g>
      </svg>
    </div>
  );
}

/**
 * 5. SkillGraph Banner Visual
 * Relational knowledge graph with Skills (cyan), Technologies (emerald),
 * Concepts (purple), and directed relationship edges.
 */
export function SkillGraphBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          <marker id="edgeArrow" viewBox="0 0 10 10" refX="5" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
            <path d="M 0 1 L 10 5 L 0 9 z" className="fill-slate-500 dark:fill-slate-400" />
          </marker>
        </defs>

        {/* Directed Edges with signal flow */}
        <motion.path
          d="M 120 70 L 250 140"
          className="stroke-cyan-500/70"
          strokeWidth="1.5"
          markerEnd="url(#edgeArrow)"
          strokeDasharray="4 4"
          animate={reduceMotion ? undefined : { strokeDashoffset: [0, -16] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "linear" }}
        />
        <motion.path
          d="M 250 140 L 390 70"
          className="stroke-emerald-500/70"
          strokeWidth="1.5"
          markerEnd="url(#edgeArrow)"
          strokeDasharray="4 4"
          animate={reduceMotion ? undefined : { strokeDashoffset: [0, -16] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "linear" }}
        />
        <motion.path
          d="M 120 220 L 250 140"
          className="stroke-purple-500/70"
          strokeWidth="1.5"
          markerEnd="url(#edgeArrow)"
          strokeDasharray="4 4"
          animate={reduceMotion ? undefined : { strokeDashoffset: [0, -16] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "linear" }}
        />
        <motion.path
          d="M 250 140 L 400 220"
          className="stroke-purple-500/70"
          strokeWidth="1.5"
          markerEnd="url(#edgeArrow)"
          strokeDasharray="4 4"
          animate={reduceMotion ? undefined : { strokeDashoffset: [0, -16] }}
          transition={{ repeat: Infinity, duration: 1.8, ease: "linear" }}
        />
        <path d="M 120 70 L 120 220" className="stroke-slate-300/50 dark:stroke-slate-800" strokeWidth="1" strokeDasharray="3 3" />

        {/* Central Skill Node: Cyan Ellipse */}
        <g transform="translate(250, 140)">
          <ellipse cx="0" cy="0" rx="64" ry="26" className="fill-cyan-500/15 stroke-cyan-500" strokeWidth="2.5" />
          <text x="0" y="4" textAnchor="middle" className="fill-cyan-800 dark:fill-cyan-300 font-sans text-[11px] font-bold">
            Backend Dev
          </text>
        </g>

        {/* Top-Left Technology Node: Emerald Rect */}
        <g transform="translate(120, 70)">
          <rect x="-48" y="-18" width="96" height="36" rx="6" className="fill-emerald-500/15 stroke-emerald-500" strokeWidth="2" />
          <text x="0" y="4" textAnchor="middle" className="fill-emerald-800 dark:fill-emerald-300 font-mono text-[11px] font-bold">
            FastAPI
          </text>
        </g>

        {/* Top-Right Technology Node: Emerald Rect */}
        <g transform="translate(390, 70)">
          <rect x="-52" y="-18" width="104" height="36" rx="6" className="fill-emerald-500/15 stroke-emerald-500" strokeWidth="2" />
          <text x="0" y="4" textAnchor="middle" className="fill-emerald-800 dark:fill-emerald-300 font-mono text-[11px] font-bold">
            PostgreSQL
          </text>
        </g>

        {/* Bottom-Left Concept Node: Purple Diamond */}
        <g transform="translate(120, 215)">
          <polygon points="0,-24 48,0 0,24 -48,0" className="fill-purple-500/15 stroke-purple-500" strokeWidth="2" />
          <text x="0" y="4" textAnchor="middle" className="fill-purple-800 dark:fill-purple-300 font-sans text-[10px] font-bold">
            Async I/O
          </text>
        </g>

        {/* Bottom-Right Concept Node: Purple Diamond */}
        <g transform="translate(400, 215)">
          <polygon points="0,-24 52,0 0,24 -52,0" className="fill-purple-500/15 stroke-purple-500" strokeWidth="2" />
          <text x="0" y="4" textAnchor="middle" className="fill-purple-800 dark:fill-purple-300 font-sans text-[10px] font-bold">
            ORM Model
          </text>
        </g>
      </svg>
    </div>
  );
}

/**
 * 6. Evidence Banner Visual
 * Grounded observation-to-evidence synthesis cards with provenance,
 * strength, and polarity indicators.
 */
export function EvidenceBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Layered Evidence Card 1 (Bottom) */}
        <rect x="90" y="30" width="340" height="58" rx="8" className="fill-slate-100 dark:fill-slate-900/50 stroke-slate-300 dark:stroke-slate-800" strokeWidth="1" />
        <circle cx="115" cy="59" r="5" fill="#10b981" />
        <text x="135" y="55" className="fill-slate-700 dark:fill-slate-300 font-mono text-[9px] font-bold">LANGUAGE DETECTED: Python (94.2%)</text>
        <text x="135" y="70" className="fill-slate-900 dark:fill-slate-100 font-mono text-[11px] font-bold">Polarity: +1.0 · Strength: 0.40</text>

        {/* Layered Evidence Card 2 (Middle) */}
        <rect x="75" y="98" width="370" height="62" rx="8" className="fill-white dark:fill-slate-900/80 stroke-slate-300 dark:stroke-slate-700" strokeWidth="1.5" />
        <circle cx="100" cy="129" r="5" fill="#06b6d4" />
        <text x="120" y="123" className="fill-slate-700 dark:fill-slate-300 font-mono text-[10px] font-bold">CLASS DEFINED: AsyncJobWorker</text>
        <text x="120" y="141" className="fill-cyan-700 dark:fill-cyan-300 font-mono text-[11px] font-bold">APPLIED_ENGINEERING (Strength: 0.80)</text>

        {/* Layered Evidence Card 3 (Forefront / Focus with gentle float) */}
        <motion.g
          transform="translate(60, 175)"
          animate={reduceMotion ? undefined : { y: [0, -3, 0] }}
          transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
        >
          <rect width="400" height="74" rx="10" className="fill-white dark:fill-slate-900 stroke-cyan-500/60" strokeWidth="2" />
          <motion.circle
            cx="28"
            cy="37"
            r="6"
            fill="#10b981"
            animate={reduceMotion ? undefined : { scale: [1, 1.25, 1] }}
            transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
          />
          <text x="48" y="28" className="fill-slate-700 dark:fill-slate-300 font-mono text-[10px] font-bold">PROVENANCE: backend/app/workers/runner.py:124</text>
          <text x="48" y="47" className="fill-slate-900 dark:fill-slate-100 font-sans text-[12px] font-extrabold">
            Demonstrates Concurrency & Atomic DB Locking
          </text>
          <text x="48" y="62" className="fill-emerald-700 dark:fill-emerald-400 font-mono text-[10px] font-bold">
            Weight: S=0.80 · D=0.90 · R=0.95 · P=+1.0
          </text>
        </motion.g>
      </svg>
    </div>
  );
}

/**
 * 7. 8-Stage Pipeline Banner Visual (How It Works)
 */
export function PipelineBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  const stages = [
    { num: "1", name: "Queue" },
    { num: "2", name: "Fetch" },
    { num: "3", name: "Mine" },
    { num: "4", name: "Graph" },
    { num: "5", name: "Risk" },
    { num: "6", name: "Evidence" },
    { num: "7", name: "Score" },
    { num: "8", name: "Done" },
  ];

  // Each stage lights up sequentially: active window per stage = 1s, total cycle = 9.6s
  const totalDuration = 9.6;
  const activeWindow = 0.75; // how long (seconds) each node stays lit green
  const n = stages.length;

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 540 160"
        className="w-full h-auto max-h-[150px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Conveyor track line */}
        <line x1="40" y1="80" x2="500" y2="80" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="3" />

        {stages.map((stage, i) => {
          const x = 50 + i * 62;
          const isDone = i === 7;

          // Normalized times when this stage turns green and dims back
          const onAt = (i * (totalDuration / n)) / totalDuration;
          const offAt = Math.min((i * (totalDuration / n) + activeWindow) / totalDuration, 1);
          // tiny epsilon for sharp transitions
          const eps = 0.001;

          return (
            <g key={stage.name} transform={`translate(${x}, 80)`}>
              {/* Base circle — always visible, handles dark/light theme */}
              <circle
                cx="0"
                cy="0"
                r="18"
                className={
                  isDone
                    ? "fill-emerald-500 stroke-white dark:stroke-slate-900"
                    : "fill-white dark:fill-slate-900 stroke-cyan-500"
                }
                strokeWidth="2.5"
              />

              {/* Active green overlay — fades in/out at this stage's turn */}
              {!reduceMotion && !isDone && (
                <motion.circle
                  cx="0"
                  cy="0"
                  r="18"
                  fill="#10b981"
                  stroke="#10b981"
                  strokeWidth="2.5"
                  animate={{
                    opacity: [0, 0, 1, 1, 0, 0],
                  }}
                  transition={{
                    repeat: Infinity,
                    duration: totalDuration,
                    ease: "easeInOut",
                    times: [
                      0,
                      Math.max(0, onAt - eps),
                      onAt,
                      offAt,
                      Math.min(1, offAt + eps),
                      1,
                    ],
                  }}
                />
              )}

              {/* Number — white when active, themed otherwise */}
              <text
                x="0"
                y="4"
                textAnchor="middle"
                className={
                  isDone
                    ? "fill-white font-mono text-[11px] font-bold"
                    : "fill-cyan-700 dark:fill-cyan-300 font-mono text-[11px] font-bold"
                }
              >
                {stage.num}
              </text>

              {/* White number overlay shown only when active */}
              {!reduceMotion && !isDone && (
                <motion.text
                  x="0"
                  y="4"
                  textAnchor="middle"
                  fill="white"
                  className="font-mono text-[11px] font-bold"
                  animate={{
                    opacity: [0, 0, 1, 1, 0, 0],
                  }}
                  transition={{
                    repeat: Infinity,
                    duration: totalDuration,
                    ease: "easeInOut",
                    times: [
                      0,
                      Math.max(0, onAt - eps),
                      onAt,
                      offAt,
                      Math.min(1, offAt + eps),
                      1,
                    ],
                  }}
                >
                  {stage.num}
                </motion.text>
              )}

              <text
                x="0"
                y="34"
                textAnchor="middle"
                className="fill-slate-700 dark:fill-slate-300 font-sans text-[10px] font-bold"
              >
                {stage.name}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

/**
 * 8. About Banner Visual
 * Architectural Ground Truth vs Resume Parser comparison.
 */
export function AboutBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  // 4 evidence items — stagger 0.6s apart, hold, then all fade out together
  const evidenceItems = [
    "✓ AST Verified",
    "✓ Git Provenance",
    "✓ Risk Weighted",
    "✓ Sigmoid Scored",
  ];

  const itemDelay = 0.65;       // seconds between each item appearing
  const holdAfterLast = 1.0;    // seconds to hold after the last item
  const fadeOut = 0.5;          // seconds to fade everything out before loop restart
  const totalDuration = evidenceItems.length * itemDelay + holdAfterLast + fadeOut;

  // Helper: returns [0, 0, 1, 1, 0] times for a staggered item
  const itemTimes = (i: number) => {
    const startAt  = (i * itemDelay) / totalDuration;
    const peakAt   = (i * itemDelay + 0.25) / totalDuration;
    const holdEnd  = (totalDuration - fadeOut) / totalDuration;
    return [0, startAt, peakAt, holdEnd, 1] as [number, number, number, number, number];
  };

  const footerTimes = () => {
    const startAt  = (evidenceItems.length * itemDelay) / totalDuration;
    const peakAt   = startAt + 0.1;
    const holdEnd  = (totalDuration - fadeOut) / totalDuration;
    return [0, startAt, peakAt, holdEnd, 1] as [number, number, number, number, number];
  };

  // Fixed y positions for 4 items — card top y=35, header y=67, divider y=73
  // Start items well below divider at y=94, spacing 22px each, footer at y=208
  // Card bottom = 35+205 = 240, so footer at y=218 is safely inside
  const itemYs = [94, 116, 138, 160];
  const footerY = 186;

  return (
    <div className={cn("relative flex items-center justify-center p-2 select-none", className)}>
      <svg
        viewBox="0 0 520 280"
        className="w-full h-auto max-h-[250px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        <defs>
          {/* Clip the right card interior so text never bleeds outside */}
          <clipPath id="rightCardClip">
            <rect x="295" y="78" width="176" height="156" />
          </clipPath>
        </defs>

        {/* Left: Traditional Resume / Quiz (Crossed / Static) */}
        <g transform="translate(60, 35)">
          <rect width="180" height="205" rx="10" className="fill-white dark:fill-slate-900/60 stroke-slate-300 dark:stroke-slate-800" strokeWidth="1.5" />
          <text x="90" y="32" textAnchor="middle" className="fill-slate-700 dark:fill-slate-300 font-sans text-[11px] font-bold uppercase">
            Static Resumes
          </text>
          <line x1="25" y1="50" x2="155" y2="50" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="1" />
          <line x1="25" y1="75" x2="135" y2="75" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="1" />
          <line x1="25" y1="100" x2="145" y2="100" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="1" />
          <line x1="25" y1="125" x2="115" y2="125" className="stroke-slate-300 dark:stroke-slate-700" strokeWidth="1" />
          <text x="90" y="175" textAnchor="middle" className="fill-rose-600 dark:fill-rose-400 font-sans text-[11px] font-bold">
            Unverified Claims
          </text>
        </g>

        {/* Center Conversion Vector with horizontal pulse */}
        <motion.g
          animate={reduceMotion ? undefined : { x: [0, 5, 0] }}
          transition={{ repeat: Infinity, duration: 2, ease: "easeInOut" }}
        >
          <path d="M 255 135 L 280 135" stroke="#06b6d4" strokeWidth="3" strokeLinecap="round" />
          <polygon points="280,130 292,135 280,140" fill="#06b6d4" />
        </motion.g>

        {/* Right card border and header — always visible */}
        <rect x="295" y="35" width="180" height="205" rx="10" className="fill-white dark:fill-slate-900 stroke-cyan-500/70" strokeWidth="2" />
        <text x="385" y="67" textAnchor="middle" className="fill-cyan-700 dark:fill-cyan-300 font-sans text-[11px] font-bold uppercase">
          DevTwin Evidence
        </text>
        <line x1="320" y1="73" x2="471" y2="73" className="stroke-cyan-500/40" strokeWidth="1" />

        {/* Evidence items revealed one by one — clipped to card interior */}
        <g clipPath="url(#rightCardClip)">
          {evidenceItems.map((text, i) => (
            <motion.text
              key={text}
              x="325"
              y={itemYs[i]}
              fill="#10b981"
              className="font-mono text-[10px] font-bold"
              initial={{ opacity: 0 }}
              animate={
                reduceMotion
                  ? { opacity: 1 }
                  : { opacity: [0, 0, 1, 1, 0] }
              }
              transition={{
                repeat: Infinity,
                duration: totalDuration,
                ease: "easeOut",
                times: itemTimes(i),
              }}
            >
              {text}
            </motion.text>
          ))}

          {/* "Verifiable Ground Truth" appears after all items */}
          <motion.text
            x="385"
            y={footerY}
            textAnchor="middle"
            fill="#06b6d4"
            className="font-sans text-[11px] font-bold"
            initial={{ opacity: 0 }}
            animate={
              reduceMotion
                ? { opacity: 1 }
                : { opacity: [0, 0, 1, 1, 0] }
            }
            transition={{
              repeat: Infinity,
              duration: totalDuration,
              ease: "easeOut",
              times: footerTimes(),
            }}
          >
            Verifiable Ground Truth
          </motion.text>
        </g>
      </svg>
    </div>
  );
}

/**
 * 9. Landing Banner Visual (The Complete Intelligence Loop)
 * Revolving outer nodes orbit smoothly around the central DevTwin Intelligence core.
 */
export function LandingBannerVisual({ className }: BannerVisualProps) {
  const reduceMotion = useReducedMotion();

  const nodes = [
    { label: "KNOW", x: 270, y: 37, color: "#06b6d4" },
    { label: "BUILD", x: 350, y: 81, color: "#10b981" },
    { label: "DETECT", x: 350, y: 169, color: "#f59e0b" },
    { label: "LEARN", x: 270, y: 213, color: "#a855f7" },
    { label: "IMPROVE", x: 190, y: 169, color: "#3b82f6" },
    { label: "RE-EVAL", x: 190, y: 81, color: "#06b6d4" },
  ];

  return (
    <div className={cn("relative flex items-center justify-center p-1 select-none", className)}>
      <svg
        viewBox="0 0 540 250"
        className="w-full h-auto max-h-[175px] sm:max-h-[190px] md:max-h-[205px]"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        aria-hidden="true"
      >
        {/* Revolving Orbit Cluster: Dashed ring and 6 outer nodes orbit together */}
        <motion.g
          animate={reduceMotion ? undefined : { rotate: 360 }}
          transition={{ repeat: Infinity, duration: 24, ease: "linear" }}
          style={{ transformOrigin: "270px 125px" }}
        >
          {/* Core Technical Loop Circle */}
          <circle cx="270" cy="125" r="88" className="stroke-cyan-500/30" strokeWidth="2" strokeDasharray="6 4" />

          {/* 6 Core Loop Stages */}
          {nodes.map((node) => (
            <g key={node.label} transform={`translate(${node.x}, ${node.y})`}>
              {/* Counter-rotate inner contents so labels remain upright and perfectly legible */}
              <motion.g
                animate={reduceMotion ? undefined : { rotate: -360 }}
                transition={{ repeat: Infinity, duration: 24, ease: "linear" }}
                style={{ transformOrigin: "0px 0px" }}
              >
                <circle cx="0" cy="0" r="20" className="fill-white dark:fill-slate-900 stroke-slate-300 dark:stroke-slate-700" strokeWidth="2" />
                <circle cx="0" cy="0" r="15" fill={node.color} className="opacity-20" />
                <text x="0" y="4" textAnchor="middle" fill={node.color} className="font-mono text-[8.5px] font-bold">
                  {node.label}
                </text>
              </motion.g>
            </g>
          ))}
        </motion.g>

        {/* Central Core Breathing Ripple */}
        <motion.circle
          cx="270"
          cy="125"
          className="stroke-cyan-500/40"
          strokeWidth="1.5"
          fill="none"
          animate={reduceMotion ? undefined : { r: [32, 54], opacity: [0.6, 0] }}
          transition={{ repeat: Infinity, duration: 2.8, ease: "easeOut" }}
        />

        {/* Central Core Emblem with gentle scale pulse */}
        <motion.g
          animate={reduceMotion ? undefined : { scale: [1, 1.04, 1] }}
          transition={{ repeat: Infinity, duration: 3, ease: "easeInOut" }}
          style={{ transformOrigin: "270px 125px" }}
        >
          <circle cx="270" cy="125" r="32" className="fill-white dark:fill-slate-900 stroke-cyan-500" strokeWidth="2.5" />
          <text x="270" y="122" textAnchor="middle" className="fill-slate-900 dark:fill-slate-100 font-sans text-[11px] font-extrabold">
            DEVTWIN
          </text>
          <text x="270" y="136" textAnchor="middle" className="fill-cyan-700 dark:fill-cyan-400 font-mono text-[8px] font-extrabold">
            INTELLIGENCE
          </text>
        </motion.g>
      </svg>
    </div>
  );
}

