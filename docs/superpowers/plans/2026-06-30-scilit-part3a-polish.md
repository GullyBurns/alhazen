# Scilit Part 3a — definitions/element-set fix + data-signature verb + cleanup

> REQUIRED SUB-SKILL: superpowers:subagent-driven-development. Checkbox steps. Same branch `feat/scilit-schema-reconfiguration` (PR #7).

**Goal:** Land the pre-re-curation code polish: (1) make OOEVV definitions first-class — `kefed-model` owns `ooevv-definition`/`ooevv-long-form` and references its element-set via a real relation (retire the `eset-{mid}` name convention); (2) add a data-signature read verb + validate `add-datum --cells` against the model's variables; (3) retire obsolete prototype seeds + dead methods. All harness-tested; NO live-DB changes (that's 3b).

**Architecture:** TypeDB 3.8, inline TypeQL. Reuse the `scratch_db`/`authoring_db` harness. 3b (data teardown + SIRT3 re-curation on `alh_deep_research`) is a separate plan with a checkpoint.

## Global Constraints
- UPSTREAM repo `~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/`, branch `feat/scilit-schema-reconfiguration`. Commit ONLY named files per task (never `git add -A`; don't stage `dashboard/lib.ts`/`pyproject.toml`/`uv.lock`).
- TypeDB 3.x rules (keywords; relations before entities that play them; SVL42; ASCII comments; never a variable-free schema match; `value integer`).
- Retired-type guards must stay green (the node-model guard names must not regress).

---

## Task 1: Schema — model definitions + first-class element-set link
**Files:** `schema.tql`, `tests/test_schema_roundtrip.py`.
- Add `entity kefed-model owns ooevv-definition, owns ooevv-long-form;` (additive owns on the existing type).
- Add `relation kefed-model-elementset, relates model, relates element-set;` — `model` played by `kefed-model`, `element-set` played by `ooevv-element-set`. A model references exactly one element-set; an element-set MAY be shared by many models (reusable vocabulary).
- [ ] TDD: `test_model_definition_and_elementset` — create a `kefed-model` with `ooevv-definition`+`ooevv-long-form`; link it to an `ooevv-element-set` via `kefed-model-elementset`; a SECOND model links the SAME element-set; assert both models resolve the shared element-set and the definitions round-trip. RED → schema → GREEN + full `tests/test_schema_roundtrip.py`. Commit `feat(scilit): kefed-model definitions + first-class element-set relation`.

## Task 2: Authoring — use the element-set relation + persist definitions
**Files:** `scientific_literature.py`, `kqed.py`, `tests/test_cli_realignment.py`.
- `cmd_add_experiment`/`cmd_ensure_template`: create-or-reference an `ooevv-element-set`, link via `kefed-model-elementset` (replace the `eset-{model_id}` naming convention); persist `--definition`/`--long-form` onto the `kefed-model` (they are currently dropped). Allow `--element-set <id>` to REUSE an existing set.
- `cmd_add_process`/`cmd_add_entity_node`/`cmd_add_variable`: find-or-create OOEVV defs in the model's element-set resolved via `kefed-model-elementset` (not `eset-{mid}`).
- `kqed.add_kefed_model`: same — link the element-set via the relation; carry a definition.
- [ ] TDD: author two models sharing one element-set via the relation + a defined template; assert defs persist and a def created for model A is reused (found) when model B (same element-set) adds a process of that type. Commit `refactor(scilit): author via kefed-model-elementset relation; persist model definitions`.

## Task 3: Data-signature read verb + add-datum validation
**Files:** `scientific_literature.py`, `tests/test_cli_realignment.py`.
- New read helper `_data_signature(tx, model_id)`: for each `measurement`-role `ooevv-variable` on a node in the model, traverse the flow edges (`ooevv-process-input`/`-output`) upstream/across to collect the `parameter`/`constant`-role variables reachable — the measurement's **index set**. Return `{measurement_var_id: {name, index: [param_var...]}}`.
- New verb `cmd_show_data_signature` (`show-data-signature --model <id>` / or `--experiment`): print the signature JSON. Wire into argparse + dispatch.
- `cmd_add_datum`: validate that every `--cells` variable id belongs to the instance's model (via node→variable), erroring clearly on an unknown variable id.
- [ ] TDD: author a model (subject entity node with a parameter → assay node with a measurement, flow-linked); call `_data_signature`/`cmd_show_data_signature` → assert the measurement's index includes the parameter. Author an instance + `cmd_add_datum` with a bogus cell var id → assert it errors; with valid ids → succeeds. Commit `feat(scilit): data-signature read verb + add-datum cell validation`.

## Task 4: Retire obsolete methods/prototypes + guard/gate
**Files:** `scientific_literature.py`, `kqed.py`, `prototypes/*` (delete obsolete), `tests/*`.
- Delete/retire obsolete prototype seeds that call old signatures and are superseded (`prototypes/seed_sirt3_kqed.py` if it will be replaced by CLI re-curation in 3b — confirm; `import_deepdive.py`/`run_deepdive_import.py` if dead). Remove any dead helper methods left from the old bigraph/slot model (grep for unreferenced `cmd_*`/`_load_*` that no dispatch entry or caller uses).
- Update the CLI guard to also assert the `eset-` name-convention string is gone from live TypeQL (now that the relation replaces it), if practical.
- [ ] Run FULL suite `uv run --python 3.12 pytest tests/ -v` — all green. Commit `chore(scilit): retire obsolete seeds/methods + gate`.

## Verification
- Full suite green; a model authored with a definition + shared element-set; `show-data-signature` returns each measurement's indexing parameters; `add-datum` rejects unknown cell variables.

## Then: Part 3b (separate, checkpoint first)
`db-export` snapshot of `alh_deep_research` → drop the old curation-layer instances + load the reconfigured schema → re-curate the SIRT3 experiment end-to-end through the CLI verbs (element-set + defs, node graph subject→assay→measured vars, instance + data table, span-anchored claims, iteration/stage) → verify counts + a `show-data-signature`/`show-instance` round-trip. Destructive on the live DB — get Gully's go-ahead before running.
