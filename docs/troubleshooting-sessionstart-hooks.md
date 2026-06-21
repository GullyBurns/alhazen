# Troubleshooting: SessionStart Hook Failures on `/clear`

**Date:** 2026-06-20 · **Status:** fixed (core fix committed to `skillful-alhazen` `main`; external-skill + jobhunt hook fixes in upstream `alhazen-skill-examples` / `alhazen-skill-dismech` working trees — see "Second pass")

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
