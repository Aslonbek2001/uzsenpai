---
name: ui-audit
description: Visually test a route in a real browser at mobile, tablet and desktop widths — screenshots, click-through, layout-shift measurement, flicker and scroll-jump detection — and fix what's broken. Use after building or changing UI, or when the user says the UI looks bad, flickers or jumps.
argument-hint: <route, e.g. /learn/kanji> [flow to click through]
---

Audit: $ARGUMENTS

1. Make sure the frontend dev server is running (`cd frontend && pnpm dev` in the background) and the backend
   too if the page needs data.
2. Delegate to the `ux-reviewer` subagent with the route(s) and the flow to click through.
3. Fix every Blocker and Major finding yourself, following `frontend/DESIGN.md`. Group fixes into shared
   components when the same problem appears on several pages (e.g. fix it in `shared/ui`, not per page).
4. Ask `ux-reviewer` to re-check only the fixed items.
5. Report in Uzbek: findings, what you fixed, remaining Minor items.
