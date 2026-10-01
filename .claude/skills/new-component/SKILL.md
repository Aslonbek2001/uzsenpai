---
name: new-component
description: Create a reusable UI component in frontend/src/shared/ui (or an entity/feature UI) with all interaction states, tokens, motion, a11y and responsive behaviour built in. Use when a new button-like, card, input, sheet, list item or other visual building block is needed.
argument-hint: <ComponentName> <what it does> [shared|entity|feature]
---

Create component: $ARGUMENTS

1. Search `src/shared/ui/` first — extend an existing component instead of creating a near-duplicate.
2. Read `frontend/DESIGN.md` §3–§8 and `shared/ui/button/Button.tsx` (the interaction reference).
3. Build with:
   - props typed with `type`, `ref` as a prop (React 19), named export, `className` passthrough via `cn()`;
   - variants/sizes as props, styles from tokens only;
   - all states: default, hover (`@media (hover:hover)` only), pressed (transform scale), focus-visible,
     disabled, loading (no size change), error, selected — whichever apply;
   - interactive parts are real `<button type="button">` / `<a>` / Radix primitives; ≥ 44px touch target;
   - motion only from `motion.ts`; respects reduced motion;
   - container queries for internal layout if it will be used in both narrow and wide places.
4. Export it from the slice `index.ts`.
5. Add a vitest + Testing Library test: renders, keyboard activation, disabled/loading behaviour.
6. No hardcoded text: labels come in as props or via `t()`; check it with the longest (ru) and ja strings.
7. If there's a demo/route to see it, run `/ui-audit` on it; otherwise describe how it looks at 360 and 1440.
