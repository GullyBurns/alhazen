#!/usr/bin/env python3
"""Guard against local skill edits being silently overwritten by skills-update.

External skills are symlinks into per-repo git clones under
`$ALHAZEN_SKILL_SOURCES` (default `~/Documents/GitHub`). `make skills-update`
pulls those clones (`--ff-only`). This check fails when a clone holds local work
that a pull/overwrite would endanger:

  - uncommitted changes (`git status --porcelain` non-empty), or
  - commits ahead of `origin/<ref>` (committed but not pushed).

A clone that is merely BEHIND origin (no local work) is reported but does NOT
fail — pulling it is the whole point of an update. The check distinguishes a
real local edit from merely-stale, using git provenance instead of a content
diff against a fresh clone.

Exit 0 if every external clone is clean & pushed (or just behind); 1 otherwise.
Core / `path:` skills are skipped — they have no separate upstream.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

GREEN, RED, YELLOW, NC = "\033[32m", "\033[31m", "\033[33m", "\033[0m"


def repo_name(url: str) -> str:
    return url.rstrip("/").split("/")[-1].removesuffix(".git")


def git(clone: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(clone), *args], capture_output=True, text=True)


def load_skills() -> list[dict]:
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
    sources_root = Path(
        os.environ.get("ALHAZEN_SKILL_SOURCES") or os.path.expanduser("~/Documents/GitHub")
    )

    # Group external skills by their backing clone (the examples repo backs several).
    repos: dict[str, dict] = {}
    for skill in load_skills():
        if "path" in skill:
            continue
        url = skill.get("git") or default_git
        if not url:
            continue
        rn = repo_name(url)
        entry = repos.setdefault(rn, {"ref": skill.get("ref") or default_ref, "skills": []})
        entry["skills"].append(skill["name"])

    drifted: list[str] = []
    for rn, info in sorted(repos.items()):
        clone = sources_root / rn
        backs = ", ".join(sorted(info["skills"]))
        ref = info["ref"]
        if not (clone / ".git").exists():
            print(f"{YELLOW}  ? {rn}: not cloned at {clone} — run make skills-install ({backs}){NC}")
            continue

        git(clone, "fetch", "origin", ref)  # best-effort; offline → ahead/behind may be stale
        dirty = git(clone, "status", "--porcelain").stdout.strip()
        lr = git(clone, "rev-list", "--left-right", "--count", f"origin/{ref}...HEAD").stdout.split()
        behind = int(lr[0]) if len(lr) == 2 else 0
        ahead = int(lr[1]) if len(lr) == 2 else 0

        if dirty or ahead:
            drifted.append(rn)
            print(f"{RED}  ✗ {rn}: local work at risk ({backs}){NC}")
            for line in dirty.splitlines()[:10]:
                print(f"      ~ {line.strip()}")
            if ahead:
                print(f"      ↑ {ahead} commit(s) ahead of origin/{ref} (unpushed)")
        elif behind:
            print(f"{YELLOW}  ↑ {rn}: {behind} commit(s) behind origin/{ref} — safe to update ({backs}){NC}")
        else:
            print(f"{GREEN}  ✓ {rn}: clean & in sync ({backs}){NC}")

    print()
    if drifted:
        print(f"{RED}✗ Upstream check FAILED — uncommitted or unpushed work in: "
              f"{', '.join(drifted)}{NC}")
        print(f"{RED}  Commit & push it from the clone, or re-run with FORCE=1 to overwrite.{NC}")
        return 1
    print(f"{GREEN}✓ All external skill clones are clean & pushed.{NC}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
