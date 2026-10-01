#!/usr/bin/env python3
"""Check that every UI string exists in all four languages (uz, ru, en, ja).

Frontend: frontend/src/shared/i18n/locales/<lang>/<namespace>.json  (i18next JSON v4, nested keys allowed)
Bot:      bot/locales/<lang>/LC_MESSAGES/messages.po                 (gettext)

Exit 1 when a key is missing, empty, or lacks the plural forms its language needs.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

LANGS = ("uz", "ru", "en", "ja")
PLURAL_SUFFIXES = ("_zero", "_one", "_two", "_few", "_many", "_other")
REQUIRED_PLURALS = {"uz": {"one", "other"}, "en": {"one", "other"}, "ru": {"one", "few", "many", "other"}, "ja": {"other"}}
ROOT = Path(__file__).resolve().parent.parent
problems: list[str] = []


def flatten(obj: dict, prefix: str = "") -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in obj.items():
        key = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            out.update(flatten(v, key))
        else:
            out[key] = v if isinstance(v, str) else json.dumps(v)
    return out


def split_plural(key: str) -> tuple[str, str | None]:
    for suf in PLURAL_SUFFIXES:
        if key.endswith(suf):
            return key[: -len(suf)], suf[1:]
    return key, None


def check_frontend() -> None:
    base = ROOT / "frontend/src/shared/i18n/locales"
    if not base.exists():
        print("i18n: frontend locales not created yet — skipped")
        return
    namespaces = sorted({p.stem for lang in LANGS for p in (base / lang).glob("*.json")})
    for ns in namespaces:
        per_lang: dict[str, dict[str, str]] = {}
        for lang in LANGS:
            f = base / lang / f"{ns}.json"
            if not f.exists():
                problems.append(f"frontend: {lang}/{ns}.json is missing")
                per_lang[lang] = {}
                continue
            try:
                per_lang[lang] = flatten(json.loads(f.read_text(encoding="utf-8")))
            except json.JSONDecodeError as e:
                problems.append(f"frontend: {lang}/{ns}.json is not valid JSON ({e})")
                per_lang[lang] = {}
        bases: dict[str, dict[str, set[str]]] = {lang: {} for lang in LANGS}
        for lang, keys in per_lang.items():
            for key, value in keys.items():
                b, form = split_plural(key)
                bases[lang].setdefault(b, set())
                if form:
                    bases[lang][b].add(form)
                if not str(value).strip():
                    problems.append(f"frontend: {lang}/{ns}: '{key}' is empty")
        all_keys = set().union(*(set(b) for b in bases.values()))
        for key in sorted(all_keys):
            plural = any(bases[lang].get(key) for lang in LANGS)
            for lang in LANGS:
                if key not in bases[lang]:
                    problems.append(f"frontend: {lang}/{ns}: missing '{key}'")
                elif plural:
                    missing = REQUIRED_PLURALS[lang] - bases[lang][key]
                    if missing:
                        problems.append(f"frontend: {lang}/{ns}: '{key}' needs plural forms {sorted(missing)}")


def check_bot() -> None:
    base = ROOT / "bot/locales"
    if not base.exists():
        print("i18n: bot locales not created yet — skipped")
        return
    try:
        from babel.messages.pofile import read_po  # available in the bot env (aiogram i18n needs Babel)
    except ImportError:
        problems.append("bot: Babel not available — run via `make i18n-check` (uses the bot's uv env)")
        return
    ids: dict[str, set[str]] = {}
    for lang in LANGS:
        po = base / lang / "LC_MESSAGES" / "messages.po"
        ids[lang] = set()
        if not po.exists():
            problems.append(f"bot: {lang}/LC_MESSAGES/messages.po is missing (make i18n-bot-init)")
            continue
        with po.open("rb") as fh:
            catalog = read_po(fh, locale=lang)
        for msg in catalog:
            if not msg.id:
                continue  # header
            key = msg.id if isinstance(msg.id, str) else msg.id[0]
            ids[lang].add(key)
            values = list(msg.string) if isinstance(msg.string, (tuple, list)) else [msg.string]
            if msg.fuzzy:
                problems.append(f"bot: {lang}: fuzzy (not compiled) '{key[:60]}'")
            elif not values or any(not (v or "").strip() for v in values):
                problems.append(f"bot: {lang}: untranslated '{key[:60]}'")
    all_ids = set().union(*ids.values())
    for lang in LANGS:
        for msgid in sorted(all_ids - ids[lang]):
            problems.append(f"bot: {lang}: missing '{msgid[:60]}' (make i18n-bot)")


check_frontend()
check_bot()
if problems:
    print(f"i18n check failed ({len(problems)}):")
    for p in problems[:200]:
        print("  -", p)
    sys.exit(1)
print("i18n check passed: uz, ru, en, ja complete")
