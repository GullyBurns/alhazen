# Scilit CLI/kqed Re-alignment (Sub-project 1, Plan 2 of 3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Re-point `kqed.py` and `scientific_literature.py` — every authoring verb AND every read/`_load_*`/`show-*` handler — off the retired types and onto the clean reconfigured schema, plus add the one missing successor relation (`scilit-sensemaking-experiment`) and make investigation authoring iteration-aware. After this, the CLI writes and reads the clean model end to end.

**Architecture:** Both files build TypeQL as inline f-strings against TypeDB 3.8 via `get_driver()`. We add a DB-backed authoring/read test layer (extending Plan 1's scratch-DB harness) that points the modules at a throwaway DB, calls the real functions, and asserts round-trips. Behavior-preserving where the type only renamed; structure-changing where the model changed (slots gone, bigraph, first-class iterations).

**Tech Stack:** TypeDB 3.8.0, `typedb-driver>=3.8.0,<3.11`, Python 3.12, `uv`, pytest.

## Global Constraints

- **Upstream repo, same branch:** all edits in `~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/`, branch `feat/scilit-schema-reconfiguration` (continues PR #7). Commit there.
- **The reconfigured schema is the source of truth** (Plan 1, already on this branch). Retired type names must NOT appear in live TypeQL of either `.py` file after this plan (comments OK). Retired→new map (apply verbatim):

  | Retired | New |
  |---|---|
  | `scilit-reported-claim` / `scilit-reported-gap` | `scilit-claim` / `scilit-gap` |
  | `kefed-variable` (entity) | `ooevv-variable` |
  | `kefed-variable-role` (attr) | `ooevv-variable-role` |
  | `kefed-value-set` (attr) | (dropped — no successor) |
  | `kefed-element(model,variable)` | `kefed-model-element(model,element)` |
  | `ooevv-set-process(container,contained-process)` / `ooevv-set-entity(container,contained-entity)` | `kefed-model-element(model,element)` |
  | `kefed-template` (entity) | `kefed-model` + `has kefed-model-state "template"` |
  | `kefed-slot`/`kefed-template-slot`/`ooevv-param-slot`/`ooevv-slot-binding` + `kefed-slot-role`/`kefed-slot-kind` | (dropped — slots folded into uninstantiated `ooevv-variable`) |
  | `kefed-observed-via(observation,model)` | (dropped — see Task 3 for the new observation↔experiment wiring) |
  | `ooevv-bundle-experiment(bundle,experiment)` | `scilit-sensemaking-experiment(sensemaking,experiment)` (added in Task 1) |
  | `scilit-iteration-number` (attr) | first-class `scilit-iteration` (owns `scilit-iteration-index`) |
  | `scilit-investigation-phasing(investigation,phase)` | `scilit-investigation-iteration` + `scilit-iteration-stage` |

  Role renames on KEPT relations: `ooevv-parameter-binding` `binding-process`→`binding-bearer`; `ooevv-produced-by` `produced-measurement`/`terminal-process`→`produced-variable`/`producing-process`; `ooevv-instance-of` `template`→`model`; `scilit-claim-observation` `reported-claim`→`claim`.
- **TypeDB 3.x:** never a variable-free schema match; `delete has $v of $e;` form; fetch returns plain dicts; relation MATCH uses `links`/`(role: $x) isa T`; cannot fetch attrs off a relation var (bind in match).
- **Tests are DB-backed and call the REAL functions** (not reimplementations) against the scratch DB, asserting via independent read queries.

## File structure

- `schema.tql` — Task 1 adds ONE relation (`scilit-sensemaking-experiment`) + its plays.
- `kqed.py` — Task 2 rewrites `add_kefed_model`, `add_observation`, `add_gap`.
- `scientific_literature.py` — Tasks 3-8 re-point the `cmd_*` and `_load_*` handlers (per the cluster inventory) and delete the obsolete slot commands + their argparse subparsers + dispatch entries.
- `tests/conftest.py` — Task 1 adds an `authoring_db` fixture (points `kqed`/`scientific_literature` at the scratch DB).
- `tests/test_cli_realignment.py` — NEW: DB-backed round-trip tests, one cluster per task.

---

## Task 1: Successor relation + authoring test harness

**Files:** Modify `schema.tql`, `tests/conftest.py`; Create `tests/test_cli_realignment.py`.

**Interfaces produced:** relation `scilit-sensemaking-experiment(sensemaking, experiment)` — `sensemaking` played by `scilit-paper-sensemaking`, `experiment` played by BOTH `kefed-model` and `kefed-instance`. Fixture `authoring_db` → yields a driver on the scratch DB with `kqed.DB` and `scientific_literature.TYPEDB_DATABASE` monkeypatched to it.

- [ ] **Step 1: Failing test** — add to `tests/test_cli_realignment.py`:

```python
import os, sys, json, types
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from conftest import w, r, SCRATCH_DB

def test_sensemaking_experiment_relation(scratch_db):
    w(scratch_db, 'insert $b isa scilit-paper-sensemaking, has id "scsm-1", has name "bundle";')
    w(scratch_db, 'insert $m isa kefed-model, has id "kefedm-x", has name "exp", has kefed-model-state "instantiated";')
    w(scratch_db, 'match $b isa scilit-paper-sensemaking, has id "scsm-1"; $m isa kefed-model, has id "kefedm-x";'
                  ' insert (sensemaking: $b, experiment: $m) isa scilit-sensemaking-experiment;')
    w(scratch_db, 'insert $i isa kefed-instance, has id "kefedi-x", has name "run";')
    w(scratch_db, 'match $b isa scilit-paper-sensemaking, has id "scsm-1"; $i isa kefed-instance, has id "kefedi-x";'
                  ' insert (sensemaking: $b, experiment: $i) isa scilit-sensemaking-experiment;')
    rows = r(scratch_db, 'match $b isa scilit-paper-sensemaking, has id "scsm-1";'
                         ' (sensemaking: $b, experiment: $e) isa scilit-sensemaking-experiment; $e has id $eid; fetch {"eid": $eid};')
    assert sorted(x["eid"] for x in rows) == ["kefedi-x", "kefedm-x"]
```

- [ ] **Step 2: Run, confirm FAIL** — `uv run --python 3.12 pytest tests/test_cli_realignment.py::test_sensemaking_experiment_relation -v` → relation undefined.
- [ ] **Step 3: Schema** — add to `schema.tql` (relations block, before the entity plays):

```tql
relation scilit-sensemaking-experiment,      # a per-paper bundle groups its KEfED experiments (model/instance)
    relates sensemaking, relates experiment;
entity scilit-paper-sensemaking plays scilit-sensemaking-experiment:sensemaking;
entity kefed-model plays scilit-sensemaking-experiment:experiment;
entity kefed-instance plays scilit-sensemaking-experiment:experiment;
```

- [ ] **Step 4: Harness** — add to `tests/conftest.py` an `authoring_db` fixture:

```python
@pytest.fixture
def authoring_db(scratch_db, monkeypatch):
    """scratch_db + the authoring modules pointed at it, so real cmd_*/kqed.* write to the scratch DB."""
    skill_dir = str(SKILL_DIR)
    if skill_dir not in sys.path:
        sys.path.insert(0, skill_dir)
    import kqed, scientific_literature
    monkeypatch.setattr(kqed, "DB", SCRATCH_DB)
    monkeypatch.setattr(scientific_literature, "TYPEDB_DATABASE", SCRATCH_DB)
    return scratch_db
```
(`SCRATCH_DB` and `SKILL_DIR` already exist in conftest from Plan 1; export `SCRATCH_DB` if not already module-level.)

- [ ] **Step 5: Run** — both the relation test and the full `tests/test_schema_roundtrip.py` pass (schema still loads).
- [ ] **Step 6: Commit** — `git add schema.tql tests/conftest.py tests/test_cli_realignment.py && git commit -m "feat(scilit): scilit-sensemaking-experiment successor relation + authoring test harness"`

---

## Task 2: kqed.py authoring rewrite (bigraph, observation, gap)

**Files:** Modify `kqed.py`, `tests/test_cli_realignment.py`.

`add_kefed_model`, `add_observation`, `add_gap` reference retired types AND pre-existing drift (`scilit-investigation-observation`, `scilit-investigation-gap`, `scilit-observation-subject` do not exist in the schema). Rewrite onto the clean model.

**New structures:**
- `add_kefed_model(driver, name, ...)` → insert a `kefed-model` (id, name, `has kefed-model-state "template"` when no values, else `"instantiated"`). Variables are now `ooevv-variable` (owns `ooevv-variable-role`, `kefed-efo-label`) grouped by `(model: $m, element: $v) isa kefed-model-element`. Drop `kefed-element`/`kefed-variable`/`kefed-variable-role`/`kefed-value-set`/`format "kefed-protocol"`.
- `add_observation(driver, sensemaking_bundle, statement, knowledge_level, bio_scale, about=None, ...)` → insert a `scilit-observation` (owns `scilit-knowledge-level`, `scilit-bio-scale`), thread it under its bundle via the existing `scilit-sensemaking-observation(sensemaking, observation)` relation (NOT the nonexistent `scilit-investigation-observation`), and span-anchor/about handling via `scilit-sensemaking-paper`/`alh-derivation` as available. Drop `kefed-observed-via` and `scilit-observation-subject` entirely. (Signature changes from `investigation`/`kefed_model` to `sensemaking_bundle`; update the 1 caller if any — grep `add_observation(`.)
- `add_gap(driver, sensemaking_bundle, category_term, knowledge_goal, provenance, statement, ...)` → insert `scilit-gap` (owns `scilit-knowledge-goal`), thread under the bundle via `scilit-sensemaking-reported-gap(sensemaking, reported-gap)`. Drop the nonexistent `scilit-investigation-gap`.

- [ ] **Step 1: Failing tests** (use `authoring_db`): build a model with one parameter + one measurement variable via `add_kefed_model`, assert `kefed-model-element` links + `ooevv-variable-role` round-trip; create a bundle + `add_observation`, assert `scilit-observation` threaded under it via `scilit-sensemaking-observation`; `add_gap`, assert `scilit-gap` threaded via `scilit-sensemaking-reported-gap`. (Write concrete inserts/asserts mirroring Task 1's style, calling `kqed.add_kefed_model(authoring_db, ...)` etc.)
- [ ] **Step 2: Run, confirm FAIL** (functions still emit retired types → query/insert errors).
- [ ] **Step 3: Rewrite** the three functions per the new structures above. Grep `add_observation(`/`add_gap(`/`add_kefed_model(` across the repo (incl. `prototypes/`) and update any in-repo caller signatures; prototypes that are one-off seeds may be left if unused by tests, but note them.
- [ ] **Step 4: Run** — new tests pass; `kqed.py`'s own `tests/` (if any) still pass.
- [ ] **Step 5: Commit** — `feat(scilit): kqed authoring onto clean model (bigraph model, bundle-threaded observation/gap)`

---

## Task 3: RENAME-ONLY batch (claim/gap/variable renames)

**Files:** Modify `scientific_literature.py`, `tests/test_cli_realignment.py`.

Mechanical substitutions only (same shape). Apply the retired→new map to these handlers:
- `cmd_add_reported_claim` (3514-3555): `scilit-reported-claim`→`scilit-claim`; `scilit-claim-observation` role `reported-claim`→`claim`.
- `cmd_add_reported_gap` (3558-3579): `scilit-reported-gap`→`scilit-gap`.
- `cmd_add_mechanism` (3398): `scilit-reported-claim`→`scilit-claim`.
- `cmd_add_evidence` (3244,3249): `scilit-reported-claim`→`scilit-claim`.
- `cmd_add_datum` (4052): cell-variable `kefed-variable`→`ooevv-variable`.
- `_load_bundles` (2291,2293): confirm claim/gap grouping rels resolve (no type literals to change; verify).
- `_scale_of` (2409): `kefed-variable`→`ooevv-variable`.

- [ ] **Step 1: Failing tests** — call `cmd_add_reported_claim`/`cmd_add_reported_gap`/`cmd_add_datum` via a `SimpleNamespace` args against `authoring_db`, capture stdout JSON (`capsys`), and assert the inserted `scilit-claim`/`scilit-gap`/datum-cell round-trips by independent query. (These FAIL pre-change because the handlers insert retired type names.)
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Apply substitutions** (exact, per the map).
- [ ] **Step 4: Run** — tests pass.
- [ ] **Step 5: Commit** — `refactor(scilit): rename reported-claim/gap and kefed-variable in simple handlers`

---

## Task 4: KEfED bigraph authoring rework + delete obsolete slot commands

**Files:** Modify `scientific_literature.py`, `tests/test_cli_realignment.py`.

**Rework** (set-process/set-entity/kefed-element → `kefed-model-element`; role renames; template→model+state):
- `cmd_add_variable` (3732-3786): type→`ooevv-variable`, attr→`ooevv-variable-role`, grouping→`kefed-model-element(model,element)`, measurement produced-by roles→`produced-variable`/`producing-process`; `ctype` template branch→`kefed-model`+state.
- `cmd_add_process` (3671-3704): grouping `ooevv-set-process`→`kefed-model-element`; template branch→model+state; keep `ooevv-process-decomposition`/process subtypes.
- `cmd_link_entity` (3707-3729): keep `ooevv-process-input`/`-output`; grouping `ooevv-set-entity`→`kefed-model-element`.
- `cmd_bind_parameter` (3789-3808): `kefed-variable`→`ooevv-variable`; `ooevv-parameter-binding` role `binding-process`→`binding-bearer`.
- `cmd_add_experiment` (3652-3668): keep `kefed-model`; bundle grouping `ooevv-bundle-experiment`→`scilit-sensemaking-experiment(sensemaking,experiment)`.
- `cmd_ensure_template` (3815-3833) + `cmd_instantiate_template` (3982-4002): redesign onto `kefed-model`+`kefed-model-state`; `ooevv-instance-of` role `template`→`model`; instance bundle attach→`scilit-sensemaking-experiment`.

**DELETE (obsolete — slots gone):** `cmd_add_slot`, `cmd_param_slot`, `cmd_bind_slot` — remove the functions, their `add_parser(...)` blocks in `main()`, and their entries in the dispatch dict. Grep to confirm no remaining references.

- [ ] **Step 1: Failing tests** — drive a small bigraph through the real handlers against `authoring_db`: create a model, `cmd_add_process` (assay), `cmd_add_variable` (a measurement), `cmd_bind_parameter`, `cmd_add_experiment`; assert `kefed-model-element` membership, `ooevv-parameter-binding:binding-bearer`, and `scilit-sensemaking-experiment` all round-trip. Also assert the deleted subcommands are gone (e.g. `cmd_add_slot` not in the dispatch dict).
- [ ] **Step 2: Run, confirm FAIL.**
- [ ] **Step 3: Rework + delete** per above.
- [ ] **Step 4: Run** — tests pass; full `tests/test_cli_realignment.py` + `tests/test_schema_roundtrip.py` green.
- [ ] **Step 5: Commit** — `refactor(scilit): KEfED bigraph authoring on kefed-model-element; remove slot commands`

---

## Task 5: Observation/bundle authoring rework

**Files:** Modify `scientific_literature.py`, `tests/test_cli_realignment.py`.

- `cmd_add_observation` (3305-3362) — the largest rework. Currently inserts `kefed-model` + `kefed-observed-via` + per-var `kefed-variable`/`kefed-variable-role`/`kefed-value-set`/`kefed-element`. New: insert `scilit-observation` (knowledge-level/bio-scale) threaded under its bundle via `scilit-sensemaking-observation`; build/attach the KEfED frame as a `kefed-model` linked to the bundle via `scilit-sensemaking-experiment` with `ooevv-variable`s grouped by `kefed-model-element`; drop `kefed-observed-via`/`kefed-value-set`.
- `cmd_create_bundle` (3272-3302) — route its `iteration` arg through the new first-class `scilit-iteration` via `_ensure_phase_note` (which Task 6 makes iteration-aware); no retired type literal here but it depends on Task 6's helper.
- `cmd_ground_bundle` (3414-3511) — the target collector (3443-3451) walks `kefed-observed-via`+`kefed-element` and writes back `("kefed-variable", …)`; re-point to the new observation/variable wiring + `ooevv-variable`.

> Order note: Task 5 depends on Task 6's iteration-aware `_ensure_phase_note`. If executing strictly in order, do Task 6 BEFORE Task 5, or stub `cmd_create_bundle`'s iteration handling and finish it after Task 6. Recommended: swap execution order to 6 then 5.

- [ ] Steps 1-5 as before: failing test (create bundle → `cmd_add_observation` → assert `scilit-observation` threaded + KEfED frame via `scilit-sensemaking-experiment`, NO `kefed-observed-via`), confirm FAIL, rework, run, commit `refactor(scilit): observation/bundle authoring onto clean KEfED frame`.

---

## Task 6: Investigation iterations (authoring side)

**Files:** Modify `scientific_literature.py`, `tests/test_cli_realignment.py`.

Make the phasing chokepoint iteration-aware. New rule: a stage note belongs to a `scilit-iteration` (resolved/created by `scilit-iteration-index` under the investigation), linked via `scilit-iteration-stage`; the investigation owns iterations via `scilit-investigation-iteration`.
- `_ensure_phase_note` (1980-2003): resolve-or-create `scilit-iteration` (by index) under the investigation; create the `scilit-investigation-phase` and link via `scilit-iteration-stage`. Drop `scilit-investigation-phasing` + `scilit-iteration-number`.
- `cmd_record_phase` (2986-3042): existence check + upsert via the iteration path.
- `cmd_create_investigation` (2049-2129): seed iteration 1 (`scilit-iteration` index 1 + `scilit-investigation-iteration`).

- [ ] Steps 1-5: failing test (`cmd_create_investigation` then `cmd_record_phase --iteration 1 --phase discovery`; assert investigation→`scilit-iteration`(index 1)→`scilit-iteration-stage`→phase, NO `scilit-investigation-phasing`), confirm FAIL, rework, run, commit `feat(scilit): iteration-aware investigation/phase authoring`.

---

## Task 7: Read model rework — bundle/experiment/variable

**Files:** Modify `scientific_literature.py`, `tests/test_cli_realignment.py`.

Re-point readers (drop slot reads; role renames; `kefed-model-element`; new bundle-experiment rel):
- `_load_bundle` (2299-2364): per-observation frame `kefed-observed-via`+`kefed-model`+`kefed-element`/`kefed-variable-role`/`kefed-value-set` → new observation/frame wiring + `ooevv-variable`/`ooevv-variable-role`; reported-claim hinge `scilit-reported-claim`→`scilit-claim`.
- `_load_experiment` (2462-2497): process enum `ooevv-set-process`→`kefed-model-element`; `ooevv-parameter-binding` + `ooevv-produced-by` role renames; keep decomposition/input/output.
- `_var_brief` (2431-2459): `kefed-variable`→`ooevv-variable`, `kefed-variable-role`→`ooevv-variable-role`; DELETE the slot block (2453-2458).
- `_load_experiments` (2373-2383), `_load_instances` (2386-2404): `ooevv-bundle-experiment`→`scilit-sensemaking-experiment`.

- [ ] Steps 1-5: build a bundle+experiment via the Task 4/5 authoring, call `_load_bundle`/`_load_experiment`, assert the assembled dict has the expected processes/variables/parameters (and no slots); confirm FAIL first; commit `refactor(scilit): read model for bundle/experiment/variable on clean schema`.

---

## Task 8: Read model rework — template/instance/investigation + lists

**Files:** Modify `scientific_literature.py`, `tests/test_cli_realignment.py`.

- `_load_template` (2513-2535): `kefed-template`→`kefed-model`(state=template); DELETE slot reads (2525-2527); variables via `kefed-model-element`.
- `_load_instance` (2548-2594): keep `kefed-instance`; `ooevv-instance-of` role `template`→`model`; DELETE slot-binding block (2563-2569); data rows keep `ooevv-instance-datum`/`ooevv-cell`/`ooevv-datum-observation`; cell var `kefed-variable-role`→`ooevv-variable-role`.
- `_load_investigation` (2182-2265): `scilit-iteration-number`/`scilit-investigation-phasing` → traverse `scilit-investigation-iteration`→`scilit-iteration`(index)→`scilit-iteration-stage`; sort by iteration index.
- `_load_synthesized_claims` (2632-2637): grounding-instance join `ooevv-bundle-experiment`→`scilit-sensemaking-experiment`.
- `cmd_list_templates` (3884-3905): template filter on `kefed-model`+state; drop slot counts; process/var counts via `kefed-model-element`; instance count role rename.
- `cmd_audit_terms` (3949-3951): `TYPES` list `kefed-variable`→`ooevv-variable`; drop `kefed-template`/`kefed-slot`.

- [ ] Steps 1-5: round-trip a template/instance + an investigation with 1 iteration + 1 phase through authoring, call `_load_template`/`_load_instance`/`_load_investigation`, assert shapes (no slots; iteration-indexed phases); confirm FAIL first; commit `refactor(scilit): read model for template/instance/investigation + lists on clean schema`.

---

## Task 9: Retired-type guard + full gate

**Files:** Modify `tests/test_cli_realignment.py`.

- [ ] **Step 1: Guard test** — assert no retired type name appears in live TypeQL of `kqed.py` or `scientific_literature.py`. Read each file, strip `#` comment lines, and assert none of the retired names (`kefed-variable`, `kefed-element`, `kefed-observed-via`, `kefed-slot`, `kefed-template`, `kefed-template-slot`, `ooevv-param-slot`, `ooevv-slot-binding`, `ooevv-bundle-experiment`, `ooevv-set-process`, `ooevv-set-entity`, `scilit-reported-claim`, `scilit-reported-gap`, `kefed-value-set`, `scilit-iteration-number`, `scilit-investigation-phasing`) appear (use precise tokens; `kefed-model-element` must NOT trip a `kefed-element` check — match `'kefed-element'` only with a non-`-model-` left boundary, or check `"isa kefed-element"`/`":model)"` patterns).
- [ ] **Step 2: Full suite** — `uv run --python 3.12 pytest tests/ -v` — all pass (schema roundtrips + cli-realignment + pure-logic units).
- [ ] **Step 3: Commit** — `test(scilit): guard no retired types in CLI/kqed + full gate`

---

## Execution notes
- **Recommended order: 1, 2, 3, 4, 6, 5, 7, 8, 9** (Task 5 depends on Task 6's iteration-aware `_ensure_phase_note`).
- Each task: TDD (failing DB-backed test calling the REAL function → rework → green), commit only the touched files.

## Self-review
- Spec coverage: every handler in the Part-2 inventory (Clusters 1-4) maps to a task: renames→T3; bigraph authoring + obsolete-slot removal→T4; observation/bundle→T5; iterations→T6; reads→T7/T8; kqed→T2; successor relation + harness→T1; guard→T9.
- The one schema touch (`scilit-sensemaking-experiment`) is isolated in T1 and tested before any handler relies on it.
- Risk: `cmd_add_observation` (T5) is the largest single rework and couples to the iteration helper (T6) — order swapped accordingly. If T5 reveals the observation↔KEfED-frame wiring needs a schema tweak, STOP and escalate (it would change Plan-1 schema).
