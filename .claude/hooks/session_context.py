#!/usr/bin/env python3
"""SessionStart: give Claude the current git branch and uncommitted changes (plain stdout -> context)."""
import subprocess


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


branch = git("branch", "--show-current")
if branch:
    status = git("status", "--short")
    last = git("log", "-3", "--oneline")
    print(f"Current git branch: {branch}")
    print("Uncommitted changes:\n" + (status or "(none)"))
    if last:
        print("Recent commits:\n" + last)
