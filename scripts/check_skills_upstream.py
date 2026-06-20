#!/usr/bin/env python3
"""Guard against local_skills/ edits being silently overwritten by skills-update.

For every EXTERNAL skill in skills-registry.yaml (and skills-registry-local.yaml)
this clones the skill's upstream at its pinned ref and compares the upstream
subdir against the installed copy in local_skills/<name>/.

`make skills-update` deletes and re-clones external skills, so any edit made
directly in local_skills/ is lost. This check fails when the installed copy holds
content that an update would DESTROY:

  - "modified": a file exists in both but differs (a likely local edit)
  - "local-only": a file exists only in local_skills/ (added locally)

Being merely BEHIND upstream ("upstream-only" files) is reported but does NOT
fail — pulling those is the whole point of an update and loses nothing.

Exit code: 0 if no skill has modified/local-only content, 1 otherwise.

Core skills (registry `path:` entries) are symlinks to in-repo sources and are
skipped — they have no separate upstream to drift from.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

# Generated / environment artifacts that are never meaningful "local edits".
IGNORE_DIRS = {
    ".git", "__pycache__", ".venv", "node_modules", ".next", ".build",
    ".pytest_cache", ".ruff_cache", ".mypy_cache", "dist", "build", ".turbo",
}
IGNORE_SUFFIXES = (".pyc", ".pyo", ".egg-info")
IGNORE_NAMES = {".DS_Store", "uv.lock", "package-lock.json"}

GREEN, RED, YELLOW, BLUE, NC = "\033[32m", "\033[31m", "\033[33m", "\033[34m", "\033[0m"


def _ignored(rel: Path) -> bool:
    if any(part in IGNORE_DIRS for part in rel.parts):
        return True
    if rel.name in IGNORE_NAMES:
        return True
    return rel.name.endswith(IGNORE_SUFFIXES)


def _hash_tree(root: Path) -> dict[str, str]:
    """Map relative-path -> sha256 for every non-ignored file under root."""
    out: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORE_DIRS]
        for fn in filenames:
            abs_path = Path(dirpath) / fn
            rel = abs_path.relative_to(root)
            if _ignored(rel):
                continue
            h = hashlib.sha256(abs_path.read_bytes()).hexdigest()
            out[str(rel)] = h
    return out


def _load_skills() -> list[dict]:
    skills: list[dict] = []
    reg = Path("skills-registry.yaml")
    if reg.exists():
        skills += (yaml.safe_load(reg.read_text()) or {}).get("skills") or []
    local_reg = Path("skills-registry-local.yaml")
    if local_reg.exists():
        skills += (yaml.safe_load(local_reg.read_text()) or {}).get("skills") or []
    return skills


def main() -> int:
    reg = Path("skills-registry.yaml")
    if not reg.exists():
        print("No skills-registry.yaml found", file=sys.stderr)
        return 0
    cfg = yaml.safe_load(reg.read_text()) or {}
    defaults = cfg.get("defaults") or {}
    default_git = os.environ.get("ALHAZEN_SKILL_LIBRARY") or defaults.get("git", "")
    default_ref = defaults.get("ref", "main")

    skills = _load_skills()
    clone_cache: dict[tuple[str, str], Path] = {}
    tmp_root = Path(tempfile.mkdtemp(prefix="skills-check-"))
    drifted: list[str] = []
    behind: list[str] = []

    try:
        for skill in skills:
            name = skill["name"]
            if "path" in skill:
                continue  # core/local symlink — no separate upstream
            git_url = skill.get("git") or default_git
            ref = skill.get("ref") or default_ref
            subdir = skill.get("subdir", ".")
            if not git_url:
                print(f"{YELLOW}  ? {name}: no git URL and no defaults.git — skipped{NC}")
                continue

            local = Path("local_skills") / name
            if not local.exists():
                print(f"{YELLOW}  ? {name}: not installed in local_skills/ — skipped{NC}")
                continue

            key = (git_url, ref)
            clone = clone_cache.get(key)
            if clone is None:
                clone = tmp_root / f"clone_{len(clone_cache)}"
                try:
                    subprocess.run(
                        ["git", "clone", "--depth=1", "--branch", ref, git_url, str(clone)],
                        check=True, capture_output=True,
                    )
                except subprocess.CalledProcessError as e:
                    print(f"{RED}  ✗ {name}: failed to clone {git_url}@{ref}: "
                          f"{e.stderr.decode()[:120]}{NC}")
                    drifted.append(name)
                    continue
                clone_cache[key] = clone

            upstream = clone / subdir if subdir != "." else clone
            if not upstream.exists():
                print(f"{RED}  ✗ {name}: subdir '{subdir}' not found in upstream{NC}")
                drifted.append(name)
                continue

            local_h, up_h = _hash_tree(local), _hash_tree(upstream)
            modified = sorted(p for p in local_h.keys() & up_h.keys() if local_h[p] != up_h[p])
            local_only = sorted(local_h.keys() - up_h.keys())
            upstream_only = sorted(up_h.keys() - local_h.keys())

            if modified or local_only:
                drifted.append(name)
                print(f"{RED}  ✗ {name}: local content would be LOST on update{NC}")
                for p in modified:
                    print(f"      ~ modified:   {p}")
                for p in local_only:
                    print(f"      + local-only: {p}")
                if upstream_only:
                    print(f"      ({len(upstream_only)} file(s) also behind upstream)")
            elif upstream_only:
                behind.append(name)
                print(f"{YELLOW}  ↑ {name}: behind upstream by {len(upstream_only)} "
                      f"file(s) (safe to update){NC}")
            else:
                print(f"{GREEN}  ✓ {name}: matches upstream{NC}")
    finally:
        shutil.rmtree(tmp_root, ignore_errors=True)

    print()
    if drifted:
        print(f"{RED}✗ Upstream check FAILED — local edits would be overwritten: "
              f"{', '.join(drifted)}{NC}")
        print(f"{RED}  Push these changes upstream first, or re-run with "
              f"FORCE=1 to overwrite them.{NC}")
        return 1
    if behind:
        print(f"{YELLOW}✓ No local edits at risk ({len(behind)} skill(s) behind "
              f"upstream — update will refresh them).{NC}")
    else:
        print(f"{GREEN}✓ All external skills match upstream.{NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
