# scilit KQED Session/Experience Reconciliation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reconcile the ad-hoc `scilit-session` and `scilit-observation-note` types into the KQED model: formalize `scilit-session` as a discourse source, rename `scilit-observation-note` → `scilit-experience-note` (freeing the `observation` name for KQED's epistemic D-node), and make both durable in the committed schema.

**Architecture:** Two schema entity types live in the external scilit skill repo's `schema.tql`; a one-off Python migration retypes the 10 live note instances and adds the new session play, then drops the old type/attrs. The committed schema is the durable home so `db-init` no longer drops them.

**Tech Stack:** TypeDB 3.8 (TypeQL define/undefine, `typedb-driver` Python), the worktree `.venv` (Python 3.12).

## Global Constraints

- TypeDB version is **3.8** — TypeQL 3.x syntax only (`attribute X, value T;`; `entity X sub Y, ...;`; relations before entity `plays`; `value integer` not `long`; delete is `delete $x;`).
- **Never emit `\uXXXX` escapes** in TypeQL string literals (panics TypeDB 3.8). Build literals with raw UTF-8; escape only `\`, `"`, newline via the canonical `escape_string` (`\\`, `\"`, `\n`, strip `\r`).
- **Relation MATCH** uses `links`: `$r isa T, links (role: $p)`. Match relation role-players by a **concrete type that plays the role** (matching the broad `alh-identifiable-entity` breaks role type-inference — INF4).
- **Variable-free schema match panics the server** — never `match scilit-X sub scilit-Y;` with two concrete labels; always bind a variable.
- **External skill edits go upstream** — `schema.tql`/`USAGE.md` live in `~/Documents/GitHub/alhazen-skill-examples`; edits there are globally visible and NOT branch-isolated in this repo.
- **Always `make db-export` before schema changes.**
- Live database name: `alhazen_notebook`. Driver creds: `admin`/`password`, `localhost:1729`, TLS off.

**Paths (exact):**
- External schema: `/Users/gullyburns/Documents/GitHub/alhazen-skill-examples/skills/biomed/scientific-literature/schema.tql`
- External usage: `/Users/gullyburns/Documents/GitHub/alhazen-skill-examples/skills/biomed/scientific-literature/USAGE.md`
- Migration script (this repo, worktree): `local_resources/typedb/migrate_observation_to_experience.py`
- Run commands from the worktree root: `/Users/gullyburns/skillful-alhazen/.worktrees/scilit-kqed-reconcile`

---

## Task 1: Formalize both types in the committed external schema

**Files:**
- Modify: `.../scientific-literature/schema.tql` — attributes block (~line 54, after `scilit-note-type`), sources section (after `scilit-protocol`, ~line 156), sensemaking-note section (after `scilit-methodology-note`, ~line 262), additive-plays section (after `entity scilit-paper plays scilit-hinge:hinged-to;`, ~line 455).

**Interfaces:**
- Produces: entity types `scilit-session`, `scilit-experience-note`; attributes `scilit-session-type`, `scilit-speaker`, `scilit-affiliation`, `scilit-session-url`, `scilit-experience-event`; additive play `scilit-session plays scilit-hinge:hinged-to`. The migration in Task 3 depends on these definitions existing.

- [ ] **Step 1: Add the new attributes** to the attributes block (after the line `attribute scilit-note-type, value string;`):

```tql
# --- discourse-source + experience-note attributes (KQED discourse/source layer) ---
attribute scilit-session-type, value string;     # keynote | workshop | tutorial | talk | panel
attribute scilit-speaker, value string;
attribute scilit-affiliation, value string;
attribute scilit-session-url, value string;
attribute scilit-experience-event, value string; # the occasion, e.g. "CAIS 2026 keynote"
```

- [ ] **Step 2: Add the `scilit-session` entity** in the sources section, immediately after `entity scilit-protocol sub scilit-paper;`:

```tql
# SCILIT-SESSION - a discourse SOURCE (keynote/workshop/tutorial/talk/panel), sibling of
# scilit-paper. The domain-neutral source for spoken/event content used by meeting surveys.
# alh-aboutness:subject and alh-collection-membership:member are inherited from alh-domain-thing;
# the scilit-hinge:hinged-to play is added additively below (scilit-hinge is defined later).
entity scilit-session sub alh-domain-thing,
    owns scilit-session-type,
    owns scilit-speaker @card(0..),
    owns scilit-affiliation @card(0..),
    owns scilit-session-url,
    owns scilit-publication-year;
```

- [ ] **Step 3: Add the `scilit-experience-note` entity** in the sensemaking-note section, immediately after the `scilit-methodology-note` entity block:

```tql
# SCILIT-EXPERIENCE-NOTE - a first-person anecdote / engagement record (System 1 rhetorical,
# discourse layer). `about` a source (session/paper) or person via the inherited alh-aboutness:note.
# Distinct from the KQED epistemic scilit-observation (a measurement-in-context, System 2).
entity scilit-experience-note sub alh-sensemaking-note,
    owns scilit-experience-event;
```

- [ ] **Step 4: Add the additive `hinged-to` play** right after `entity scilit-paper plays scilit-hinge:hinged-to;`:

```tql
entity scilit-session plays scilit-hinge:hinged-to;
```

- [ ] **Step 5: Verify the schema parses by loading it into a throwaway temp DB**

Run (from the worktree root):
```bash
uv run python skills/typedb-notebook/typedb_notebook.py import-db \
  --zip ~/.alhazen/cache/typedb/$(ls -t ~/.alhazen/cache/typedb/ | grep alhazen_notebook_export | head -1) \
  --database scilit_schema_probe >/dev/null 2>&1; echo "imported baseline"
# apply ONLY the new schema delta into the probe DB via a SCHEMA transaction
uv run python - <<'PY'
from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB
d=TypeDB.driver("localhost:1729",Credentials("admin","password"),DriverOptions(is_tls_enabled=False))
delta=open("/Users/gullyburns/Documents/GitHub/alhazen-skill-examples/skills/biomed/scientific-literature/schema.tql").read()
# load the whole committed schema.tql as an idempotent define against the probe
with d.transaction("scilit_schema_probe", TransactionType.SCHEMA) as tx:
    tx.query(delta).resolve(); tx.commit()
print("schema.tql applied to probe OK")
d.databases.get("scilit_schema_probe").delete(); print("probe dropped")
d.close()
PY
```
Expected: `schema.tql applied to probe OK` then `probe dropped`, with no `[DEX*]`/`[SVL*]` errors. If it errors on `scilit-session`/`scilit-experience-note`, fix ordering/syntax and re-run.

- [ ] **Step 6: Commit (in the external repo, on a feature branch)**

```bash
cd /Users/gullyburns/Documents/GitHub/alhazen-skill-examples
git checkout -b feat/scilit-session-experience-kqed
git add skills/biomed/scientific-literature/schema.tql
git commit -m "feat(scilit): formalize scilit-session source + scilit-experience-note (KQED discourse layer)"
cd /Users/gullyburns/skillful-alhazen/.worktrees/scilit-kqed-reconcile
```

---

## Task 2: Document the meeting-survey workflow in USAGE.md

**Files:**
- Modify: `.../scientific-literature/USAGE.md` — add a "Meeting surveys (discourse sources)" subsection near the Investigations section.

**Interfaces:**
- Consumes: the types from Task 1. Produces: no code, documentation only.

- [ ] **Step 1: Append the meeting-survey subsection** to `USAGE.md` (after the Investigations section):

```markdown
## Meeting surveys (discourse sources)

A **meeting survey** (a `survey`-type investigation, e.g. the CAIS 2026 conference survey)
covers a program of papers + spoken sessions. Two types support this, both in the
**domain-neutral discourse/source layer** (KQED System 1) — they never touch the biomed
S2/S3 (KEfED, bio-mechanism):

- **`scilit-session`** — a discourse SOURCE (keynote | workshop | tutorial | talk | panel),
  sibling of `scilit-paper`. Owns `scilit-session-type`, `scilit-speaker` (multi),
  `scilit-affiliation` (multi), `scilit-session-url`, `scilit-publication-year`. A claim can
  cite a talk via `scilit-hinge:hinged-to`, exactly as it cites a paper; a session is a corpus
  member and an aboutness subject like any source.
- **`scilit-experience-note`** — a first-person anecdote / engagement record (`sub
  alh-sensemaking-note`), `about` a session/paper/person. Owns `scilit-experience-event` (the
  occasion, e.g. "CAIS 2026 keynote"). This is distinct from the KQED epistemic
  `scilit-observation` (a measurement-in-context, System 2 / KEfED D-node).
```

- [ ] **Step 2: Commit (external repo, same branch)**

```bash
cd /Users/gullyburns/Documents/GitHub/alhazen-skill-examples
git add skills/biomed/scientific-literature/USAGE.md
git commit -m "docs(scilit): document meeting-survey discourse-source workflow"
cd /Users/gullyburns/skillful-alhazen/.worktrees/scilit-kqed-reconcile
```

---

## Task 3: Write the live migration script (with dry-run)

**Files:**
- Create: `local_resources/typedb/migrate_observation_to_experience.py`

**Interfaces:**
- Consumes: live DB `alhazen_notebook`. Produces: a re-runnable, idempotent migration with `--dry-run` (report only) and `--apply` (execute). Functions: `read_notes(driver)` → list of `{id, content, name, created_at, event, subjects:[(sid,stype)]}`; `apply_schema(driver)`; `migrate(driver, notes)`; `drop_old(driver)`.

- [ ] **Step 1: Create the migration script** with this exact content:

```python
#!/usr/bin/env python
"""Migrate scilit-observation-note -> scilit-experience-note (KQED reconciliation).

Idempotent. Run from the worktree root with the project venv:
    uv run python local_resources/typedb/migrate_observation_to_experience.py --dry-run
    uv run python local_resources/typedb/migrate_observation_to_experience.py --apply
"""
import argparse, os, sys
from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB

DB = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
HOST = os.getenv("TYPEDB_HOST", "localhost"); PORT = os.getenv("TYPEDB_PORT", "1729")
USER = os.getenv("TYPEDB_USERNAME", "admin"); PW = os.getenv("TYPEDB_PASSWORD", "password")

def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

def dt(s):  # TypeDB datetime literal, seconds precision, bare (no quotes)
    return str(s).strip().replace(" ", "T").split(".")[0]

def driver():
    return TypeDB.driver(f"{HOST}:{PORT}", Credentials(USER, PW), DriverOptions(is_tls_enabled=False))

SCHEMA_ADD = """
define
attribute scilit-experience-event, value string;
entity scilit-experience-note sub alh-sensemaking-note,
  owns scilit-experience-event;
entity scilit-session plays scilit-hinge:hinged-to;
"""

def type_exists(tx, label):
    # variable-bound (never `match X sub Y;` with two concrete labels)
    rows = list(tx.query(f"match $t sub {label}; fetch {{ \"l\": $t }};").resolve())
    return len(rows) > 0

def read_notes(drv):
    notes = {}
    with drv.transaction(DB, TransactionType.READ) as tx:
        for r in tx.query(
            'match $n isa scilit-observation-note, has id $id, has content $c;'
            ' try { $n has name $nm; }; try { $n has created-at $ca; };'
            ' try { $n has scilit-observation-event $ev; };'
            ' fetch { "id": $id, "c": $c, "nm": $nm, "ca": $ca, "ev": $ev };'
        ).resolve():
            j = r.to_json() if hasattr(r, "to_json") else r
            nid = j["id"]
            notes[nid] = {"id": nid, "content": j.get("c"), "name": j.get("nm"),
                          "created_at": j.get("ca"), "event": j.get("ev"), "subjects": []}
        for r in tx.query(
            'match $n isa scilit-observation-note, has id $nid;'
            ' $r isa alh-aboutness, links (note: $n, subject: $s); $s isa! $st, has id $sid;'
            ' fetch { "nid": $nid, "sid": $sid, "st": $st };'
        ).resolve():
            j = r.to_json() if hasattr(r, "to_json") else r
            st = j["st"]["label"] if isinstance(j["st"], dict) else j["st"]
            if j["nid"] in notes:
                notes[j["nid"]]["subjects"].append((j["sid"], st))
    return list(notes.values())

def apply_schema(drv):
    with drv.transaction(DB, TransactionType.SCHEMA) as tx:
        tx.query(SCHEMA_ADD).resolve(); tx.commit()

def migrate(drv, notes):
    for n in notes:
        with drv.transaction(DB, TransactionType.WRITE) as tx:
            # delete old aboutness rels + old note
            tx.query(f'match $n isa scilit-observation-note, has id "{esc(n["id"])}";'
                     f' $r isa alh-aboutness, links (note: $n); delete $r;').resolve()
            tx.query(f'match $n isa scilit-observation-note, has id "{esc(n["id"])}"; delete $n;').resolve()
            # insert new experience-note (same id)
            parts = [f'has id "{esc(n["id"])}"', f'has content "{esc(n["content"])}"']
            if n.get("name"): parts.append(f'has name "{esc(n["name"])}"')
            if n.get("created_at"): parts.append(f'has created-at {dt(n["created_at"])}')
            if n.get("event"): parts.append(f'has scilit-experience-event "{esc(n["event"])}"')
            tx.query("insert $n isa scilit-experience-note, " + ", ".join(parts) + ";").resolve()
            # re-link aboutness to each subject (match subject by its concrete type)
            for sid, stype in n["subjects"]:
                tx.query(f'match $n isa scilit-experience-note, has id "{esc(n["id"])}";'
                         f' $s isa {stype}, has id "{esc(sid)}";'
                         f' insert (note: $n, subject: $s) isa alh-aboutness;').resolve()
            tx.commit()

def drop_old(drv):
    with drv.transaction(DB, TransactionType.SCHEMA) as tx:
        if type_exists(tx, "scilit-observation-note"):
            tx.query("undefine owns scilit-observation-event from scilit-observation-note;").resolve()
            tx.query("undefine owns scilit-observation-context from scilit-observation-note;").resolve()
            tx.query("undefine scilit-observation-note;").resolve()
        if type_exists(tx, "scilit-observation-event"):
            tx.query("undefine scilit-observation-event;").resolve()
        if type_exists(tx, "scilit-observation-context"):
            tx.query("undefine scilit-observation-context;").resolve()
        tx.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        print("specify --dry-run or --apply"); sys.exit(2)
    drv = driver()
    try:
        notes = read_notes(drv)
        print(f"scilit-observation-note instances to migrate: {len(notes)}")
        for n in notes:
            print(f"  {n['id']}  event={n['event']!r}  subjects={len(n['subjects'])}")
        if a.dry_run:
            print("DRY-RUN: no writes."); return
        apply_schema(drv);  print("schema add OK")
        migrate(drv, notes); print(f"migrated {len(notes)} notes")
        drop_old(drv);       print("old type/attrs undefined")
        print("MIGRATION COMPLETE")
    finally:
        drv.close()

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run the dry-run** to verify the read phase sees exactly the expected state

Run:
```bash
uv run python local_resources/typedb/migrate_observation_to_experience.py --dry-run 2>&1 | grep -v VIRTUAL_ENV
```
Expected: `scilit-observation-note instances to migrate: 10`, then 10 lines each with a non-null `event=` and `subjects=` count ≥ 1, then `DRY-RUN: no writes.` If the count is not 10, STOP and investigate (the migration must not run against an unexpected state).

- [ ] **Step 3: Commit the script**

```bash
git add local_resources/typedb/migrate_observation_to_experience.py
git commit -m "feat(migration): scilit-observation-note -> scilit-experience-note migration script"
```

---

## Task 4: Execute the migration and verify

**Files:** none created — operates on the live DB.

**Interfaces:** Consumes the script from Task 3 and the schema from Task 1 (loaded into live via the SCHEMA_ADD define inside the script, so this task does not depend on a SessionStart reload).

- [ ] **Step 1: Back up the live DB**

Run:
```bash
make db-export 2>&1 | grep -E "zip_path|Database exported"
```
Expected: a new `zip_path` under `~/.alhazen/cache/typedb/` and `✓ Database exported`. Record the zip name (recovery path).

- [ ] **Step 2: Apply the migration**

Run:
```bash
uv run python local_resources/typedb/migrate_observation_to_experience.py --apply 2>&1 | grep -v VIRTUAL_ENV
```
Expected: `schema add OK`, `migrated 10 notes`, `old type/attrs undefined`, `MIGRATION COMPLETE`.

- [ ] **Step 3: Verify the final DB state**

Run:
```bash
export TYPEDB_DATABASE=alhazen_notebook
echo "experience-note count:"; uv run python skills/typedb-notebook/typedb_notebook.py query --read 'match $n isa scilit-experience-note; fetch { "i": $n.id };' --limit 1000 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['count'])"
echo "experience aboutness edges:"; uv run python skills/typedb-notebook/typedb_notebook.py query --read 'match $n isa scilit-experience-note; $r isa alh-aboutness, links (note: $n, subject: $s); fetch { "i": $s.id };' --limit 1000 2>/dev/null | python3 -c "import sys,json;print(json.load(sys.stdin)['count'])"
echo "old type still present? (expect MISSING):"; uv run python skills/typedb-notebook/typedb_notebook.py query --read 'match $t sub scilit-observation-note; fetch { "t": $t };' 2>/dev/null | python3 -c "import sys,json;print('EXISTS' if json.load(sys.stdin).get('success') else 'MISSING')"
echo "epistemic scilit-observation intact? (expect EXISTS):"; uv run python skills/typedb-notebook/typedb_notebook.py query --read 'match $t sub scilit-observation; fetch { "t": $t };' 2>/dev/null | python3 -c "import sys,json;print('EXISTS' if json.load(sys.stdin).get('success') else 'MISSING')"
echo "session hinged-to play (expect a row):"; uv run python skills/typedb-notebook/typedb_notebook.py describe-schema --type scilit-session 2>/dev/null | python3 -c "import sys,json;d=json.load(sys.stdin);print([p for p in d.get('plays',[]) if p.get('relation')=='scilit-hinge'])"
```
Expected: experience-note count **10**; aboutness edges **24**; old type **MISSING**; epistemic `scilit-observation` **EXISTS**; session plays `scilit-hinge:hinged-to`.

- [ ] **Step 4: Spot-check one migrated note's content + event + a preserved link**

Run:
```bash
uv run python skills/typedb-notebook/typedb_notebook.py query --read 'match $n isa scilit-experience-note, has id "scilit-observation-note-d53843c069f1", has content $c, has scilit-experience-event $e; $r isa alh-aboutness, links (note: $n, subject: $s), $s has id $sid; fetch { "e": $e, "len": $c, "subj": $sid };' 2>/dev/null
```
Expected: `e` = `"CAIS 2026 keynote"`, a multi-hundred-char `len` (content preserved), and at least the `scilit-session-0eaf5f280ce0` + `scilit-investigation-64e61368ead2` subjects.

- [ ] **Step 5: Lock in the migrated state**

Run:
```bash
make db-export 2>&1 | grep -E "zip_path|Database exported"
```
Expected: a fresh export zip. (No code commit — this task only changed DB state.)

---

## Task 5: Push upstream + record durability fix

**Files:**
- Modify: memory `project_cais_restore_schema_gap.md` (mark durability gap closed).

**Interfaces:** Consumes the external-repo commits (Tasks 1–2).

- [ ] **Step 1: Push the external branch (CONFIRM with the user first — outward-facing)**

Ask the user to confirm before pushing. On confirmation:
```bash
cd /Users/gullyburns/Documents/GitHub/alhazen-skill-examples
git push -u origin feat/scilit-session-experience-kqed
cd /Users/gullyburns/skillful-alhazen/.worktrees/scilit-kqed-reconcile
```
Expected: branch pushed; open a PR per the repo's convention.

- [ ] **Step 2: Verify durability — the committed schema now defines both types**

Run:
```bash
grep -nE "entity scilit-session sub|entity scilit-experience-note sub|scilit-session plays scilit-hinge" \
  /Users/gullyburns/Documents/GitHub/alhazen-skill-examples/skills/biomed/scientific-literature/schema.tql
```
Expected: three matches (session entity, experience-note entity, additive play). A future `db-init` now recreates both — the live-only drift is gone.

- [ ] **Step 3: Update the memory note** `project_cais_restore_schema_gap.md` — change the "Durability gotcha … Not yet done" line to note both types are now in the committed scilit schema (upstream `feat/scilit-session-experience-kqed`), `scilit-observation-note` renamed to `scilit-experience-note`, and `scilit-session` formalized.

---

## Notes on execution order & safety

- Tasks 1–2 (external schema/docs) and Task 3 (script) are non-destructive and can be done in any order; **Task 4 is the only destructive step** (live `undefine`) and is gated by the Step-1 backup.
- The migration script applies its own `SCHEMA_ADD`, so Task 4 does not require a SessionStart reload of the Task-1 schema — but Task 1 is still required for **durability** (otherwise `db-init` drops the types again).
- If Task 4 fails partway, recover with `make db-import ZIP=<the Step-1 backup>` and re-run; the script is idempotent (re-running after a partial run migrates only remaining `scilit-observation-note` instances and skips already-absent undefines).
