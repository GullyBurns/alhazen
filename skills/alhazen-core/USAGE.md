# Alhazen Core — Usage Reference

## Commands

### `init`

Idempotent setup: starts the TypeDB Docker container, creates the `alhazen_notebook` database, and loads the base schema.

```bash
uv run --project <skill-path> python <skill-path>/alhazen_core.py init
```

**Expected output:**
```json
{
  "success": true,
  "typedb": "running",
  "database": "alhazen_notebook",
  "database_created": true,
  "schema": "loaded",
  "message": "Alhazen core ready."
}
```

Re-running `init` is safe — it skips steps that are already done.

**Auto-schema detection:** If a `schema.tql` file exists in the same directory as `alhazen_core.py`, `init` loads it automatically after the base schema. The output will include `"extra_schema": "loaded"` and an updated message. This is used by self-contained plugin bundles (e.g. `plugins/jobhunt/`) so a single SessionStart hook initializes both schemas without a separate `init-schema` step.

### `status`

Check whether Docker, the TypeDB container, and the database are ready.

```bash
uv run --project <skill-path> python <skill-path>/alhazen_core.py status
```

### `reset`

Drop and recreate the database, reloading the base schema. **Destroys all data.**

```bash
uv run --project <skill-path> python <skill-path>/alhazen_core.py reset --yes
```

### `backup`

Create a **focused, portable backup** of a subset of the graph as a single zip: a
scoped TypeDB subgraph slice (via `subgraph_migrator`, into a throwaway temp DB
that is exported and dropped) plus native Qdrant per-collection snapshots. Each
bundle re-imports standalone (`typedb-notebook import-db` + Qdrant snapshot
upload — restore steps are written into the bundle's `MANIFEST.json`). Zips land
in `~/.alhazen/cache/backups/`. Reads only; the live DBs are never modified.

```bash
# list presets
uv run python skills/alhazen-core/alhazen_core.py backup --list
# report scope + counts without writing a zip
uv run python skills/alhazen-core/alhazen_core.py backup --target deep-research --dry-run
# write the bundle(s)
uv run python skills/alhazen-core/alhazen_core.py backup --target career-kg
uv run python skills/alhazen-core/alhazen_core.py backup --all
```

Presets: **career-kg** (`alh_personal` `career-`/`jhunt-` + career/jobhunt Qdrant
collections) and **deep-research** (`alh_deep_research`
`scilit-`/`kefed-`/`ooevv-`/`trec-` + the `alhazen_papers` vectors). Shared
reference data (vocabulary, tags) is carried in every slice so it restores
cleanly. Engine lives in `src/skillful_alhazen/utils/focused_backup.py`; edit the
`TARGETS` dict there to add or adjust presets.

### `restore`

Load a bundle back in. It reads the bundle's own `MANIFEST.json`, imports the
TypeDB slice, and uploads each Qdrant snapshot — all against `TYPEDB_HOST` /
`QDRANT_HOST`. **To load elsewhere, point those env vars at the destination
instance** (the bundle is fully self-contained; nothing else is needed).

```bash
# preview only — reads the manifest, touches nothing
uv run python skills/alhazen-core/alhazen_core.py restore --zip <bundle>.zip --dry-run
# load into a fresh instance (default mode)
uv run python skills/alhazen-core/alhazen_core.py restore --zip <bundle>.zip
# to a different machine:
TYPEDB_HOST=box2 QDRANT_HOST=box2 uv run python skills/alhazen-core/alhazen_core.py restore --zip <bundle>.zip
```

Modes:
- **fresh** (default) — create the DB / collection; **refuses** if either already exists.
- **merge** — id-preserving additive: imports the slice into a temp DB, then copies it into the target (idempotent, skips ids already present). TypeDB only — Qdrant snapshot recovery can't merge point-wise, so a merge restore into an existing Qdrant collection is refused.
- **replace** — DESTRUCTIVE: drops the target DB / collection first, then loads. Requires `--yes`.

Other flags: `--target-db NAME` (override destination DB; default = bundle's source DB), `--typedb-only`, `--qdrant-only`.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `TYPEDB_HOST` | `localhost` | TypeDB server host |
| `TYPEDB_PORT` | `1729` | TypeDB server port |
| `TYPEDB_DATABASE` | `alhazen_notebook` | Database name |
| `TYPEDB_USERNAME` | `admin` | TypeDB username |
| `TYPEDB_PASSWORD` | `password` | TypeDB password |

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Docker is not running` | Start Docker Desktop (macOS) or `sudo systemctl start docker` |
| Container fails to start in 60s | `docker logs alhazen-typedb` — increase Docker memory in Desktop settings |
| Port 1729 already in use | `docker ps -a \| grep 1729` then `docker stop <id>` |
| Schema error `[SYR1]` | Run `reset --yes` to start fresh |

## After Init

After `init` succeeds, load each domain skill's schema:

```bash
# Example for jobhunt skill
uv run --project <jobhunt-path> python <jobhunt-path>/jobhunt.py init-schema

# Example for scientific-literature skill
uv run --project <scilit-path> python <scilit-path>/scientific_literature.py init-schema
```
