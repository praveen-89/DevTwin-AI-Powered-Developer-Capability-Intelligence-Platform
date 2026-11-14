"use client";

/**
 * DevTwin — Animated Number
 *
 * Tweens a numeric value between renders instead of snapping directly to
 * the new figure. Used for capability score / confidence displays so that
 * a score update (e.g. after a new analysis run or re-run) is visibly
 * legible as a change rather than an instant replacement.
 *
 * Presentation-only: does not alter the underlying value, only how it is
 * rendered. Respects `prefers-reduced-motion` — when reduced motion is
 * requested, the new value is shown immediately with no tween.
 */

import { useEffect, useRef, useState } from "react";
import { animate, useReducedMotion } from "motion/react";

interface AnimatedNumberProps {
  /** The current numeric value to display (already in display units, e.g. 0.0–1.0). */
  value: number;
  /** Formats the (possibly intermediate, tweened) numeric value into display text. */
  format: (value: number) => string;
  className?: string;
  durationSec?: number;
}

export function AnimatedNumber({
  value,
  format,
  className,
  durationSec = 0.6,
}: AnimatedNumberProps) {
  const reduceMotion = useReducedMotion();
  const [display, setDisplay] = useState(value);
  const prevRef = useRef(value);

  useEffect(() => {
    if (reduceMotion) {
      setDisplay(value);
      prevRef.current = value;
      return;
    }

    const from = prevRef.current;
    if (from === value) {
      setDisplay(value);
      return;
    }

    const controls = animate(from, value, {
      duration: durationSec,
      ease: "easeOut",
      onUpdate: (latest) => setDisplay(latest),
    });
    prevRef.current = value;

    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value, reduceMotion, durationSec]);

  return <span className={className}>{format(display)}</span>;
}
