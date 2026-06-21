# Troubleshooting: SessionStart Hook Failures on `/clear`

**Date:** 2026-06-20 · **Status:** core + external hook *wiring* fixed (passes 1–2). **But** a third root cause was found the same evening: the harness was firing hooks from **stale on-disk copies of the repo** (`.skills-build/` container-mount staging dir + an iCloud-synced clone), not from the fixed working tree — so the symptom survived correct, committed fixes. See "Third root cause" below; this is the one to check first if `/clear` still shows failures.

If, on `startup` / `clear` / `compact`, you see a stack of:

```
SessionStart:clear hook  Failed with non-blocking status code: No stderr output
SessionStart:clear hook  Failed with non-blocking status code: warning: `VIRTUAL_ENV=.venv` does not match ... will be ignored ...
```

…this is the issue described here. It is **non-blocking** — TypeDB and the dashboard still come up — but it's noisy and means dependent skills skip their schema-load step.

## Two independent root causes

The Alhazen core skills (`alhazen-core`, `agent-os`, `agentic-memory`, `typedb-notebook`,
`curation-skill-builder`, `tech-recon`, `web-search`) each ship a `SessionStart` hook in
`skills/<name>/hooks/hooks.json`. In this dev repo they load as local symlinks
(`.claude/skills/* → local_skills/* → skills/*`), **not** as installed marketplace plugins.

1. **Hook wiring (the "No stderr output" failures).**
   The six *dependent* skills' hooks located alhazen-core via
   `find ~/.claude/plugins/cache -path '*/alhazen-core/*/alhazen_core.py'`.
   In the dev repo alhazen-core is a symlink, not a cached plugin, so `find` returned empty
   and each hook printed a message to **stdout** and `exit 1` — surfaced as
   *"Failed … No stderr output"* (the message went to stdout, not stderr). They never reached
   their `init` / `load-schema` step.

2. **typedb-driver segfault on Python 3.14 (the `VIRTUAL_ENV` warning failure, exit 139).**
   `skills/alhazen-core/pyproject.toml` had `requires-python = ">=3.11"` with **no upper bound**,
   so `uv` built the venv on **CPython 3.14.3**. `typedb-driver` 3.8.x's native wheel
   **segfaults (SIGSEGV in `_wrap_credentials_new`)** constructing `Credentials(...)` under 3.14.
   It's *intermittent* (the first call in a fresh process sometimes survives), which is why it
   looked flaky. Native traceback:
   `typedb/native_driver_wrapper.py:credentials_new` → `native_driver_python.so` → segfault.

   `dismech` and `mythras-gm` already carried the `<3.14` cap — this bug had been hit before.

## What was changed (the fix)

**`skillful-alhazen` (this repo — uncommitted in working tree at time of writing):**

- `skills/alhazen-core/pyproject.toml`: `requires-python = ">=3.11,<3.14"`; venv re-synced to
  **Python 3.13.12** (`uv.lock` updated). `init` now returns `{"success": true, ...}`.
- All 7 `skills/*/hooks/hooks.json` rewritten so each hook now:
  - falls back to the sibling `${CLAUDE_PLUGIN_ROOT}/../alhazen-core/alhazen_core.py` when
    the plugin-cache `find` misses (fixes dev; `find` still covers the installed-plugin path);
  - uses `exit 0` (not `exit 1`) when alhazen-core is genuinely absent — graceful, no "Failed";
  - prepends `unset VIRTUAL_ENV; export PYTHONWARNINGS=ignore::SyntaxWarning;` for clean stderr.

  Editing `skills/*/hooks/hooks.json` is sufficient — the symlink chain means **no rebuild**.

**`alhazen-skill-examples` (upstream — pushed to `main`, commit `8c3d963`/`c2c1242`):**

- Same `<3.14` cap added to `coach`, `literature-trends`, `scientific-literature`
  (external skills; per repo convention the fix must go upstream, not into `local_skills/`).
  Local venvs for these were re-synced to 3.13/3.12. `make skills-update` will pull the cap.

## Second pass (same day) — the OTHER 6 hooks were still failing

The first pass fixed only the **7 core** skills. The harness actually fires **13** SessionStart
hooks, and 6 were untouched — `/clear` still showed a stack of failures:

- **5 external skills** — `coach`, `dismech`, `dismech-notebook`, `literature-trends`,
  `scientific-literature` — still had the old `find`→`exit 1` wiring (the "No stderr output"
  failures). **The core skills' sibling fallback does NOT help them:** their
  `.claude/skills/<name>` symlinks point into *different* repos
  (`alhazen-skill-examples`, `alhazen-skill-dismech`), so `${CLAUDE_PLUGIN_ROOT}/../alhazen-core`
  resolves to the wrong parent and misses. They need the **project-dir fallback**
  `${CLAUDE_PROJECT_DIR}/.claude/skills/alhazen-core/alhazen_core.py`, which resolves regardless
  of where the skill's symlink lands.
- **`jobhunt`** — its hook ran (`exit 0`) but leaked the `VIRTUAL_ENV=.venv does not match`
  warning to stderr because it lacked `unset VIRTUAL_ENV` (the "warning" failures).

**Fix applied (all upstream — these are symlink targets of `local_skills/`):**

- The 5 external hooks + `jobhunt`'s source hook (`alhazen-skill-examples/skills/demo/jobhunt`)
  rewritten with the full fallback chain: `find` (installed-plugin) → sibling
  (`${CLAUDE_PLUGIN_ROOT}/../alhazen-core`, core-skill dev) → **project-dir**
  (`${CLAUDE_PROJECT_DIR}/.claude/skills/alhazen-core`, any dev skill) → graceful `exit 0`;
  each prepends `unset VIRTUAL_ENV; export PYTHONWARNINGS=ignore::SyntaxWarning;`. Each skill's
  own `init`/`load-schema`/`TYPEDB_DATABASE` tail is preserved verbatim.
- Edited via the `local_skills/<name>/hooks/hooks.json` symlinks, which write straight into the
  upstream clones (`alhazen-skill-examples`, `alhazen-skill-dismech`) — so this is the upstream
  fix *and* immediate dev relief in one. **Still uncommitted in those clones' working trees** at
  time of writing; commit + push to make durable.
- The installed `jobhunt` 1.0.0 in `~/.claude/plugins/cache` was also patched in place for
  immediate relief, but that copy is overwritten on plugin update — the source fix above is the
  permanent one.

After this pass, all **13** hooks exit 0 with clean stderr.

## Third root cause (2026-06-20, evening) — the fix was real but the harness wasn't reading the fixed repo

After the two passes above, `/clear` **still** showed ~10 `SessionStart:clear … No stderr output`
failures — even though every `skills/*/hooks/hooks.json` on disk was correct and ran clean
(`exit 0`) both sequentially and concurrently. The fixes were committed (`ac3e392`, 21:53);
the `/clear` was at 22:07; the failures persisted. **The fix landed in a repo the harness
doesn't read for these hooks.**

### How it was diagnosed (do this first next time — don't theorize)

The session transcript records every hook result. Pull them directly instead of guessing:

```bash
F=~/.claude/projects/-Users-gullyburns-skillful-alhazen/<session-id>.jsonl
python3 - "$F" <<'PY'
import json,sys
for line in open(sys.argv[1]):
    o=json.loads(line); a=o.get('attachment',{})
    if a.get('type')=='hook_non_blocking_error' and a.get('hookEvent')=='SessionStart':
        print(a['exitCode'], repr(a.get('stdout','')[:80]), '|', a['command'][:120])
PY
```

The fired commands were the **old `find → echo → exit 1` wiring** (no fallback, no
`unset VIRTUAL_ENV`) — i.e. pre-fix text. Two giveaways:

- The `stdout` was `alhazen-core plugin required…` and `exitCode` was `1` → that's the old
  `echo "…" && exit 1` branch printing to **stdout** (hence "No stderr output").
- A **single `/clear` fired a mix of two historical eras at once**: 4 hooks said
  `…@alhazen-core` (the May 22–Jun 13 text) and 6 said `…@skillful-alhazen` (Jun 13–Jun 20
  text). One in-memory snapshot can't hold two eras → the hooks were being read from **two
  different stale on-disk copies of the repo**, not from the working tree.

Then content-match each distinct fired command against every `hooks.json` on the machine:

```bash
# the fired command text is unique enough to pin its source file exactly
find ~ -name hooks.json -not -path '*/node_modules/*' 2>/dev/null | while read f; do
  grep -q "find ~/.claude/plugins/cache -path '\*/alhazen-core" "$f" && grep -q '&& exit 1' "$f" \
    && echo "STALE: $f"
done
```

### The two stale sources (both proven by byte-exact content match)

1. **`./.skills-build/`** — the **container-mount staging dir** (Makefile `stage-skills`, a
   symlink-free `cp -RL` copy of the skills for Docker bind-mounts). It was staged *before* the
   21:53 hook fix, so its copy was frozen at the stale era. **Claude Code's skill discovery
   scans the project working tree and picks up `.skills-build/*/SKILL.md` + `hooks/hooks.json`
   as additional skill sources.** Source of the 6 `@skillful-alhazen` failures (incl. the only
   on-disk match for `typedb-notebook`/`web-search` init-only).
2. **An iCloud-synced clone** — `~/Library/Mobile Documents/com~apple~CloudDocs/Documents/GitHub/skillful-alhazen`
   — a *divergent* checkout frozen at the older `@alhazen-core` era (HEAD `d644eef`, already an
   ancestor of canonical `main`, so it holds no unique committed work). Source of the 4
   `@alhazen-core` failures. (Discovery vector: a runtime skill scan that reaches it — **not** a
   registered project and **not** under `ALHAZEN_SKILL_SOURCES` (`~/Documents/GitHub`, which is
   *local* on this machine). Resolution is dynamic per-startup, not a persisted path: the
   `~/.claude/plugins/data/*-skills-dir` markers predate `.skills-build`'s creation yet
   `.skills-build` content still fired.)

Why earlier passes missed it: they edited `skills/*/hooks/hooks.json` (correct, committed) and
the upstream working trees. None of that touches `.skills-build/` (gitignored build artifact)
or a separate iCloud checkout. **Editing the working repo's hooks does nothing if the live hook
source is a stale copy elsewhere.**

### The fix

- **`.skills-build/`** — re-stage so the copy carries the *current* fixed hooks (clears in place,
  keeps running container mounts valid):
  ```bash
  make stage-skills          # then verify:
  grep -rl '&& exit 1' .skills-build/*/hooks/hooks.json   # must print nothing
  ```
  (Better long-term: stop Claude's skill discovery from descending into `.skills-build/` at all
  — see origin branch `feat/skills-mounted-sources`.)
- **iCloud clone** — its committed work is already in canonical `main`; retire it (move it out of
  any scanned location, or `git pull` it current) so its stale hooks stop being discovered. Verify
  first that nothing unique is uncommitted.
- **Restart Claude Code fully** (quit the process — `/clear` re-runs the *same* startup scan
  result for the session; a fresh process re-scans the now-clean sources) and re-run the
  transcript check above to confirm 0 failures.

## Verify it's working

```bash
# Each hook should exit 0 with clean JSON and no segfault/warning:
ROOT=/Users/gullyburns/skillful-alhazen
CORE="$ROOT/.claude/skills/alhazen-core"
unset VIRTUAL_ENV
uv run --project "$CORE" python "$CORE/alhazen_core.py" init   # -> {"success": true, ...}

# Confirm the venv is NOT on 3.14:
$CORE/.venv/bin/python --version                                # -> 3.13.x (must be < 3.14)
```

## If it's still broken / something else regressed

- **Still segfaulting (exit 139):** a venv got rebuilt on 3.14. `rm -rf <skill>/.venv && uv sync
  --project <skill>` and confirm `requires-python` has the `<3.14` cap. Check *all* skills with
  `typedb-driver`: `grep -l typedb-driver skills/*/pyproject.toml local_skills/*/pyproject.toml`.
- **"alhazen-core not found" on session start:** expected/harmless now (exit 0). It means neither
  the plugin cache nor the sibling symlink resolved. In the dev repo, run `make build-skills` to
  restore the `.claude/skills/* → local_skills/* → skills/*` symlinks.
- **Hooks reverted to `exit 1` / old wiring:** `make skills-update` overwrote an *external* skill,
  or someone rebuilt from a stale source. Core-skill hooks live in `skills/*/hooks/hooks.json`
  (committed here); external-skill hooks must be fixed upstream in `alhazen-skill-examples`.
- **TypeDB itself down:** unrelated to this fix — `docker ps` and `make db-start`.
