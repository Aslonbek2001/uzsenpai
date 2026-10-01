/**
 * Motion presets for `motion/react`. Use these instead of ad-hoc values.
 * Only transform + opacity. Reduced motion is handled by <MotionConfig reducedMotion="user"> in app/providers.
 */
import type { Transition, Variants } from "motion/react";

export const duration = { press: 0.09, fast: 0.15, base: 0.22, slow: 0.32 } as const;

export const ease = {
  out: [0.22, 1, 0.36, 1],
  in: [0.55, 0, 1, 0.45],
} as const;

export const spring: Transition = { type: "spring", stiffness: 420, damping: 32, mass: 0.9 };

/** Route content: 8px rise + fade. Exit faster than enter. */
export const page: Variants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: duration.base, ease: ease.out } },
  exit: { opacity: 0, transition: { duration: duration.fast, ease: ease.in } },
};

/** Bottom sheet (mobile) — drag-to-dismiss friendly. */
export const sheet: Variants = {
  initial: { y: "100%" },
  animate: { y: 0, transition: spring },
  exit: { y: "100%", transition: { duration: duration.base, ease: ease.in } },
};

/** Dialog / popover. */
export const pop: Variants = {
  initial: { opacity: 0, scale: 0.96 },
  animate: { opacity: 1, scale: 1, transition: { duration: duration.base, ease: ease.out } },
  exit: { opacity: 0, scale: 0.98, transition: { duration: duration.fast, ease: ease.in } },
};

/** List container: stagger only the first 6 children (30ms each). */
export const list: Variants = {
  animate: { transition: { staggerChildren: 0.03, staggerDirection: 1 } },
};
export const listItem = (index: number): Variants => ({
  initial: index < 6 ? { opacity: 0, y: 6 } : { opacity: 1, y: 0 },
  animate: { opacity: 1, y: 0, transition: { duration: duration.base, ease: ease.out } },
});

/** Signature moment: hanko stamp pressing onto a completed card. */
export const hanko: Variants = {
  initial: { opacity: 0, scale: 1.4, rotate: -14 },
  animate: {
    opacity: 1,
    scale: 1,
    rotate: -8,
    transition: { type: "spring", stiffness: 520, damping: 18, mass: 0.7 },
  },
};

/** Tap feedback for motion components (CSS .btn handles plain buttons). */
export const tap = { scale: 0.97, transition: { duration: duration.press } } as const;
