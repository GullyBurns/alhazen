# Scilit Part 3b — RUNBOOK: in-place reconcile of `alh_deep_research` + re-curate SIRT3

> **This is a self-contained runbook for a FRESH session.** Read it top to bottom, then execute. It is the last phase of the scientific-literature reconfiguration. Everything BEFORE 3b (the code) is already done, reviewed, and on PR #7 — 3b only touches the LIVE database + curates data through the (already re-aligned) CLI verbs.

## 0. Orient first (do this before anything)
- **Work branch:** `feat/scilit-schema-reconfiguration` in the UPSTREAM skill repo `/Users/gullyburns/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/` (symlinked as `local_skills/scientific-literature`). HEAD should be `0d33677` or later. This is PR #7 (`sciknow-io/alhazen-skill-deep-research`).
- **Progress ledger (READ IT):** `/Users/gullyburns/skillful-alhazen/.superpowers/sdd/progress.md` — the full record of Parts 1/2/2b/3a. Trust it + `git log` over memory.
- **State of the code:** Part 1 (schema reconfiguration) + Part 2 (CLI/kqed re-alignment) + Plan 2b (kefed-model-node graph) + Plan 3a (definitions/element-set + data-signature verb + cleanup) are ALL complete and reviewed. **67/67 tests pass** (`cd <skill dir> && uv run --python 3.12 pytest tests/ -v`). The reconfigured `schema.tql` and the re-aligned CLI verbs are the clean model. 3b does NOT change code (except tiny fixups if a verb misbehaves during curation).
- **The clean model, in one breath:** OOEVV ElementSet = reusable vocabulary of definitions; a `kefed-model` is a graph of `kefed-model-node`s (each typed by an OOEVV def via `kefed-node-type`, carrying `ooevv-variable`s via `kefed-node-variable`); flow edges `ooevv-process-input`/`-output` connect nodes; `ooevv-subject` marks the source; traversing from a `measurement` variable's node collects its indexing parameters = the **data signature**; `kefed-instance` + `ooevv-datum`/`ooevv-cell` hold the data table + `scilit-warrant`; claims/gaps (`scilit-claim`/`scilit-gap`) are span-anchored via `alh-derivation` with an AZ property; an investigation owns first-class `scilit-iteration`s each with 5 stage notes. Full design: `docs/superpowers/specs/2026-06-29-scilit-kefed-ooevv-reconfiguration-design.md`.

## 1. Environment prereqs (verify, fix if needed)
- **typedb-driver MUST be <3.11** in whatever venv runs DB ops. The main repo `/Users/gullyburns/skillful-alhazen/.venv` was found stale at 3.11.5 (which breaks EVERY DB op with `DriverOptions.__init__() got an unexpected keyword argument 'is_tls_enabled'`). Fixed via `uv sync --all-extras` (→ 3.8.0). If you see that error again: `cd /Users/gullyburns/skillful-alhazen && uv sync --all-extras`. The skill's own venv is fine (3.10.0). Verify: `.venv/bin/python -c "import importlib.metadata as m; print(m.version('typedb-driver'))"`.
- TypeDB container `alhazen-typedb` running at `localhost:1729` (creds admin/password). Reconfigured-schema round-trip harness lives in the skill's `tests/`.

## 2. Current LIVE state of `alh_deep_research` (verified 2026-06-30)
This is the KEfED working DB (renamed from `alh_deep_research_ng` on Jun 29). It still runs the **OLD** schema.
- **KEEP (raw layer):** 549 `scilit-paper`, 3 `scilit-corpus`, ~2569 `alh-artifact` (+ their fragments/representations).
- **DELETE (old-schema curation layer):** ~849 `scilit-observation`, 418 `scilit-reported-claim`, 478 `kefed-model`, 387 `kefed-variable`, **1842 `kefed-instance`**, 1 `scilit-investigation`, plus fragments-as-curation / hinges / evidence / gaps / vocab-classifications specific to curation. (New types like `scilit-claim`/`scilit-gap`/`kefed-model-node` do NOT exist in the live DB yet.)
- **The SIRT3 paper `scilit-paper-a5c569d48e76` is NOT in this DB** — it must be re-ingested (step 4). It is the Cell Reports 2013 study "SIRT3 Reverses Aging-Associated Degeneration in Hematopoietic Stem Cells" (Brown/Chen et al.). Resolve its DOI/PMID at ingest time via `scilit ingest` (OpenAlex/PubMed) — do NOT hardcode a guessed DOI.
- **Latest safety snapshot:** `~/.alhazen/cache/typedb/alh_deep_research_export_20260630_232414.zip` (valid backup of the current DB; recover with `make db-import DB=alh_deep_research ZIP=<path>`). Take a FRESH one at step 3 anyway.

## 3. Step 1 — Fresh snapshot + verify (SAFETY, do first)
```
cd /Users/gullyburns/skillful-alhazen
make db-export DB=alh_deep_research           # -> ~/.alhazen/cache/typedb/alh_deep_research_export_<ts>.zip
ls -lt ~/.alhazen/cache/typedb/alh_deep_research_export_*.zip | head -2
```
Confirm the new zip exists and is non-trivial (~1MB+). This is your rollback (`make db-import DB=alh_deep_research ZIP=<path>`).

## 4. Step 2 — RECONCILE the schema in place (DESTRUCTIVE) — **test on a temp copy FIRST**
Approach A (Gully's choice): keep the raw layer, wipe the curation layer, swap the curation schema to the branch's clean `schema.tql`.

**MANDATORY: rehearse the whole reconcile on a temp copy before touching live.**
1. Import the snapshot into a throwaway DB, e.g. `alh_dr_reconcile_test` (use `typedb_notebook.py import-db`/`make db-import` targeting a temp name, or the driver `databases` API). 
2. Run steps (a)+(b)+(c) below against the temp DB; iterate the undefine until it loads clean and the raw layer is intact. ONLY when the temp rehearsal is clean, apply the identical sequence to live `alh_deep_research`.

**(a) Delete curation-layer instances (keep raw).** Delete relations first, then entities, for every curation type. The KEEP set (do NOT delete): core `alh-*` (person/role/vocab/artifact/fragment/representation/fragmentation/collection/collection-membership/classification/derivation/aboutness/note-threading), `scilit-paper`(+`scilit-review`/`scilit-protocol`/`scilit-preprint`), `scilit-corpus`, `scilit-session`, `scilit-dataset`, `scilit-book`, the artifact subtypes (`scilit-jats-fulltext`/`scilit-pdf-fulltext`/`scilit-citation-record`/`scilit-supplementary`/`scilit-structured-data`), the fragment subtypes (`scilit-section`/`figure`/`table`/`paragraph`/`sentence`/`equation`/`reference`), `alh-vocabulary`/`alh-vocabulary-type`/`scilit-ontology-term`. **Everything else `scilit-*`/`kefed-*`/`ooevv-*` = curation → delete.** Enumerate the live curation types by introspecting the loaded schema (query subtypes of the curation bases) or diff the old `schema.tql` (main branch) vs the KEEP set. A `delete $x;` per type (relations before entities) with a variable bound each time (never a variable-free match).

**(b) Undefine the old curation schema.** In TypeDB 3.x order: remove `owns`/`plays` first, then `sub`, then the type (see MEMORY.md "TypeDB 3.x Undefine Syntax"). This is the fiddly part — generate the undefine list from the live curation types (KEEP set excluded) and undefine leaf-first. If undefine of a specific type fights you, that's exactly why you rehearse on the temp DB.

**(c) Load the reconfigured schema.** 
```
TYPEDB_DATABASE=alh_deep_research uv run --project local_skills/alhazen-core \
  python local_skills/alhazen-core/alhazen_core.py load-schema \
  /Users/gullyburns/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/schema.tql
```
Expect `{"success": true, ..., "schema": "loaded"}`, no `[DEX*]`/`[SYR*]`. Then sanity-check: `match $p isa scilit-paper; ... count` still 549; `match $n isa kefed-model-node;` resolves (new type present); `scilit-claim`/`kefed-node-type`/`kefed-node-variable` resolve.

> If the in-place undefine proves intractable even on the temp copy, fall back is Approach B (fresh DB from `schema.tql` + re-import ONLY the raw layer via `src/skillful_alhazen/utils/subgraph_migrator.py copy --prefix scilit-paper/scilit-corpus ... --also-types <raw refs>`). Flag to Gully before switching approaches.

## 5. Step 3 — Re-ingest the SIRT3 paper
```
cd <skill dir>
uv run python scientific_literature.py ingest --doi "<resolve via search>"   # SIRT3 HSC-aging, Cell Reports 2013
# or:  ... ingest --pmid "<pmid>"
```
Confirm a `scilit-paper` now exists for it; note its id (it will be deterministic per `paper_identity`, NOT the old `scilit-paper-a5c569d48e76`). Optionally `fetch-pdf` for full text so claims can span-anchor to real fragments.

## 6. Step 4 — Re-curate SIRT3 on the clean model (via CLI verbs)
**Content source:** the OLD seed captured the full SIRT3 curation. Recover it read-only for the content (fragments, 5 experiments, observations, claims):
```
git -C /Users/gullyburns/Documents/GitHub/alhazen-skill-deep-research show \
  0d33677~1:skills/scientific-literature/prototypes/seed_sirt3_kqed.py
```
Re-express that content through the NEW verbs (get exact args via `uv run python scientific_literature.py <verb> --help`; cross-check the ledger + USAGE.md):
1. **Investigation + iteration:** `create-investigation --type ... --name "Hallmarks of aging (KQED) — SIRT3"` (seeds iteration 1); `record-phase --iteration 1 --phase discovery/ingest/...`.
2. **Per-paper sensemaking bundle:** `create-bundle --investigation <id> --paper <sirt3-paper-id> --iteration 1`.
3. **KEfED experiments as node graphs** (5 of them: expression-profiling, loss-of-function [WT vs SIRT3-KO], gain-of-function [lentiviral SIRT3 rescue], + the others in the seed): for each — `add-experiment` (kefed-model + element-set + bundle link); `add-entity-node --subject` for the study subject (HSC/mouse) with parameter variables (genotype WT|KO, age young|old, SIRT3-level control|overexpressed — ground to EFO); `add-process` for each assay (qPCR, western, flow cytometry, competitive transplantation, colony-forming); `link-nodes` subject→assay (role input); `add-variable --node <assay> --role measurement` for the readouts (expression, enzymatic activity, reconstitution %, ROS); `bind-parameter` where needed. Verify each with `show-data-signature --model <id>` (each measurement should index its condition parameters).
4. **Observations** (the seed's O1AC/O3E/O3G/O3IJ/O4DF…): `add-observation --bundle <id> --statement "..." --knowledge-level association|assertion --bio-scale molecular|tissue --source-label OF1A+C`. Pass the seed's code through `--source-label` (it becomes the note `name`; statement stays in `content`) — **rewrite legacy bare-figure codes to the explicit form** (`O4DF` → `OF4DF`) and use the non-figure forms where the evidence isn't a main figure (`OSF3B` supplemental, `OT2` table, `OE5` figure-less experiment, `OX` text-only). Grammar: `skills/scientific-literature/docs/observation-source-labeling.md`. Then span-anchor to the paper's fragment quotes (F5/F8/F10/F12… — via `kqed.add_fragment` + `ground_note`/`alh-derivation`).
5. **Claims/gaps:** `add-reported-claim` (now `scilit-claim`, AZ role) span-anchored to fragments; `add-reported-gap` for "future studies will determine the effect of SIRT3 on lifespan" (F13); hinges/mechanisms as in the seed.
6. **Instance + data table** where the seed had data rows: `instantiate-template`/instance + `add-datum --cells` (validated against the model's variables).

## 7. Step 5 — Verify
- `show-investigation`, `show-bundle`, `show-data-signature`, `show-instance` round-trip the SIRT3 record on the clean model.
- Counts: raw layer intact (549 papers); new curation types populated (`scilit-claim`, `kefed-model-node`, `kefed-node-variable`, `kefed-instance`); no `[INF2]` on any read verb.
- Full test suite still 67/67 (schema unchanged by data ops).
- Then re-snapshot: `make db-export DB=alh_deep_research`.

## 8. After SIRT3
Gully wants the rest of the previously-curated data reingested from scratch too — SIRT3 is the first exemplar / proof of the workflow. Once SIRT3 is clean, generalize the recipe (it's the same verb sequence per study) and work through the other studies. The whole PR (Parts 1–3b) can then move from draft → ready.

## Safety rules (non-negotiable)
- Snapshot before ANY destructive step; verify the zip; know the `make db-import` recovery.
- Rehearse the reconcile on a TEMP copy before live.
- Never a variable-free schema match (crashes TypeDB 3.8).
- Commit only intended files; the code side is frozen — 3b is data + at most tiny verb fixups (push those upstream on the branch, keep tests green).
- External skill: all code edits are in the upstream repo on `feat/scilit-schema-reconfiguration`.
