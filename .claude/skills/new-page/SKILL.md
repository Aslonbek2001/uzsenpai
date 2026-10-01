---
name: new-page
description: Design and build a new frontend page/screen end-to-end with the UzSenpai design system — plan with wireframes for mobile/tablet/desktop, then build with all states, motion and interaction rules, then visually verify. Use for any new route or full-screen redesign.
argument-hint: <route> <what the page is for> [career|visa|learn|hub]
---

Build page: $ARGUMENTS

1. Delegate design + build to the `ui-designer` subagent with: the route, purpose, space (career/visa/learn/hub),
   the API hooks available in `entities/`, and any copy the user gave. Ask it to show its Pass-1 plan
   (wireframes 360/768/1440 + states) in its result.
2. Page structure (Feature-Sliced): `pages/<name>/ui/<Name>Page.tsx` composes widgets/features only;
   route registered lazily in `app/router` with a skeleton fallback the same size as the page.
3. Wrap the page in `data-space="career|visa|learn"` (hub: none) so `--accent` is correct.
4. Data: TanStack Query with `placeholderData: keepPreviousData` for lists; prefetch on link hover/touch.
5. When the subagent is done, run `/ui-audit <route>`; fix Blocker/Major findings.
6. Texts in all four locales (`/translate`), then `make i18n-check && cd frontend && pnpm lint && pnpm typecheck && pnpm test`.
7. Summarise in Uzbek: what was built, screenshots checked, anything left.
