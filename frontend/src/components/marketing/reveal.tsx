"use client";

/**
 * DevTwin Marketing — Scroll Reveal
 *
 * A tasteful, staggered scroll-triggered reveal used across the marketing
 * site. Respects `prefers-reduced-motion`: when the visitor has asked for
 * reduced motion, content appears immediately with no transform/opacity
 * animation at all (handled by `motion`'s `useReducedMotion`).
 */

import { motion, useReducedMotion } from "motion/react";

interface RevealProps {
  children: React.ReactNode;
  className?: string;
  /** Stagger delay in seconds, intended for sequential siblings. */
  delay?: number;
  /** Vertical offset (px) the content animates in from. */
  y?: number;
}

export function Reveal({ children, className, delay = 0, y = 16 }: RevealProps) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <div className={className}>{children}</div>;
  }

  return (
    <motion.div
      className={className}
      initial={{ opacity: 0, y }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.5, delay, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
