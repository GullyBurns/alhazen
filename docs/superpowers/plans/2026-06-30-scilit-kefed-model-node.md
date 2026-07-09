# Scilit KEfED model-node redesign (Sub-project 1, Plan 2b) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps.

**Goal:** Make a `kefed-model` a graph of **`kefed-model-node`s** — each node typed by an OOEVV definition and carrying its variables — instead of putting OOEVV definition types directly into the bigraph. This resolves the entity-authoring blocker (only `ooevv-material-entity` could play bigraph roles; nothing created it or the subject) and makes the model a clean node graph whose traversal yields the data-table signature.

**Architecture:** Two layers. (1) **Definitions** = the OOEVV ElementSet vocabulary (`ooevv-material-entity`, `ooevv-process`/subtypes, `ooevv-quality`, `ooevv-variable`, scales) — reusable *types*; they STOP playing bigraph roles and instead are referenced as a node's type. (2) **Graph** = `kefed-model` groups `kefed-model-node`s; each node links to its OOEVV type and carries `ooevv-variable`s; flow edges connect nodes; the subject is the source node. Revises Part-1 schema + Part-2 bigraph authoring/reads on the same branch (`feat/scilit-schema-reconfiguration`, PR #7). The claim/rhetorical/iteration/instance-data layers are unchanged.

**Tech Stack:** TypeDB 3.8, `typedb-driver>=3.8.0,<3.11`, Python 3.12, uv, pytest. Reuse the `scratch_db`/`authoring_db` harness + `w`/`r` helpers.

## Global Constraints
- UPSTREAM repo `~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/`, branch `feat/scilit-schema-reconfiguration`. Commit ONLY the named files per task (never `git add -A`; don't stage `dashboard/lib.ts`/`pyproject.toml`/`uv.lock`).
- TypeDB 3.x: `entity`/`relation`/`attribute` keywords; relations before entities that play them; subtypes do NOT redeclare inherited plays (SVL42); never a variable-free schema match; ASCII comments; `value integer` not `long`.
- Target schema (names chosen):
  - `entity kefed-model-node sub alh-domain-thing` — a node in a model graph.
  - `relation kefed-node-type, relates node, relates node-type;` — node-type played by `ooevv-material-entity` + `ooevv-process` (subtypes inherit).
  - `relation kefed-node-variable, relates node, relates variable;` — variable played by `ooevv-variable`. Folds in the retired `ooevv-parameter-binding` + `ooevv-produced-by`.
  - `kefed-model-element(model, element)` — `element` now played by `kefed-model-node` (NOT ooevv-process/variable).
  - `ooevv-subject(model, subject-node)`, `ooevv-process-input(input-node, consuming-node)`, `ooevv-process-output(producing-node, output-node)` — all node-played.
  - RETIRE: `ooevv-parameter-binding`, `ooevv-produced-by`, and the direct bigraph `plays` on `ooevv-material-entity`/`ooevv-process`/`ooevv-variable` (they keep `ooevv-set-element:element`, `ooevv-measures`, `ooevv-has-scale`, and gain `kefed-node-type:node-type` / `kefed-node-variable:variable`).
  - KEEP unchanged: `ooevv-cell(datum, cell-variable)` (cell-variable still `ooevv-variable`), `ooevv-instance-*`, `ooevv-datum-observation`, `ooevv-parameter-target` (optional — retarget `targeting-parameter`=`ooevv-variable`, `target-entity`→`target-node`=`kefed-model-node` if kept; else drop).

---

## Task 1: Schema — kefed-model-node graph
**Files:** `schema.tql`, `tests/test_schema_roundtrip.py`.
**Produces:** `kefed-model-node`; relations `kefed-node-type`, `kefed-node-variable`; node-played `kefed-model-element`/`ooevv-subject`/`ooevv-process-input`/`ooevv-process-output`.

- [ ] **Step 1: Failing test** — add `test_kefed_model_node_graph`: create a `kefed-model`; a node typed as a material-entity (`kefed-node-type` → an `ooevv-material-entity` def) as the subject (`ooevv-subject`); a node typed as an assay; link them via `ooevv-process-input(input-node, consuming-node)`; attach a `measurement` `ooevv-variable` to the assay node via `kefed-node-variable` and a `parameter` variable to the subject node; assert: model→node membership, node→type, node→variable(role), and the input edge, all round-trip. (This is the data-signature scaffold: measurement node ← flow ← parameter node.)
- [ ] **Step 2: Run → FAIL** (`kefed-model-node`/`kefed-node-type`/`kefed-node-variable` undefined).
- [ ] **Step 3: Schema** — add `kefed-model-node` + the relations; move the bigraph `plays` from `ooevv-material-entity`/`ooevv-process`/`ooevv-variable` onto `kefed-model-node`; give the OOEVV defs `plays kefed-node-type:node-type` (material-entity + process) and `ooevv-variable plays kefed-node-variable:variable`; RETIRE `ooevv-parameter-binding` + `ooevv-produced-by` (and every `plays` of them — grep). Whole file must load (all prior roundtrip tests pass).
- [ ] **Step 4: Run → PASS** (new test + all `tests/test_schema_roundtrip.py`).
- [ ] **Step 5: Commit** `schema.tql` + test: `feat(scilit): kefed-model-node graph (nodes typed by OOEVV defs, carry variables)`.

## Task 2: Authoring — build node graphs
**Files:** `scientific_literature.py`, `kqed.py`, `tests/test_cli_realignment.py`.
Re-align the bigraph authoring to create nodes typed by OOEVV definitions and attach variables:
- `cmd_add_process`: find-or-create the OOEVV process *definition* (an `ooevv-assay`/… by name) in the model's element-set, then create a `kefed-model-node` typed by it (`kefed-node-type`) and add it to the model (`kefed-model-element`).
- New `cmd_add-node`/`cmd_set-subject` (pick): create an entity node typed by an `ooevv-material-entity` def; mark it the model's subject (`ooevv-subject`).
- `cmd_link_entity` → connect two `kefed-model-node`s via `ooevv-process-input`/`ooevv-process-output` (node↔node), NOT `scilit-entity`.
- `cmd_add_variable`: create/find an `ooevv-variable` def and attach it to a node via `kefed-node-variable` (drop `kefed-model-element` for variables + the retired `ooevv-produced-by`).
- `cmd_bind_parameter`: a parameter is a `parameter`-role variable attached to a node (`kefed-node-variable`); keep `ooevv-parameter-target` only if retained in Task 1.
- `kqed.add_kefed_model`: build a model + its subject node + variable-bearing nodes.
- [ ] TDD: author a small graph via the real verbs (subject entity node → assay node with a measurement variable + a parameter), assert the node graph + data-signature traversal round-trips; delete/replace the now-invalid bigraph inserts. Commit (named files only): `refactor(scilit): author kefed-model-node graphs`.

## Task 3: Reads — traverse nodes
**Files:** `scientific_literature.py`, `tests/test_cli_realignment.py`.
- `_load_experiment`: enumerate the model's nodes (`kefed-model-element`), each with its OOEVV type (`kefed-node-type`) + attached variables (`kefed-node-variable`, with roles) + flow edges (`ooevv-process-input`/`-output`) + the subject; assemble a node-graph dict. Drop the retired `ooevv-parameter-binding`/`ooevv-produced-by` reads.
- `_var_brief` (and any variable reader): read variables via `kefed-node-variable`.
- [ ] TDD: author a graph, `_load_experiment` → assert nodes/types/variables/edges/subject present. Commit: `refactor(scilit): read kefed-model-node graphs`.

## Task 4: Guard + gate
**Files:** `tests/test_cli_realignment.py`, `tests/test_schema_roundtrip.py` (guard only).
- [ ] Add `ooevv-parameter-binding`/`ooevv-produced-by` to the retired-type guards (both the schema guard and the CLI guard). Run the FULL suite `uv run --python 3.12 pytest tests/ -v` — all green. Commit: `test(scilit): guard retired bigraph relations + full gate`.

## Verification
- Full suite green; a worked node-graph (subject → assay → measurement, with a parameter) authored and read back via the real verbs; data-signature traversal (measurement node ← flow ← parameter) returns the parameter.

## Self-review
Covers: node entity + typing + variable attachment (T1); authoring incl. subject + node edges (T2); node-graph reads (T3); retired-relation guard (T4). The instance/data-cell layer (`ooevv-cell`) is unchanged — cells still reference `ooevv-variable`s, now node-attached. `scilit-entity` is no longer forced into the bigraph; it remains the grounded rhetorical/mechanism entity.
