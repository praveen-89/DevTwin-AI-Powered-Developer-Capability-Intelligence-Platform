"use client";

/**
 * DevTwin — Stagger Item
 *
 * A small, reusable mount-entrance wrapper used to give lists of cards /
 * rows (capability cards, evidence rows, etc.) a consistent staggered
 * entrance animation across pages. Delay is derived from the item's index
 * and capped so long lists don't produce an unreasonably long wait for
 * items near the bottom.
 *
 * Respects `prefers-reduced-motion`: when reduced motion is requested, the
 * item renders as a plain (static) element with no animation at all.
 */

import { motion, useReducedMotion } from "motion/react";
import type { ReactNode } from "react";

interface StaggerItemProps {
  children: ReactNode;
  index?: number;
  className?: string;
  /** Underlying element tag — defaults to "div". */
  as?: "div" | "li" | "tr";
  /** Caps the stagger delay multiplier so very long lists don't lag. */
  maxStaggerIndex?: number;
}

const STAGGER_STEP_SEC = 0.045;
const ENTRANCE_DURATION_SEC = 0.35;

export function StaggerItem({
  children,
  index = 0,
  className,
  as = "div",
  maxStaggerIndex = 12,
}: StaggerItemProps) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    if (as === "tr") return <tr className={className}>{children}</tr>;
    if (as === "li") return <li className={className}>{children}</li>;
    return <div className={className}>{children}</div>;
  }

  const delay = Math.min(index, maxStaggerIndex) * STAGGER_STEP_SEC;
  const transition = { duration: ENTRANCE_DURATION_SEC, delay, ease: "easeOut" as const };

  if (as === "tr") {
    return (
      <motion.tr
        className={className}
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={transition}
      >
        {children}
      </motion.tr>
    );
  }

  if (as === "li") {
    return (
      <motion.li
        className={className}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={transition}
      >
        {children}
      </motion.li>
    );
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={transition}
    >
      {children}
    </motion.div>
  );
}
