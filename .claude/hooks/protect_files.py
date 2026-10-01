#!/usr/bin/env python3
"""PreToolUse (Edit|Write|Read): block reading/editing .env secrets; block edits to secrets, lock files, generated code and migrations merged into main.
Note: only Edit/Write are guarded — shell writes are covered by permissions, not this hook.

Exit 2 = block; stderr is shown to Claude as the reason.
"""
import json
import subprocess
import sys
from pathlib import Path

data = json.load(sys.stdin)
raw = (data.get("tool_input") or {}).get("file_path", "")
path = raw.replace("\\", "/")
name = Path(path).name


def block(reason: str) -> None:
    print(reason, file=sys.stderr)
    sys.exit(2)


tool = data.get("tool_name", "")
is_secret = name == ".env" or (name.startswith(".env.") and name != ".env.example")

# Secrets: never read or edited by Claude (any .env* except .env.example)
if is_secret:
    if tool == "Read":
        block(f"{name}: secret file — not readable by Claude. Use .env.example to see which variables exist.")
    block(f"{name}: secret files are edited by the user only. Update .env.example instead and tell the user.")

if tool == "Read":
    sys.exit(0)  # everything below guards writes only

# Lock files — change them via the package manager, not by hand
if name in {"uv.lock", "pnpm-lock.yaml", "package-lock.json", "yarn.lock"}:
    block(f"{name} is managed by the package manager. Use `uv add` / `pnpm add` instead.")

# Generated API client
if "/frontend/src/shared/api/generated/" in path:
    block("Generated API client — don't edit by hand. Change the backend schema and run `make api-types`.")

# Alembic: new or unmerged migrations OK; a migration that already exists on main must not change
if "/backend/migrations/versions/" in path and Path(raw).exists():
    def git(*args: str) -> subprocess.CompletedProcess[str] | None:
        try:
            return subprocess.run(["git", *args], capture_output=True, text=True, cwd=Path(raw).parent, timeout=5)
        except Exception:
            return None

    top = git("rev-parse", "--show-toplevel")
    if top is not None and top.returncode == 0:
        rel = Path(raw).resolve().relative_to(Path(top.stdout.strip()).resolve()).as_posix()
        for base in ("origin/main", "main"):
            on_main = git("cat-file", "-e", f"{base}:{rel}")
            if on_main is not None and on_main.returncode == 0:
                block("This migration is already merged into main. Create a new revision instead of editing it.")

sys.exit(0)
