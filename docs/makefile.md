# Makefile Usage

Two phases, each with a primary entry point:

**Phase 1 — Build (local dev, Claude Code):**
```bash
make build            # Full build: deps + skills + TypeDB
make build-env        # Install Python dependencies only
make build-skills     # Resolve skills registry → local_skills/ + wire .claude/skills/
make build-db         # Start TypeDB + load all schemas
```

**Phase 2 — Deploy (production OpenClaw) — ⚠️ DEPRECATED:**
> OpenClaw deployment is no longer supported — the project pivoted to a full Claude-based
> implementation (run with Claude Code) to keep the approach undiluted and avoid the token-cost of a
> persistent service through the API. These targets remain but are unmaintained.
```bash
make deploy-macmini   # Deploy to Mac Mini (Docker Desktop)
make deploy-vps       # Deploy to VPS (Podman rootless)
make deploy-openclaw  # Wire skills + config for local OpenClaw instance
```

**Skills management:**
```bash
make skills-list      # Show all skills from registry with resolution status
make skills-update    # Re-resolve all skills (re-link core, re-clone external)
make skills-validate  # Validate all resolved skills have correct SKILL.md
```

**Database management:**
```bash
make db-start         # Start TypeDB container
make db-stop          # Stop TypeDB container
make db-init          # Create database and load all schemas (discovers local_skills/*/schema.tql)
make db-export        # Export database to timestamped zip
make db-import ZIP=/path/to/export.zip  # Import database
```

**Backups — TypeDB (`alhazen_notebook` and `dismech`):**

Exports are written to `~/.alhazen/cache/typedb/<database>_export_<timestamp>.zip`.

```bash
# Export (works while TypeDB is running)
make db-export                                   # exports alhazen_notebook (default)
uv run python .claude/skills/typedb-notebook/typedb_notebook.py export-db --database dismech

# Restore (drops and recreates the database)
uv run python .claude/skills/typedb-notebook/typedb_notebook.py import-db \
  --zip ~/.alhazen/cache/typedb/alhazen_notebook_export_<timestamp>.zip \
  --database alhazen_notebook
# NOTE: database must not already exist — delete it first if needed:
# uv run python -c "
#   from typedb.driver import TypeDB, Credentials, DriverOptions
#   d = TypeDB.driver('localhost:1729', Credentials('admin','password'), DriverOptions(is_tls_enabled=False))
#   d.databases.get('alhazen_notebook').delete(); d.close()
# "
```

**Backups — Qdrant vector store:**

Snapshots are created online (no downtime) and stored inside the container at `/qdrant/snapshots/<collection>/`.
Copy them out immediately — they do not persist across container recreation.

```bash
# Discover all collections and snapshot each one
collections=$(curl -s http://localhost:6333/collections | python3 -c "import json,sys; [print(c['name']) for c in json.load(sys.stdin)['result']['collections']]")
for coll in $collections; do
  curl -s -X POST "http://localhost:6333/collections/${coll}/snapshots" 2>/dev/null && echo "${coll}: OK"
done

# Copy all snapshots out of container
mkdir -p ~/.alhazen/cache/qdrant-snapshots
for coll in $collections; do
  docker cp alhazen-qdrant:/qdrant/snapshots/${coll}/. ~/.alhazen/cache/qdrant-snapshots/ 2>/dev/null
done

# Restore a collection from snapshot
curl -X POST "http://localhost:6333/collections/<collection>/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{"location": "file:///path/to/<snapshot-file>.snapshot"}'
```

**What to back up and when:**
- **TypeDB databases** — back up after significant work sessions with `make db-export`. Each database in the system can be exported independently via `typedb_notebook.py export-db --database <name>`.
- **Qdrant collections** — back up after any embedding update. Rebuilding requires Voyage AI API credits and time. Use the discovery-based script above to catch all collections regardless of which skills created them.

## Development Commands

**Project status:**
```bash
make status         # Show TypeDB container status + skills deployment count
```

**Manual commands:**
```bash
# Installation
uv sync --all-extras

# TypeDB management
make db-start       # Start TypeDB container
make db-stop        # Stop TypeDB container

# Full stack with MCP server
docker compose -f docker-compose-typedb-mcp.yml up -d

# Testing and development
make test           # Run tests
make lint           # Run linter
make clean          # Clean generated files
```

**CLI usage:**
```bash
uv run python .claude/skills/typedb-notebook/typedb_notebook.py insert-collection --name "Test"
uv run python .claude/skills/scientific-literature/scientific_literature.py count --query "CRISPR"
uv run python .claude/skills/jobhunt/jobhunt.py list-pipeline
# Note: .claude/skills/* are symlinks -> local_skills/* -> skills/* (for core)
```

**Dashboard:**
```bash
cd dashboard && npm install && npm run dev
```

## Quick Reference

```bash
make build            # Full Phase 1 build: deps + skills + agents + TypeDB
make build-env        # Install Python dependencies (uv sync --all-extras)
make build-skills     # Resolve skills-registry.yaml -> local_skills/ + wire .claude/skills/
make build-agents     # Resolve agents-registry.yaml -> .claude/agents/
make build-db         # Start TypeDB + load all schemas (run after build-skills)
make db-start         # Start TypeDB container only
make db-init          # (Re-)load all schemas into running TypeDB
make skills-update    # Force re-clone all external skills
make status           # Show TypeDB + skills deployment status
make deploy-macmini   # Phase 2 (DEPRECATED): deploy to Mac Mini (Docker Desktop)
make deploy-vps       # Phase 2 (DEPRECATED): deploy to VPS (Podman rootless)
```
