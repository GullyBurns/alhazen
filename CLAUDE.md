# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

Skillful-Alhazen is a TypeDB-powered scientific knowledge notebook. It helps researchers build knowledge graphs from papers and notes using AI-powered analysis. Named after Ibn al-Haytham (965-1039 AD), an early pioneer of the scientific method.

Forked from the CZI [alhazen](https://github.com/chanzuckerberg/alhazen) project.

## Agent OS — Coordinator Role

Claude Code acts as the **coordinator agent** for the Alhazen notebook OS. The OS has 6 layers, all backed by TypeDB as the single source of truth:

| Layer | Purpose | Implementation |
|-------|---------|----------------|
| **Identity** | Who the operator is, rules enforced every session | `nbmem-operator-role` linked to `alh-person` via `alh-role-bearing` (6 context domains) via `agentic_memory.py` |
| **Context** | Structured knowledge about the operator's situation | TypeDB relations + context files in workspace |
| **Skills** | Domain-specific reusable instruction sets | `skills/` directories, `skills-registry.yaml` |
| **Memory** | What the system remembers across sessions | Two-tier: MEMORY.md (short-term) + TypeDB `nbmem-memory-claim-note` (long-term) |
| **Connections** | How agents reach external systems | Documented in `connections/README.md` |
| **Verification** | Ensuring outputs are correct, system improves | `skilllog` + quality labels + schema gap detection |

### Coordinator Responsibilities

1. **Load identity at session start** — Query the operator's context from TypeDB to understand who you're working for:
   ```bash
   uv run python skills/agentic-memory/agentic_memory.py get-context --operator-id <id> 2>/dev/null
   ```

2. **Consolidate results into long-term memory** — After significant work:
   ```bash
   uv run python skills/agentic-memory/agentic_memory.py consolidate \
     --content "<key finding>" --subject <entity-id> --alh-fact-type knowledge --confidence 0.9
   ```

3. **Create session episodes** — At session close, capture a process account:
   ```bash
   uv run python skills/agentic-memory/agentic_memory.py create-episode \
     --skill <primary-skill> --summary "<what was accomplished>"
   ```

### Available Agents

Agents are defined in `agents/` and resolved to `.claude/agents/` via `agents-registry.yaml`:

| Agent | Skills | Purpose |
|-------|--------|---------|
| `career-assistant` | jobhunt, web-search, agentic-memory, typedb-notebook | Career assistant: pipeline management, networking, interview prep/debrief, market monitoring, JSC tracking |

Read an agent's `AGENT.md` before dispatching to understand its capabilities and operating rules.

> **Note:** Sub-agent dispatch via `Agent()` is not currently implemented. Agents are used as persona prompts loaded via Claude Code's `/agents` feature.

### Core OS Components (not skills)

- **Identity + Memory + Context**: `skills/agentic-memory/agentic_memory.py` — operator profiles, memory claims, episodes, context domains
- **Notebook**: `skills/typedb-notebook/typedb_notebook.py` — collections, notes, tagging, aboutness
- **Verification**: `local_resources/skilllog/skill_logger.py` — invocation logging, quality labels, schema gap detection

## Database Architecture — per-repo split (Jun 2026)

Data is split across **one TypeDB database per repo** (the old single `alhazen_notebook` is being retired). Each skill's `TYPEDB_DATABASE` default points at its repo's DB; skills outside `alh_core` carry a `.standalone-db` marker (skipped by `make db-init`) and provision their own DB via a per-skill SessionStart hook.

| Database | Repo | Skills |
|----------|------|--------|
| `alh_core` | skillful-alhazen | alhazen-core, typedb-notebook, agentic-memory, curation-skill-builder, agent-os, web-search |
| `alh_deep_research` | `sciknow-io/alhazen-skill-deep-research` | scientific-literature (schema base), literature-trends, tech-recon, dismech-notebook |
| `alh_personal` | `sciknow-io/alhazen-skill-personal-assistant` | jobhunt, coach |
| `alh_mythras` | `fourth-wall-gaming/mythras-gm` | mythras-gm |
| `alh_biorodeo` | alhazen-skill-biorodeo | biorodeo-workbench |
| `dismech` | alhazen-skill-dismech | dismech (Monarch ingest source; GLAV source for dismech-notebook) |

Rules:
- **Shared reference data** (`alh-vocabulary`, `alh-vocabulary-type`, `alh-tag`) is **replicated** into each DB so classification/tagging/vocab relations resolve locally.
- **No cross-database relations** (TypeDB limitation). A skill that references another DB's entity uses a soft reference (an id/DOI attribute resolved in the app layer) — e.g. jobhunt's `jhunt-cited-paper-id` → `scilit-paper` in `alh_deep_research`. Skills that need TypeDB-level links (tech-recon/dismech-notebook → `scilit-paper`) must be **co-located in the same DB**.
- **Migration tool**: `src/skillful_alhazen/utils/subgraph_migrator.py` (`copy`/`verify`) — id-preserving, scope by `--prefix`/`--types`, `--also-types` for shared refs, `--closure-notes` for aboutness-owned bare notes.

## First-Run Check

> Before doing any work, check whether the project has been built. If `local_skills/` does not exist, run `make build` from the project root. The build is idempotent — safe to re-run.
>
> ```bash
> ls local_skills/ 2>/dev/null || echo "NOT BUILT — run: make build"
> ```
>
> **Worktrees:** `make build` works from worktrees. TypeDB is a shared Docker container (uses a fixed compose project name), so `db-start` is idempotent.

## Directory Structure

```
agents/                 # Named sub-agent definitions (committed)
agents-registry.yaml    # Single source of truth for agents
skills/                 # Skills (committed — core OS + domain skills)
skills-registry.yaml    # Single source of truth for skills
connections/            # Documented connection capabilities
local_skills/           # Gitignored build artifact — DO NOT EDIT
.claude/skills/         # Gitignored — symlinks generated by make build-skills
.claude/agents/         # Gitignored — symlinks generated by make build-agents
local_resources/typedb/ # Core schema + infrastructure schemas
src/skillful_alhazen/   # Main package (mcp/, utils/)
dashboard/              # Next.js TypeScript dashboard
deploy/                 # Ansible deployment scripts
tests/                  # Test files
```

## On-Demand Reference Docs

Read these **before** the relevant task — they are NOT auto-loaded:

| Doc | Read before... |
|-----|----------------|
| [`docs/setup.md`](docs/setup.md) | First-time build, troubleshooting prerequisites, environment variables |
| [`docs/makefile.md`](docs/makefile.md) | Running `make` targets, backups, CLI usage |
| [`docs/typedb.md`](docs/typedb.md) | Writing ANY TypeQL query or schema definition |
| [`docs/architecture.md`](docs/architecture.md) | Understanding data model, skills, agents, dashboards, cache |
| [`docs/schema-lifecycle.md`](docs/schema-lifecycle.md) | Schema gaps, migration methods (in-place, GLAV, binary), PR workflow |
| [`docs/conventions.md`](docs/conventions.md) | Audit process, dashboard work, external skill fixes |
| [`docs/dashboard-guide.md`](docs/dashboard-guide.md) | Building a new skill dashboard (Python CLI → lib → API → pages) |
| [`docs/deployment.md`](docs/deployment.md) | Deploying to Mac Mini or VPS |
| [`docs/troubleshooting-sessionstart-hooks.md`](docs/troubleshooting-sessionstart-hooks.md) | `SessionStart:clear hook Failed` errors, typedb-driver segfaults on Python 3.14 |
| `local_resources/typedb/llms.txt` | Full TypeDB 3.x query reference (load on demand) |

## Skill Loading: Dual-Mode (publishable marketplace + registry-only local dev)

This repo has **two non-overlapping loading paths**. They never mix — that separation is the whole design.

**1. LOCAL DEV (how you, the maintainer, work) — registry-only.** Every skill loads through ONE path: the registry. `skills-registry.yaml` (committed) + `skills-registry-local.yaml` (gitignored local overrides) → `make build-skills` → `local_skills/<name>` symlinks → `.claude/skills/<name>`. Skills load with **bare names** (`tech-recon`, `jobhunt`). External skills point at upstream clones via `subdir:` (default git) or absolute `path:`. **TypeDB autostart** is delivered at the project level: `make deploy-claude-settings` writes a `SessionStart` hook into `.claude/settings.json` that runs `local_skills/alhazen-core/alhazen_core.py init` — it does NOT depend on any plugin being installed.

**2. EXTERNAL USERS — this repo IS a publishable Claude Code marketplace.** `.claude-plugin/marketplace.json` (repo root) publishes the **7 in-repo core skills** (`alhazen-core`, `agentic-memory`, `typedb-notebook`, `web-search`, `curation-skill-builder`, `tech-recon`, `agent-os`). External users run `/plugin marketplace add sciknow-io/skillful-alhazen` → `/plugin install <skill>@skillful-alhazen`. On that path TypeDB autostart comes from `alhazen-core`'s OWN `hooks/hooks.json` SessionStart hook (`${CLAUDE_PLUGIN_ROOT}/alhazen_core.py init`). Keep the manifest correct with `make validate-plugins` (`scripts/validate_plugins.py`). External (non-core) skills — `scientific-literature`, `jobhunt`, `dismech-notebook`, etc. — self-publish from their own upstream marketplaces; this manifest is core-only.

**NEVER let the local clone act like a marketplace.** Do NOT `/plugin marketplace add` this repo locally, and do NOT enable any alhazen skill as a plugin in `~/.claude/settings.json` / project `.claude/settings.json`. The plugin cache pins an old commit and **shadows the live registry copy with stale code** (this is what broke `jobhunt` against the migrated `jhunt-*` data). The active guard `scripts/check_no_local_marketplace.py` (run automatically by `make build-skills`) warns loudly if it ever detects this repo in `extraKnownMarketplaces` or a core skill in `enabledPlugins`. The marketplace manifest is *inert* — it does nothing until someone explicitly registers it — so it sits in the repo harmlessly while you develop via the registry.

> **The two paths DO touch at one layer — the `skills-dir` auto-plugin — and that is deliberate.** Recent Claude Code auto-loads any `.claude/skills/<name>/` that contains a `.claude-plugin/plugin.json` as a plugin named `<name>@skills-dir` (no marketplace, no install). We *rely* on this in local dev: it is what registers each skill's own `hooks/hooks.json` `SessionStart` hook — the per-skill TypeDB schema provisioner that runs via `${CLAUDE_PLUGIN_ROOT}` (the `.standalone-db` skills depend on this; the project-level `.claude/settings.json` hook only inits `alhazen-core`'s core schema). The problem: Claude Code also validates that manifest's cross-marketplace `dependencies` (`alhazen-core@skillful-alhazen`, …), which can't resolve locally because we never install the alhazen marketplace as plugins — surfacing as `<skill>@skills-dir: Dependency "…" is not installed` errors at session start.
>
> **The fix lives in `make deploy-claude`:** `.claude/skills/<name>` is a real directory of per-item symlinks into `local_skills/<name>`, with one exception — `.claude-plugin/plugin.json` is written as a **local copy with the `dependencies` field stripped**. Hooks still register (skill is still a `skills-dir` plugin); there are no `dependencies` to fail; and the **upstream** manifest keeps its full `dependencies` for the publish path (§2). So: never expose the upstream manifest's `dependencies` under `.claude/skills/` — strip them — and never delete the manifest entirely (that would unregister the per-skill schema hooks).

> When you change an external skill, still reproduce the fix in its **upstream repo** and publish there; `make skills-update` pulls it back. Only the 7 core skills live-and-publish from THIS repo.

> **Plugin dependencies (base pair).** Use Claude Code's official **`dependencies`** field in `plugin.json` (NOT the old advisory `requires.plugins`, which Claude Code ignores — `validate_plugins.py` now flags any leftover `requires`). `alhazen-core` + `typedb-notebook` are the inseparable **base pair**: `typedb-notebook` declares `dependencies: ["alhazen-core"]`, and any skill that uses the notebook CRUD engine declares `typedb-notebook` (which transitively pulls core). `alhazen-core` itself depends on nothing — **never make alhazen-core depend on typedb-notebook** (Claude Code does not support dependency cycles). There is no official manifest field for system bins (`uv`/`docker`) — document those in SKILL.md. Cross-marketplace deps (a skill in another repo depending on this marketplace's core/notebook) need `allowCrossMarketplaceDependenciesOn` in the *root* marketplace plus a `marketplace` key on the dependency entry.

## Parallel Work-Thread Worktrees

Run multiple work-threads in parallel, each isolated on its own branch + git worktree of THIS repo. Each thread should target a different skill so they don't collide at the skill level; branch-per-thread keeps shared main-repo setup edits (registries, `Makefile`, core schema, dashboard wiring, `.claude/settings.json`) from stepping on each other.

### What a worktree isolates vs. shares
- **Isolated per worktree:** working tree + branch, `local_skills/`, `.claude/` symlinks, `dashboard/src/` generated copies, `.venv`.
- **Shared across ALL worktrees (single instance, NOT branched):** the TypeDB container + `alhazen_notebook` DB, `~/.alhazen/cache`, the external skill repos (symlinked, each on its own `main`), and Docker ports.

### Setup (per thread) — branches named `wt/<short-task>`; `.worktrees/` is already gitignored
1. **Back up the shared DB first:** `make db-export`, verify the zip in `~/.alhazen/cache/typedb/`.
2. From the repo root (separate Bash call — **NEVER chain `rm -rf` + `make`**):
   `git worktree add .worktrees/<slug> -b wt/<slug>`
3. Inside the worktree, run the **NON-DESTRUCTIVE build subset** (everything except `build-db`):
   `cd .worktrees/<slug> && make build-env build-skills build-agents build-dashboard`
   **Do NOT run `make build` / `make build-db` in a worktree** — `build-db` → `db-init` reloads every skill schema into the SHARED DB from your branch. The shared DB already has all schemas; reloading from a branch is unnecessary and risky. `db-start` is idempotent and the container is already running.
   **Pin Python 3.12 for the venv:** `pyproject.toml` has `requires-python = ">=3.11"` with no upper cap, so a fresh worktree's `make build-env` can create a **Python 3.14** `.venv` — and **`typedb-driver` segfaults on 3.14** (`exit 139` on any query). After build-env, force the proven-good interpreter:
   `uv sync --all-extras --python 3.12` (recreates `.venv` on 3.12.12; `--all-extras` is required — `typedb-driver` lives in the `[typedb]` extra). Verify with `uv run python -c "import sys,typedb; print(sys.version)"`.

### Per-tree dashboard (local `next dev`, no docker; distinct port, avoid docker's `:3001`)
```
cd .worktrees/<slug>/dashboard && npm install   # first time
PROJECT_ROOT=<absolute-worktree-root> TYPEDB_DATABASE=alhazen_notebook npx next dev -p <port>
```
`PROJECT_ROOT` is **required**: `dashboard/src/lib/*.ts` defaults it to `process.cwd()` (= `dashboard/` under `next dev`), so without it the API routes resolve `.claude/skills/...` against the wrong directory. Suggested ports: 3010, 3011, 3012, …

### Coordination rules
- **Core `alhazen-core` schema: ONE THREAD AT A TIME**; other threads stay skill-namespaced. Always `make db-export` before any schema delta.
- **Skill schemas must be namespaced & disjoint** (`scilit-`, `jhunt-`, …) — this is what makes parallel data-layer work safe on the one shared DB.
- **External skill-repo edits are globally visible and NOT branch-isolated**; push upstream from the thread, and give the external repo its own branch/worktree if a thread must change it.

### Teardown
```
git worktree remove .worktrees/<slug>   # --force if it holds build artifacts
git branch -d wt/<slug>                  # -D if intentionally discarding unmerged work
```

## Critical Safety Rules

### NEVER Chain Destructive Commands With make build-skills

**Never combine `rm -rf` on skill directories with `make build-skills` (or any `make` target) in a single Bash tool call.**

In March 2026, this pattern **deleted the entire project directory**. Rules:
1. **Never chain `rm -rf` + `make` in one Bash call.** Split into separate tool calls with verification between each.
2. **Read the Makefile before running any `make` target** — `make build-skills` calls `deploy-claude-settings`, which has side effects.
3. **After any `rm -rf`, verify the working directory still exists** before doing anything else.
4. **If `make` output is unexpectedly empty or silent, stop and investigate.**

### Always Back Up TypeDB Before Schema Changes or db-init

**`make db-init` and `make build-db` DROP and RECREATE the database.** All data is lost. Before running any command that touches the schema or reinitializes the database:

1. **Run `make db-export`** — creates a timestamped zip in `local_resources/typedb/exports/`
2. **Verify the export exists** before proceeding
3. If `db-init` fails partway (e.g., schema conflict), the backup zip is the recovery path

This applies to:
- `make db-init`, `make build-db`, `make build` (which calls `build-db`)
- Any manual `db_init.py` invocation
- Schema changes that require reloading (new attributes, new entity types)
- `make db-migrate` (which creates its own backup, but verify)

**Safe pattern:**
```bash
make db-export              # Step 1: backup
make db-init                # Step 2: reload schemas (destructive!)
# If db-init fails, recover: make db-import ZIP=<latest-export.zip>
```

### NEVER Run a Variable-Free Schema Match (crashes TypeDB 3.8)

**A schema match where both sides are concrete type labels with no variable — e.g. `match alh-analysis-pipeline-note sub alh-note;` or `match scilit-faceting-note sub alh-analysis-pipeline-note;` — panics the TypeDB server** (`assertion failed: num_input_variables > 0`, `compiler/executable/match_/planner/plan.rs`). The driver surfaces it as `h2 protocol error: ... broken pipe` and the Docker container actually **restarts**, so it looks like a transient connection drop but is a reproducible crash that takes the DB down.

**Always bind a variable** when checking that a type exists or listing subtypes:
```python
# GOOD — returns the type plus its subtypes; read labels via the concept API
match $t sub alh-analysis-pipeline-note;   # then row.get("t").get_label()
```
Do **not** use `fetch { "x": $t.label }` — `label` is a reserved keyword in fetch and also errors.

### External Skill Fixes Must Go Upstream

External skills (`jobhunt`, `dismech-notebook` etc.) are cloned from other repositories (`https://github.com/sciknow-io/alhazen-skill-examples`, `https://github.com/sciknow-io/alhazen-skill-dismech`). Fixes in `local_skills/` get overwritten by `make skills-update` (which is very, very, very bad). ALWAYS push fixes upstream first. See [`docs/conventions.md`](docs/conventions.md) for details.

### Dashboard Files: NEVER Edit in dashboard/src/ Directly

**`dashboard/src/components/`, `dashboard/src/lib/`, `dashboard/src/app/(skill)/`, `dashboard/src/app/api/skill/` are GENERATED copies.** They get overwritten by `make build-dashboard`.

The source of truth for each skill's dashboard is `skills/{name}/dashboard/` (for core skills) or `local_skills/{name}/dashboard/` (for external skills), with 4 slots:

```
skills/{name}/dashboard/
  components/   -> dashboard/src/components/{name}/
  lib.ts        -> dashboard/src/lib/{name}.ts
  pages/        -> dashboard/src/app/({name})/
  routes/       -> dashboard/src/app/api/{name}/
```

**To edit dashboard code:** Edit in `skills/{name}/dashboard/` (or the upstream git repo for external skills), then run `make build-dashboard` to propagate. NEVER edit the copies in `dashboard/src/` — they will be silently overwritten on next build.

### Playwright Screenshots Go in the Cache

When using Playwright MCP tools to take screenshots during testing, **always save them to `~/.alhazen/cache/screenshots/`**, not the project root. Screenshots left in the project root pollute `git status` and risk being committed.

```bash
# Good — save to cache
mcp__playwright__browser_take_screenshot(filename="~/.alhazen/cache/screenshots/my-test.png")

# Bad — pollutes project root
mcp__playwright__browser_take_screenshot(filename="my-test.png")
```

The cache directory is `~/.alhazen/cache/screenshots/` — create it if it doesn't exist.
