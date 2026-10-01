---
name: ui-polish
description: Take an existing screen that works but looks plain or feels cheap and raise it to the UzSenpai design standard — hierarchy, spacing, typography, responsive layout, micro-interactions, states and motion — without changing behaviour. Use when the user says a page looks "oddiy", "sodda", ugly, or not like the design.
argument-hint: <route or component path>
---

Polish: $ARGUMENTS

1. Run `/ui-audit` on it first to get a baseline (screenshots at 360/768/1440 + findings).
2. Ask `ui-designer` for a critique against `frontend/DESIGN.md`: hierarchy, spacing rhythm, type scale,
   accent usage (career/visa/learn/hub), generic-template smells, missing states, motion opportunities that explain
   change (not decoration). It returns a prioritized change list.
3. Apply changes in order of visual impact. Don't change data flow or API usage.
4. Re-run `/ui-audit`. Show before/after screenshots side by side in your summary (Uzbek).
