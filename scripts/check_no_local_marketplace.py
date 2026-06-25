#!/usr/bin/env python3
"""Guard: this clone must stay registry-only — it must NEVER act like a marketplace.

skillful-alhazen ships a publishable plugin marketplace (`.claude-plugin/marketplace.json`)
for EXTERNAL users. Locally, skills load via the registry (`make build-skills` ->
`.claude/skills/<name>` symlinks). The two paths must never mix: if the maintainer registers
THIS repo as a marketplace and installs an alhazen skill as a plugin, the plugin cache pins an
old commit and SHADOWS the live registry copy with stale code (this is what broke `jobhunt`
against the migrated `jhunt-*` data).

This check reads `~/.claude/settings.json` and the project `.claude/settings.json` and WARNS
(loudly, but never fails — exit 0 always) when it finds the dangerous overlap:
  * this repo registered in `extraKnownMarketplaces`, or
  * any core skill enabled as a plugin (`<skill>@skillful-alhazen` or a bare core-skill key)
    in `enabledPlugins`.

Run: `python scripts/check_no_local_marketplace.py`  (also called from `make build-skills`).
"""
from __future__ import annotations

import json
import os
import sys

MARKETPLACE_NAME = "skillful-alhazen"
REPO_SLUG = "sciknow-io/skillful-alhazen"
ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

# The 7 in-repo core skills published by this marketplace.
CORE_SKILLS = {
    "alhazen-core", "agentic-memory", "typedb-notebook", "web-search",
    "curation-skill-builder", "tech-recon", "agent-os",
}

YELLOW, RED, RESET = "\033[33m", "\033[31m", "\033[0m"


def _load(path: str) -> dict:
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _marketplace_is_this_repo(entry: object) -> bool:
    """True if an extraKnownMarketplaces entry points at THIS repo (github slug or local path)."""
    src = entry.get("source", entry) if isinstance(entry, dict) else entry
    if isinstance(src, dict):
        repo = (src.get("repo") or "").lower()
        if repo == REPO_SLUG.lower():
            return True
        path = src.get("path") or src.get("url") or ""
        if path and os.path.realpath(os.path.expanduser(str(path))) == ROOT:
            return True
    elif isinstance(src, str):
        if src.lower() == REPO_SLUG.lower():
            return True
        try:
            if os.path.realpath(os.path.expanduser(src)) == ROOT:
                return True
        except OSError:
            pass
    return False


def _scan(settings_path: str, label: str) -> list[str]:
    data = _load(settings_path)
    problems: list[str] = []

    for name, entry in (data.get("extraKnownMarketplaces") or {}).items():
        if name == MARKETPLACE_NAME or _marketplace_is_this_repo(entry):
            problems.append(
                f"[{label}] extraKnownMarketplaces['{name}'] registers THIS repo as a marketplace."
            )

    for key, enabled in (data.get("enabledPlugins") or {}).items():
        if not enabled:
            continue
        plug = key.split("@", 1)[0]
        market = key.split("@", 1)[1] if "@" in key else ""
        if plug in CORE_SKILLS and (market == MARKETPLACE_NAME or market == ""):
            problems.append(
                f"[{label}] enabledPlugins['{key}'] enables a core skill as a plugin — it will "
                f"SHADOW the live registry copy with stale cached code."
            )
    return problems


def main() -> None:
    home_settings = os.path.expanduser("~/.claude/settings.json")
    proj_settings = os.path.join(ROOT, ".claude", "settings.json")
    problems = _scan(home_settings, "~/.claude") + _scan(proj_settings, "project")

    if not problems:
        return  # silent on a clean (registry-only) environment

    print(f"{RED}WARNING: local clone is configured to act like a marketplace.{RESET}",
          file=sys.stderr)
    for p in problems:
        print(f"{YELLOW}  - {p}{RESET}", file=sys.stderr)
    print(f"{YELLOW}  Local dev must stay registry-only. Remediate:{RESET}", file=sys.stderr)
    print("      /plugin marketplace remove skillful-alhazen", file=sys.stderr)
    print("      /plugin uninstall <skill>@skillful-alhazen", file=sys.stderr)
    print(f"{YELLOW}  (Skills load via `make build-skills` -> .claude/skills, not via plugins.){RESET}",
          file=sys.stderr)
    # Warn only — never block legitimate work.
    sys.exit(0)


if __name__ == "__main__":
    main()
