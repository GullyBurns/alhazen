# Skill Query Gateway

A warm, long-lived Python service that runs skill CLI commands in-process, so the
dashboard no longer spawns `uv run python <skill>.py` per request.

## Why

Every dashboard data request currently does:

```ts
execFileAsync('uv', ['run', 'python', SCRIPT, ...args]) // → JSON.parse(stdout)
```

Each call pays Python cold-start + uv resolution + a fresh TypeDB connection, and
the dashboard image has to bundle uv + Python + the venv + **every skill's code**
(~11 GB). The *contract* (`{skill, command, argv} → JSON`) is good; only the
*transport* (subprocess-per-request) is the problem.

The gateway keeps the contract and replaces the transport: it imports each skill
module **once** and drives the skill's existing `main()` via a synthetic
`sys.argv`, capturing the JSON the command prints. **No skill code changes** — it
works because every skill follows the same `argparse → commands[cmd](args) →
print(json.dumps(...))` shape over the shared root venv.

## Design

- `src/skillful_alhazen/gateway/dispatcher.py` — resolves a skill to its full
  source dir (`local_skills/<skill>` or `skills/<skill>`), imports the entrypoint
  module once (cached), then per call sets `sys.argv`, redirects stdout, runs
  `main()`, catches `SystemExit`, and parses the printed JSON. A process-global
  lock serializes invocations (`sys.argv`/`sys.stdout` are global).
- `src/skillful_alhazen/gateway/app.py` — FastAPI: `GET /health`, `POST /run`.
  Runs the dispatcher in a thread with a timeout so the loop stays responsive.
- Runs as the `gateway` service (`gateway/Dockerfile`, `docker-compose.yml`) —
  Python + skills, **no Node**. This is where the "run a skill" weight belongs.

## HTTP contract

```
GET  /health → { "ok": true, "skills": ["agentic-memory", ...] }

POST /run
  body: { "skill": "jobhunt", "argv": ["list-pipeline", "--status", "active"],
          "entrypoint": "jobhunt"?, "timeout": 120? }
  200:  { "ok": true,  "result": <parsed JSON the command printed>,
          "exit_code": 0, "stderr": "...", "entrypoint": "jobhunt" }
  200:  { "ok": false, "error": "non-JSON stdout: ...", "raw": "...", "stderr": "..." }
  404:  { "ok": false, "error": "unknown skill: 'nope'" }
  504:  { "ok": false, "error": "command timed out after 120s" }
```

`entrypoint` is the script stem; it defaults to the skill's primary script
(`skill.yaml` `cli:` or first of `scripts:`). Pass it for secondary scripts,
e.g. jobhunt's `job_forager`.

## Adopting it in a dashboard lib (future work)

`dashboard/src/lib/skill-gateway.ts` exports `runSkill(skill, argv, opts?)`. A
skill's `lib.ts` helper changes from a subprocess spawn to a one-liner:

```ts
// before
async function runJobhunt(args: string[]) {
  const { stdout } = await execFileAsync('uv', ['run','python', JOBHUNT_SCRIPT, ...args]);
  return JSON.parse(stdout);
}
// after
import { runSkill } from '@/lib/skill-gateway';
async function runJobhunt(args: string[]) { return runSkill('jobhunt', args); }
```

Call sites (the exported `listPipeline()` etc.) don't change.

> **Note:** for **external** skills (jobhunt, scientific-literature, coach,
> dismech) the `lib.ts` source lives upstream — those edits must go to the
> upstream repo, not `local_skills/`, or `make skills-update` will overwrite
> them. See [`conventions.md`](conventions.md).

The dashboard image can only drop Python **after every lib has migrated** to the
gateway.

## Limitations (v1)

- Invocations serialize per process; long-running commands (scilit `search`/
  `embed`, `fetch-pdf`, jobhunt foraging) are better left on the CLI path. A
  future async/background-job endpoint can lift this.
- A hung command holds the lock until the timeout. Single uvicorn worker by
  design; scale by running multiple gateway replicas or, later, a worker pool.
