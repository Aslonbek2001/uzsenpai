#!/usr/bin/env python3
"""PostToolUse (Edit|Write): auto-format the file Claude just changed.

- *.py in backend/ or bot/ -> ruff check --fix, then ruff format (via uv, using that app's config)
- *.ts/tsx/js/jsx/css/json in frontend/ -> prettier (only if installed in frontend/node_modules)
Markdown is never reformatted (DESIGN.md / CLAUDE.md tables stay as written).
Missing tools are skipped silently; lint errors ruff can't fix are reported back to Claude (exit 2).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

data = json.load(sys.stdin)
raw = (data.get("tool_input") or {}).get("file_path", "")
if not raw or not Path(raw).exists():
    sys.exit(0)

file = Path(raw).resolve()
parts = file.as_posix().split("/")


def app_root(name: str) -> Path | None:
    if name not in parts:
        return None
    idx = len(parts) - 1 - parts[::-1].index(name)
    root = Path("/".join(parts[: idx + 1]) or "/")
    return root if (root / "pyproject.toml").exists() or (root / "package.json").exists() else None


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=50)
    except (OSError, subprocess.TimeoutExpired):
        return None


if file.suffix == ".py":
    root = app_root("backend") or app_root("bot")
    if root is None or not shutil.which("uv"):
        sys.exit(0)
    res = run(["uv", "run", "--quiet", "ruff", "check", "--fix", str(file)], root)
    run(["uv", "run", "--quiet", "ruff", "format", str(file)], root)
    if res is not None and res.returncode != 0 and res.stdout.strip():
        print(f"ruff found issues it couldn't fix in {file.name}:\n{res.stdout[-3000:]}", file=sys.stderr)
        sys.exit(2)

elif file.suffix in {".ts", ".tsx", ".js", ".jsx", ".css", ".json"}:
    root = app_root("frontend")
    prettier = root / "node_modules" / ".bin" / "prettier" if root else None
    if prettier is not None and prettier.exists():
        run([str(prettier), "--write", "--log-level", "warn", str(file)], root)  # type: ignore[arg-type]

sys.exit(0)
