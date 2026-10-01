---
paths:
  - "frontend/src/**/*.tsx"
  - "frontend/src/**/*.css"
---

# UI rules (full spec: frontend/DESIGN.md — read it before designing a new screen)

Checklist for every component/page you touch:

- [ ] Colours, radii, spacing, durations come from tokens (`tokens.css` / Tailwind theme) — no raw hex, no magic ms.
- [ ] Uses the right space accent (`--accent`) — career = fuji purple, visa = wakatake green, learn = ai indigo, hub = ink.
- [ ] Mobile 360px first, then 768 and 1440. No horizontal scroll. Touch targets ≥ 44px.
- [ ] All states designed: loading (skeleton same size), empty (with action), error (with retry), success.
- [ ] Press feedback via transform; hover only for `(hover: hover)`; `focus-visible` ring present.
- [ ] No `href="#"`, every `<button>` has `type`, filters/tabs use `preventScrollReset`.
- [ ] No layout shift: fixed-size loading buttons, image aspect ratios, `keepPreviousData` on paginated queries.
- [ ] Only `transform`/`opacity` animated, presets from `motion.ts`, `prefers-reduced-motion` respected.
- [ ] Use primitives from `shared/ui` (`Button` exists; create `Sheet`, `Dialog`, `Skeleton`, `Ruby` there the first
      time they're needed, following Button's interaction rules) — don't restyle raw elements per page.
- [ ] Japanese text wrapped with `lang="ja"`; furigana via `<Ruby>`; kanji study glyphs use the `font-study` class.
- [ ] All strings via `t()`; check the layout with long Russian strings too.

The `ui_lint` hook flags common violations after each edit — fix them, don't suppress them.
After building a screen, run `/ui-audit <route>` (screenshots at 3 widths) before calling it done.
