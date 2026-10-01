#!/usr/bin/env python3
"""PostToolUse (Edit|Write): flag UI anti-patterns that cause flicker, page jumps, layout shift or a11y bugs.

Runs only for frontend/src/**/*.tsx|.jsx|.css (not generated code). Exit 2 → findings shown to Claude to fix.
"""
import json
import re
import sys
from pathlib import Path

data = json.load(sys.stdin)
raw = (data.get("tool_input") or {}).get("file_path", "")
path = raw.replace("\\", "/")
if "/frontend/src/" not in path or "/generated/" in path or not Path(raw).exists():
    sys.exit(0)
suffix = Path(raw).suffix
if suffix not in {".tsx", ".jsx", ".css"}:
    sys.exit(0)

src = Path(raw).read_text(encoding="utf-8", errors="ignore")
is_token_file = path.endswith("/theme/tokens.css")
findings: list[str] = []


def line_of(pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def mask_attr_expressions(text: str) -> str:
    """Blank out the inside of attribute expressions (`attr={...}`) so `>` in arrows, comparisons or
    generics inside handlers can't end a tag match. Length and newlines are kept, so line numbers stay right."""
    out = list(text)
    i = 0
    while (i := text.find("={", i)) != -1:
        depth, j = 0, i + 1
        while j < len(text):
            ch = text[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        for k in range(i + 2, min(j, len(text))):
            if out[k] != "\n":
                out[k] = " "
        i = j
    return "".join(out)


def check(pattern: str, message: str, flags: int = 0, text: str | None = None) -> None:
    for m in re.finditer(pattern, text if text is not None else src, flags):
        findings.append(f"L{line_of(m.start())}: {message}")


if suffix in {".tsx", ".jsx"}:
    jsx = mask_attr_expressions(src)
    check(r"""href=\{?["']#["']\}?""", 'href="#" jumps to the top of the page — use <button type="button"> for actions.')
    check(r"<button(?![^>]*\btype=)[^>]*>", "<button> without explicit type — defaults to submit inside forms (reload / jump).", re.S, jsx)
    check(r"<(div|span|li|img)\b[^>]*\bonClick=", "Clickable non-interactive element — use <button type=\"button\"> (keyboard + a11y).", re.S, jsx)
    check(r"-\[#[0-9a-fA-F]{3,8}\]", "Raw hex colour in className — use a token (bg-accent, text-ink, border-line…).")
    check(r"""(color|background(Color)?|borderColor)\s*:\s*["']#[0-9a-fA-F]{3,8}["']""", "Raw hex colour in style — use CSS variables from tokens.css.")
    check(r"window\.scrollTo\(\s*0\s*,\s*0\s*\)", "Manual scroll-to-top — use <ScrollRestoration/> / preventScrollReset instead.")
    check(r"\bh-screen\b|\bmin-h-screen\b", "100vh jumps on mobile when the URL bar hides — use h-dvh / min-h-dvh.")
    check(r"\btransition-all\b", "transition-all animates layout props and causes flicker — transition specific properties.")
    for m in re.finditer(r"\boutline-none\b", src):
        line = src[src.rfind("\n", 0, m.start()) + 1 : src.find("\n", m.start())]
        if "focus-visible" not in line:
            findings.append(f"L{line_of(m.start())}: outline-none without a focus-visible replacement — keyboard users lose focus.")
    check(r"<img\b(?![^>]*\b(width|aspect|className=\"[^\"]*aspect-))[^>]*>", "<img> without width/height or aspect ratio — causes layout shift.", re.S, jsx)
    # 4 languages: no hardcoded user-facing text (tests/stories excluded)
    if not re.search(r"\.(test|spec|stories)\.[jt]sx$", path):
        letters = r"[A-Za-zА-Яа-яЁёʻ぀-ヿ一-鿿]"
        check(rf"[>}}]\s*([^<>{{}}\n;=()&|]*{letters}{{2}}[^<>{{}}\n;=()&|]*)\s*</", "Hardcoded UI text — use t('…') with keys in all 4 locales (uz, ru, en, ja).", 0, jsx)
        check(rf"\b(aria-label|placeholder|title|alt)=\"[^\"{{]*{letters}{{2}}", "Hardcoded attribute text — use {t('…')} (4 locales).", 0, jsx)

if suffix == ".css" and not is_token_file:
    check(r"transition\s*:\s*all\b", "transition: all causes flicker/jank — list specific properties (transform, opacity, colors).")
    check(r"(?<![\w-])100vh\b", "100vh jumps on mobile — use 100dvh / 100svh.")
    check(r"[\w-]+\s*:\s*[^;{}]*(?<!url\()#[0-9a-fA-F]{3,8}\b(?=[^{}]*[;}])", "Raw hex colour in a declaration — use tokens from tokens.css.")
    check(r"transition[^;]*\b(width|height|top|left|margin|padding)\b", "Animating layout properties — animate transform/opacity instead.")
    if ":hover" in src and "hover: hover" not in src and "hover:hover" not in src:
        findings.append("File uses :hover without @media (hover: hover) — hover sticks on touch screens.")
    check(r"outline\s*:\s*(none|0)\s*;", "outline removed — make sure a :focus-visible style replaces it.")

if findings:
    print(f"UI lint ({Path(raw).name}) — fix per frontend/DESIGN.md §7:", file=sys.stderr)
    for f in findings[:20]:
        print(f"  - {f}", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
