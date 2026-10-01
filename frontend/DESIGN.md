# UzSenpai Design System — "Sumi & Ai"

Source of truth for how UzSenpai looks, moves and feels. Every UI change follows this file.
Tokens live in `src/shared/ui/theme/tokens.css`, motion presets in `src/shared/ui/theme/motion.ts`.

## 1. Who we design for

UzSenpai is a **paid services platform**; learning Japanese is one section, not the whole product.

| Audience | Situation | What the UI must do |
|---|---|---|
| **Job seekers** (Uzbekistan → Japan, 20–40) | Need a Japanese resume and to pass an interview with a Japanese employer; anxious, not sure what's expected | Guide step by step, show the finished document early, make paying feel safe and worth it |
| **Migrants in Japan** (workers, students, Tokutei Ginō) | Visa deadlines, city hall, insurance; tired, prepaid data, need an answer *now* | Calm, plain language, fast on weak networks, sources with dates, quick path to a human expert |
| **Learners** | Studying for JLPT / work, in short phone sessions | Satisfying 5-minute sessions, visible progress, big readable kana/kanji |

Primary device is a mid-range Android phone. Design mobile-first, then tablet, then desktop.

### Information architecture

Bottom tabs (mobile) / sidebar (desktop), in this order:
**Asosiy** (hub: next steps, active orders, deadlines) · **Karyera** (resume, interview, expert review) ·
**Viza** (visa info, checklists, life guides, consultations) · **Oʻrganish** (learning) · **Profil**
(subscription, purchases, documents).

## 2. Design language

Inspired by Japanese stationery and printed textbooks, not by "anime" clichés (no cherry blossoms
falling, no torii gates as decoration, no fake brush fonts for UI text).

- **Sumi (墨)** — ink. Text and structure are deep blue-black ink, never pure #000. The hub uses sumi.
- **Fuji (藤)** — wisteria purple. The Career space (resume, interview): professional, confident.
- **Wakatake (若竹)** — young bamboo green. The Visa & life space: calm, reassuring.
- **Ai (藍)** — indigo, the colour of Japanese workwear and school uniforms. The Learning space.
- **Yamabuki (山吹)** — golden yellow. Streaks, XP, highlights. Used rarely, and only as a fill —
  text in this family uses `--yamabuki-ink` on `--yamabuki-soft` (yellow text on white fails contrast).
- **Shu (朱)** — vermilion seal ink. Reserved for the **hanko stamp** (achievements, completed lessons) and
  destructive actions. Never as a general accent.
- **Genkō yōshi (原稿用紙)** — the squared manuscript paper. A faint grid used as the canvas for kanji
  practice, writing exercises and the learning hero. This is the one signature motif — don't spread it elsewhere.

**Signature moment:** when something important is finished — a resume is ready, an order is delivered, a
lesson or test is passed — a vermilion hanko stamp presses onto the card (scale 1.4→1, slight rotate,
1 small "ink spread" ring, haptic `navigator.vibrate(12)` on Android). Stamp text matches the event:
完成 (resume ready), 合格 (test passed), 済 (order completed). This is the only celebratory animation in the
product — no confetti.

Everything else stays quiet: generous whitespace, clear hierarchy, few borders, no gradient washes, no
identical card grids with the same shadow. Hierarchy through type size, weight and spacing first,
colour second, borders/shadows last.

## 3. Colour tokens (semantic — always use these, never raw hex)

| Token | Light | Dark | Use |
|---|---|---|---|
| `--bg` | #F3F5F8 | #0E1420 | App background (cool paper, not cream) |
| `--surface` | #FFFFFF | #161E2E | Cards, sheets |
| `--surface-sunken` | #E8ECF2 | #0A0F18 | Inputs, wells |
| `--ink` | #17202F | #E6EAF1 | Primary text |
| `--ink-muted` | #5A6578 | #9AA5B8 | Secondary text (≥4.5:1 on bg) |
| `--ai` | #233F73 | #8FAEE6 | Learning primary |
| `--fuji` | #5B3F8C | #B9A2E3 | Career primary |
| `--wakatake` | #2E7D62 | #6CC9A6 | Visa & life primary |
| `--yamabuki` | #E3A21A | #F2C14E | Streak / XP fills (never as text colour) |
| `--yamabuki-soft` / `--yamabuki-ink` | #FDF3DC / #8A5A00 | #3A2F12 / #F2C14E | "Premium" label, days-left warning text |
| `--line` / `--line-strong` | #D6DCE5 / #737E92 | #263247 / #717E99 | Dividers / input and control borders (≥ 3:1) |
| `--shu` | #C8382B | #F07466 | Hanko, destructive, errors |

Each space sets `--accent` to its primary (`[data-space="career"]` → fuji, `[data-space="visa"]` → wakatake,
`[data-space="learn"]` → ai; the hub has no space and uses sumi/ink), so shared components use `--accent`
and automatically take the right colour.
Dark mode ("Yoru") is first-class: follows the system, with a manual toggle.

## 4. Typography

| Role | Font | Notes |
|---|---|---|
| UI text (uz, en Latin; ru Cyrillic) | **Onest** | Clear at small sizes, full Cyrillic |
| Japanese UI / sentences | **Zen Kaku Gothic New** | Applied via `:lang(ja)` — when the UI locale is `ja` the whole app uses it; line-height 1.8 |
| Kanji / kana study display | **Klee One** | Textbook handwriting style — shows real stroke shapes, which matters for learners |
| (all fonts) | self-hosted woff2 in `public/fonts/`, `font-display: swap`, metric-matched fallback | no third-party font requests |
| Numbers (scores, timers) | Onest with `font-variant-numeric: tabular-nums` | No jumping digits |

Scale (rem): 0.8125 · 0.9375 · **1 (16px body)** · 1.125 · 1.375 · 1.75 · 2.25 · 3 (display kanji: 4–6).
Body never below 16px (also prevents iOS zoom on inputs). Line length ≤ 70ch.
Japanese: `line-break: strict; word-break: auto-phrase` (graceful fallback), furigana via `<ruby>`, with a
global "Show furigana" toggle. Sentence case everywhere; no ALL-CAPS labels.

## 5. Layout & responsive

Breakpoints: `sm 640` · `md 768` · `lg 1024` · `xl 1280`. Required checks at **360, 768, 1440** px (what `/ui-audit` runs); spot-check 390 and 1024.

| | Mobile < 768 | Tablet 768–1023 | Desktop ≥ 1024 |
|---|---|---|---|
| Navigation | Bottom tab bar (4–5 items), safe-area aware | Left nav rail (icons + labels) | Left sidebar, collapsible |
| Content | Single column, 16px gutters | 1–2 columns, 24px gutters | Max 1200px, 12-col grid, 32px gutters |
| Secondary panels | Bottom sheet | Side sheet | Inline right column |
| Lesson player | Full screen, thumb-zone controls at bottom | Centered card | Centered card + side notes |

- Components respond to their container (`@container`), pages to the viewport.
- Use `100dvh`/`svh`, never `100vh`. Respect `env(safe-area-inset-*)`.
- Primary actions sit in the bottom thumb zone on mobile.
- Touch targets ≥ 44×44px with ≥ 8px between them.

## 6. Motion

Motion explains what changed. It never blocks input and never decorates.

| Token | Value | Use |
|---|---|---|
| `--dur-press` | 90ms | Button/card press feedback |
| `--dur-fast` | 150ms | Hover, toggles, colour changes |
| `--dur-base` | 220ms | Dropdowns, tooltips, tab indicator |
| `--dur-slow` | 320ms | Sheets, dialogs, page transitions |
| `--ease-out` | cubic-bezier(0.22, 1, 0.36, 1) | Entering |
| `--ease-in` | cubic-bezier(0.55, 0, 1, 0.45) | Leaving (≈70% of enter duration) |
| `spring` (motion.ts) | stiffness 420, damping 32, mass 0.9 | Sheets, drag |
| `hanko` (motion.ts) | stiffness 520, damping 18, mass 0.7 | The stamp only (a deliberate overshoot) |

- Animate only `transform` and `opacity` (and `clip-path`). Never `width/height/top/left/margin`.
- Page transition: 8px slide + fade, 220ms. Never re-animate on back navigation.
- Lists: stagger max 6 items × 30ms, then the rest appear together.
- `prefers-reduced-motion`: replace movement with opacity fades, keep durations ≤ 150ms, no hanko bounce.

## 7. Interaction quality — the "no flicker, no jump" rules

These are the bugs that make an app feel cheap. Every component and page must pass them.

**Press & click**
1. Every tap gives visible feedback within 100ms: `:active` → `scale(0.97)` via transform.
2. `-webkit-tap-highlight-color: transparent` + our own pressed state (no grey Android flash).
3. Hover styles only under `@media (hover: hover)` (Tailwind v4 `hover:` already does this). Otherwise hover
   "sticks" on touch screens and looks like flicker.
4. Loading buttons keep their exact size: label becomes `visibility: hidden`, spinner overlays it. Never swap
   text for a spinner (width jumps). Block double-submit while loading.
5. Disabled ≠ loading: loading keeps full opacity; only real disabled dims.

**No page jumps**
6. Never `<a href="#">`. Actions are `<button type="button">`; navigation is `<Link>`.
7. Every `<button>` has an explicit `type` — a default `submit` inside a form reloads/jumps the page.
8. Tabs, filters, pagination, search params → React Router `preventScrollReset`. Real navigations use
   `<ScrollRestoration />`; back navigation restores the previous position.
9. Opening dialogs/sheets must not shift the page: use Radix primitives (they lock scroll and compensate
   the scrollbar) and `scrollbar-gutter: stable` on `html`.

**No layout shift (CLS ≈ 0)**
10. Skeletons have the exact size of the content they replace.
11. Images/video have `width`/`height` or `aspect-ratio`.
12. Refetch/pagination keeps previous data (`placeholderData: keepPreviousData`) — lists never collapse to
    empty and back.
13. Fonts: `font-display: swap` with metric-matched fallbacks; numbers `tabular-nums`.
14. Toasts and banners overlay; they never push content down.

**Feels instant**
15. Optimistic UI for SRS answers, favourites, checklist ticks, settings toggles — roll back on error.
16. Prefetch the next lesson and on link hover/touchstart.
17. Spinners only after 300ms delay; under that, show nothing (avoids flashing spinners).

**Forms (mobile)**
18. Inputs ≥ 16px font, correct `inputMode`/`autocomplete`/`enterKeyHint`, labels always visible.
19. Errors inline under the field, focus moves to the first error, form keeps the user's input.
20. Sticky bottom actions stay above the on-screen keyboard (`visualViewport`).

## 8. Accessibility (floor, not a feature)

WCAG 2.2 AA: contrast ≥ 4.5:1 text / 3:1 UI, visible `:focus-visible` ring (2px `--accent`, 2px offset),
full keyboard support, semantic elements (no clickable `div`s), `lang` attribute on Japanese text so screen
readers pronounce it correctly, audio for kana/kanji has a visible play control.

## 9. Domain patterns

**Hub (Asosiy)**
- Answers "what should I do next?": one primary next step (e.g. finish resume, interview tomorrow),
  active orders with status, upcoming deadlines (visa expiry), then the service catalogue.
- Services are shown by the problem they solve ("Yaponcha rezyume tayyorlash"), not by product names.

**Career space (`data-space="career"`)**
- Resume builder: step-by-step (Shaxsiy → Ta’lim → Ish tajribasi → Malaka → 志望動機 → 自己PR), autosave,
  live A4 preview of the real 履歴書 layout, side-by-side uz input → Japanese output with "AI tarjima" that the
  user reviews. Completion = 完成 hanko on the preview.
- Mock interview: chat-like, interviewer bubble in Japanese with optional furigana/translation toggle,
  answer by voice or text, timer per question; report with scores per area and better sample answers.
- Expert review upsell appears only after the user has a draft (value first).

**Paid services — trust patterns (all spaces)**
- Price card: what you get (3–5 concrete bullets), delivery time, price in the checkout currency (soʻm for UZS), refund terms — before the pay
  button. One primary action per card.
- Free vs paid is marked with a small "Premium" label (`--yamabuki-ink` on `--yamabuki-soft`), never by greying out content the user
  can't understand.
- Checkout as a bottom sheet (mobile) / dialog (desktop): order summary, payment method (Rahmat page:
  cards, Click / Payme / Uzum),
  total, one pay button that keeps its size while processing. After paying: receipt + clear next step.
- Orders screen: status timeline (Qabul qilindi → Toʻlandi → Ishlanmoqda → Tayyor), expert's name and
  photo, deadline, deliverables to download, chat with the expert.
- Never fake urgency (countdown timers, "only 2 left"), never pre-ticked add-ons, cancellation as easy as purchase.

**Visa & life space (`data-space="visa"`)**
- "My status" card: residence status, expiry date, days left (`--yamabuki-ink` under 90 days, `--shu` under 30).
- Visa info pages: plain language, official source + "updated on" date, outdated warning, and a
  "Mutaxassisdan soʻrash" (paid consultation) action at the end — information is not legal advice.
- Step-by-step checklists (residence card, My Number, health insurance, bank, pension) with progress saved.
- Emergency card always reachable in ≤ 2 taps: 110, 119, #7119, embassy; works offline.
- "Xodimga koʻrsatish" phrase cards: Japanese large, full screen, high contrast.
- Guides cached for offline (PWA), images lazy and compressed.

**Learning space (`data-space="learn"`)**
- Kanji card: large Klee One glyph on the genkō yōshi grid, reading (on/kun), meaning in the user's language (uz/ru/en; ja UI gets a Japanese gloss), stroke order
  animation (play/pause, replay), audio.
- SRS review: one card at a time, answer buttons in thumb zone, keyboard shortcuts 1–4 on desktop,
  swipe on mobile, optimistic, next card prefetched.
- Progress: JLPT level path (N5→N1) as a vertical route; streak in yamabuki; completion = hanko stamp.

## 10. Four languages in the UI (uz · ru · en · ja)

- `<html lang>` follows the UI locale; Japanese fragments inside other languages still get `lang="ja"`.
- Language picker: first-run screen, Profil › Til, and the desktop header. Show each language in its own name
  (Oʻzbekcha, Русский, English, 日本語) — never flags.
- Design for the longest string: Russian is usually ~30% longer than Uzbek/English, Japanese is shorter but
  needs more line-height. Buttons and tabs must not truncate or wrap awkwardly in any of the four —
  `/ui-audit` checks every screen in ru and ja too.
- Dates, numbers, money via `Intl`: `26-dekabr, 2026` (uz), `26 декабря 2026 г.` (ru), `December 26, 2026` (en),
  `2026年12月26日` (ja). Money via `fmt.money(amount_minor, currency, locale)`: UZS → `150 000 soʻm`, `150 000 сум`, `150,000 UZS`,
  `150,000 スム`; international prices in their own currency (`$12.00`, `￥1,200`) — never converted on the client.
- Tab bar labels are short in every language (≤ 10 characters); if not, use a shorter synonym, not ellipsis.

## 11. Copy

Write the Uzbek text first, then ru/en/ja with the same meaning and tone (Japanese: polite です・ます).
Write for the user, in their language: plain verbs, sentence case, no jargon. A button says exactly what
happens ("Darsni boshlash", not "Yuborish"); the same action keeps the same name in the toast.
Errors say what happened and how to fix it. Empty states invite the next action.
