#!/usr/bin/env python3
"""Validate every plugin in the marketplace against the Alhazen plugin-architecture bar.

For each plugin listed in `.claude-plugin/marketplace.json`, check:
  - the `source` directory exists
  - `.claude-plugin/plugin.json` is present and its `version` matches the
    marketplace entry's `version` (when both are set)
  - `SKILL.md` is present
  - if `hooks/hooks.json` initializes alhazen-core (calls `alhazen_core.py`):
      * the install hint uses `alhazen-core@skillful-alhazen`
        (fail on `@alhazen-core` / `@alhazen-skills`)
      * `plugin.json` `dependencies` resolves to include `alhazen-core`
        (directly, or transitively via `typedb-notebook`)
      * every `load-schema "${CLAUDE_PLUGIN_ROOT}/<f>"` target file exists

Exit non-zero with a readable list on any failure. Run: `python scripts/validate_plugins.py`.

Note: CLI self-containment (skillful_alhazen imports) is intentionally NOT checked —
in-repo plugins may import the parent package by design.
"""
from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
MARKETPLACE = os.path.join(ROOT, ".claude-plugin", "marketplace.json")

BAD_HINTS = ("alhazen-core@alhazen-core", "alhazen-core@alhazen-skills")

# Plugins that transitively pull in alhazen-core via their own `dependencies`.
# Depending on any of these satisfies the "must reach alhazen-core" rule.
PULLS_IN_CORE = {"alhazen-core", "typedb-notebook"}


def _dep_names(pj: dict) -> list[str]:
    """Extract dependency plugin names from the official `dependencies` field.

    Entries may be bare strings or objects ({"name": ..., "version"?, "marketplace"?}).
    """
    names: list[str] = []
    for dep in pj.get("dependencies") or []:
        if isinstance(dep, str):
            names.append(dep)
        elif isinstance(dep, dict) and dep.get("name"):
            names.append(dep["name"])
    return names


def _hook_commands(hooks_path: str) -> list[str]:
    data = json.load(open(hooks_path, encoding="utf-8"))
    cmds = []
    for group in data.get("hooks", {}).get("SessionStart", []):
        for h in group.get("hooks", []):
            if h.get("command"):
                cmds.append(h["command"])
    return cmds


def validate(root: str = ROOT) -> list[str]:
    problems: list[str] = []
    mp_path = os.path.join(root, ".claude-plugin", "marketplace.json")
    market = json.load(open(mp_path, encoding="utf-8"))

    for entry in market.get("plugins", []):
        name = entry.get("name", "?")
        pdir = os.path.normpath(os.path.join(root, entry.get("source", "")))

        def err(msg: str) -> None:
            problems.append(f"[{name}] {msg}")

        if not os.path.isdir(pdir):
            err(f"source dir missing: {entry.get('source')}")
            continue

        reqs: list[str] = []
        plugin_json = os.path.join(pdir, ".claude-plugin", "plugin.json")
        if not os.path.isfile(plugin_json):
            err("missing .claude-plugin/plugin.json")
        else:
            pj = json.load(open(plugin_json, encoding="utf-8"))
            reqs = _dep_names(pj)
            if pj.get("requires"):
                err("legacy `requires` field present — migrate to official `dependencies`")
            if entry.get("version") and pj.get("version") and entry["version"] != pj["version"]:
                err(f"version mismatch: marketplace {entry['version']} != plugin.json {pj['version']}")

        if not os.path.isfile(os.path.join(pdir, "SKILL.md")):
            err("missing SKILL.md")

        hooks_path = os.path.join(pdir, "hooks", "hooks.json")
        if os.path.isfile(hooks_path):
            try:
                cmds = " ".join(_hook_commands(hooks_path))
            except Exception as exc:  # noqa: BLE001
                err(f"hooks.json invalid: {exc}")
                cmds = ""
            if "alhazen_core.py" in cmds and name != "alhazen-core":
                for bad in BAD_HINTS:
                    if bad in cmds:
                        err(f"hook install hint uses '{bad}' (want 'alhazen-core@skillful-alhazen')")
                if not (set(reqs) & PULLS_IN_CORE):
                    err("hook initializes alhazen-core but `dependencies` does not reach "
                        "'alhazen-core' (directly or via 'typedb-notebook')")
                for tgt in re.findall(r'load-schema "\$\{CLAUDE_PLUGIN_ROOT\}/([^"]+)"', cmds):
                    if not os.path.isfile(os.path.join(pdir, tgt)):
                        err(f"hook load-schema target missing: {tgt}")
    return problems


def main() -> None:
    problems = validate()
    market = json.load(open(MARKETPLACE, encoding="utf-8"))
    if problems:
        print("Plugin validation FAILED:", file=sys.stderr)
        for p in problems:
            print("  - " + p, file=sys.stderr)
        sys.exit(1)
    print(f"OK: {len(market.get('plugins', []))} plugins valid")


if __name__ == "__main__":
    main()
