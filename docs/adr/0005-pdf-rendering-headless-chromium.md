# 0005. PDF rendering with headless Chromium (Playwright)

- Status: accepted
- Date: 2026-10-02

## Context
The resume module exports 履歴書, 職務経歴書 and an English CV as A4 PDFs with embedded Japanese fonts.
JIS-style 履歴書 is a dense grid layout; output must match what the user previewed in the browser.

## Options
1. **WeasyPrint** — pure Python, light. Cons: its own CSS engine; layouts can differ from the browser preview.
2. **Headless Chromium via Playwright (Python)** — same engine as the preview, full modern CSS. Cons: heavy
   worker image (~1 GB), more RAM per render.
3. **Gotenberg** — Chromium as a separate HTTP service. Cons: one more container to run and secure.

## Decision
Playwright for Python driving headless Chromium inside the Taskiq worker. Pixel-faithful output matters more
than image size for a paid resume product.

## Consequences
- Worker Docker image installs Chromium and the self-hosted Japanese fonts; the API image stays slim.
- One browser instance per worker process, a new page per job, concurrency limited to protect RAM.
- Templates are rendered from trusted HTML only (no user-supplied HTML, JavaScript disabled, no network
  access during render) to avoid SSRF and script injection.
- Revisit (WeasyPrint) if memory on the VPS becomes the bottleneck.
