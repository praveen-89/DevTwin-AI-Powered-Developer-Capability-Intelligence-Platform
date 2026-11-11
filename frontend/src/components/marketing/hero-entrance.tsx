"use client";

/**
 * DevTwin Marketing — Hero Entrance
 *
 * A single, understated entrance animation for the landing hero. Respects
 * `prefers-reduced-motion` by rendering the content with no animation at
 * all when the visitor has requested it.
 */

import { motion, useReducedMotion } from "motion/react";

export function HeroEntrance({ children }: { children: React.ReactNode }) {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) {
    return <>{children}</>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6, ease: "easeOut" }}
    >
      {children}
    </motion.div>
  );
}
