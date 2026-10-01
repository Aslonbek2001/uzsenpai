#!/usr/bin/env python3
"""PostToolUse (Edit|Write): keep files small enough to read and review.

Limits (lines): Python 400 (tests 600), TS/TSX/JS/JSX 300 (tests 500). Generated code and migrations are exempt.
Over the limit → exit 2, Claude must split the file by responsibility before continuing.
"""
import json
import sys
from pathlib import Path

data = json.load(sys.stdin)
raw = (data.get("tool_input") or {}).get("file_path", "")
path = raw.replace("\\", "/")
p = Path(raw)
if not raw or not p.exists() or "/.claude/" in path:
    sys.exit(0)
if any(seg in path for seg in ("/migrations/", "/generated/", "/node_modules/", "/locales/")):
    sys.exit(0)

is_test = "/tests/" in path or p.name.startswith("test_") or ".test." in p.name or ".spec." in p.name
ts_limit = 500 if is_test else 300
limits = {".py": 600 if is_test else 400, **dict.fromkeys((".ts", ".tsx", ".js", ".jsx", ".mjs"), ts_limit)}
limit = limits.get(p.suffix)
if limit is None:
    sys.exit(0)

lines = sum(1 for _ in p.open(encoding="utf-8", errors="ignore"))
if lines <= limit:
    sys.exit(0)

hints = {
    ".py": "Backend: one resource per routers/<resource>.py, one use-case group per services/<name>_service.py, "
    "one aggregate per repositories/ and models/ file, pure rules in domain/. Bot: handlers/<feature>/ package "
    "(one file per step). Split by responsibility, not by line count.",
    ".ts": "Move helpers to lib/, API calls to api/, state to model/ inside the same FSD slice.",
    ".tsx": "Extract sub-components into the slice's ui/ folder, hooks into model/, keep one component per file.",
}
hint = hints.get(p.suffix, hints[".ts"] if p.suffix in (".js", ".mjs") else hints[".tsx"])
print(f"{p.name} has {lines} lines (limit {limit}). Split it now. {hint}", file=sys.stderr)
sys.exit(2)
