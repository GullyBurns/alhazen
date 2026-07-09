# Scilit Schema Reconfiguration (Sub-project 1, Plan 1 of 3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the muddled OOEVV/KEfED/KQED/investigation blocks of the scientific-literature
`schema.tql` with the clean model from the design spec — OOEVV ElementSet as a first-class vocabulary,
`kefed-model` as just the bigraph, template = uninstantiated model, typed data-transformations with
parameter-mapping rules, span-anchored rhetorical claims, and first-class investigation iterations —
validated by a scratch-DB round-trip harness.

**Architecture:** TypeDB 3.8 schema (TypeQL). The reconfigured types live in the scilit namespace
(`ooevv-*`, `kefed-*`, `scilit-*`) as subtypes of core `alh-*` bases. We validate each layer by loading
the schema into a throwaway DB via `alhazen-core` and asserting a minimal insert/match round-trip — the
existing pure-logic unit tests stay untouched; this plan adds the first DB-backed tests.

**Tech Stack:** TypeDB 3.8.0, `typedb-driver>=3.8.0,<3.11`, Python 3.12, `uv`, pytest. Schema loaded via
`alhazen-core`'s `alhazen_core.py {init,load-schema}`.

## Global Constraints

- **Upstream repo:** all edits are in `~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/`
  (the `local_skills/scientific-literature` symlink target). External-skill fixes go upstream; push there.
- **TypeDB 3.x syntax (verbatim rules):** entity defs REQUIRE the `entity` keyword; relations declared
  top-level as `relation X,` (never `sub relation`); attributes as `attribute X, value T;`; integers are
  `value integer` (never `long`); no `@key` on custom attributes (only inherited `id @key`); declare
  relations BEFORE the entities that `plays` their roles; subtypes must RE-declare `plays` (not inherited);
  `@abstract` only on a subtype whose supertype is also abstract (`alh-domain-thing` is concrete);
  ASCII-only in comments (no `->`, `°`, etc.).
- **Never run a variable-free schema match** (`match X sub Y;` with two concrete labels) — it crashes the
  server. Always bind a variable: `match $t sub ooevv-element;`.
- **Back up before any reload of a real DB:** `make db-export` first. This plan only writes to a SCRATCH DB
  (`alh_scilit_schema_test`), so live `alh_deep_research` is never touched — but the teardown plan (Plan 3)
  will require the backup.
- **CURIE grounding defaults (spec §6):** material-entity `obo:BFO_0000040`; ICE/variable `obo:IAO_0000030`;
  process `obo:BFO_0000015`; assay `obo:OBI_0000070`; material-processing `obo:OBI_0000094`;
  data-transformation `obo:OBI_0200000`; measurement `obo:IAO_0000109`; variable *definitions* ground to
  **EFO** factor terms (via `kefed-efo-label`). Scales keep OOEVV's own taxonomy. Each element type carries
  its upper-ontology CURIE via the existing `scilit-curie` slot; these are recorded as comments on the type
  and (for instances) populated at curation time.

---

## File structure

- `schema.tql` — the reconfigured OOEVV/KEfED/KQED/investigation blocks (current lines ~422-963 replaced).
  Single file; one responsibility (the scilit schema). We replace the muddled blocks in place.
- `tests/conftest.py` — **new**: a `scratch_db` pytest fixture that provisions a throwaway TypeDB database
  with the core + scilit schema and yields a driver, dropping the DB on teardown.
- `tests/test_schema_roundtrip.py` — **new**: one DB-backed round-trip test per schema layer, asserting the
  new types insert and match. This is the executable spec of the reconfigured schema.

The old types we retire (`kefed-slot`, `kefed-observed-via`, the ElementSet-fused `kefed-model` wiring,
the prototype `kefed-model`/`kefed-variable` duplication, `scilit-claim`/`scilit-gap` legacy aliases) are
removed from `schema.tql` as part of the layer tasks that supersede them; the DATA teardown is Plan 3.

---

## Task 1: Scratch-DB round-trip test harness

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_schema_roundtrip.py`

**Interfaces:**
- Produces: pytest fixture `scratch_db` → yields a `typedb` driver connected to a freshly-provisioned
  `alh_scilit_schema_test` DB (core `alh-` schema + the current `schema.tql`), dropped on teardown.
  Helpers `w(driver, q)` (write+commit) and `r(driver, q)` (read→list of rows), same signatures as `kqed.py`.

- [ ] **Step 1: Write the fixture and helpers**

Create `tests/conftest.py`:

```python
import os, subprocess, pytest
from pathlib import Path
from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType

SKILL_DIR = Path(__file__).resolve().parent.parent
SCRATCH_DB = "alh_scilit_schema_test"

def _alhazen_core():
    # Resolve alhazen-core's alhazen_core.py from the local registry build.
    for c in [
        SKILL_DIR.parent / "alhazen-core" / "alhazen_core.py",
        Path.home() / "skillful-alhazen" / "local_skills" / "alhazen-core" / "alhazen_core.py",
        Path.home() / "skillful-alhazen" / ".claude" / "skills" / "alhazen-core" / "alhazen_core.py",
    ]:
        if c.exists():
            return c
    raise RuntimeError("alhazen-core not found; build the registry (make build-skills) first")

def _run_core(*args):
    core = _alhazen_core()
    env = {**os.environ, "TYPEDB_DATABASE": SCRATCH_DB, "PYTHONWARNINGS": "ignore::SyntaxWarning"}
    env.pop("VIRTUAL_ENV", None)
    subprocess.run(["uv", "run", "--project", str(core.parent), "python", str(core), *args],
                   check=True, env=env, capture_output=True, text=True)

def _driver():
    return TypeDB.driver("localhost:1729", Credentials("admin", "password"),
                         DriverOptions(is_tls_enabled=False))

@pytest.fixture
def scratch_db():
    # Drop any stale scratch DB, then provision core + scilit schema fresh.
    d = _driver()
    if d.databases.contains(SCRATCH_DB):
        d.databases.get(SCRATCH_DB).delete()
    d.close()
    _run_core("init")                                   # creates DB + core alh- schema
    _run_core("load-schema", str(SKILL_DIR / "schema.tql"))
    d = _driver()
    try:
        yield d
    finally:
        d.close()
        d2 = _driver()
        if d2.databases.contains(SCRATCH_DB):
            d2.databases.get(SCRATCH_DB).delete()
        d2.close()

def w(driver, q):
    with driver.transaction(SCRATCH_DB, TransactionType.WRITE) as tx:
        tx.query(q).resolve(); tx.commit()

def r(driver, q):
    with driver.transaction(SCRATCH_DB, TransactionType.READ) as tx:
        return list(tx.query(q).resolve())
```

- [ ] **Step 2: Write a smoke test that the harness provisions and the CURRENT schema loads**

Create `tests/test_schema_roundtrip.py`:

```python
from conftest import w, r

def test_harness_loads_current_schema(scratch_db):
    # scilit-paper already exists in the current schema; a round-trip proves the harness works.
    w(scratch_db, 'insert $p isa scilit-paper, has id "scilit-paper-smoke", has name "smoke";')
    rows = r(scratch_db, 'match $p isa scilit-paper, has id "scilit-paper-smoke", has name $n; fetch {"n": $n};')
    assert rows and rows[0]["n"] == "smoke"
```

- [ ] **Step 3: Run it to verify the harness works against today's schema**

Run: `cd ~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature && uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_harness_loads_current_schema -v`
Expected: PASS (proves provisioning + round-trip; if it errors on the scilit-paper insert, the harness is wrong, not the schema).

- [ ] **Step 4: Commit**

```bash
git add tests/conftest.py tests/test_schema_roundtrip.py
git commit -m "test(scilit): scratch-DB schema round-trip harness"
```

---

## Task 2: OOEVV vocabulary layer — ElementSet + elements

Replace the OOEVV element definitions so an **ElementSet** is a first-class vocabulary object grouping
its **entities** (material vs ICE), **processes** (assay/material-processing/data-transformation),
**variables** (constant/parameter/measurement), and **scales**.

**Files:**
- Modify: `schema.tql` — replace the OOEVV element/entity definitions in the `# OOEVV + KEfED PROTOCOL-GRAPH`
  block (current lines ~754-856); KEEP the scale subtypes (`ooevv-nominal-scale` etc., lines ~821-830) and
  the `ooevv-*` attributes (`ooevv-definition/unit/min/max/allowed-value/named-rank`, lines ~763-768).
- Modify: `tests/test_schema_roundtrip.py` — add the layer test.

**Interfaces:**
- Produces (new types later tasks build on): `ooevv-element-set`, `ooevv-element` (base),
  `ooevv-material-entity`, `ooevv-variable` (owns `ooevv-variable-role`, `ooevv-ice-kind`, `kefed-efo-label`),
  `ooevv-process` + subtypes `ooevv-assay` / `ooevv-material-processing` / `ooevv-data-transformation`,
  `ooevv-scale` (+ existing subtypes). Relation `ooevv-set-element(element-set, element)`.

- [ ] **Step 1: Write the failing layer test**

Add to `tests/test_schema_roundtrip.py`:

```python
def test_ooevv_elementset_and_elements(scratch_db):
    w(scratch_db,
      'insert $s isa ooevv-element-set, has id "ooevv-es-rnaseq", has name "RNASeq",'
      '  has ooevv-definition "vocabulary for RNASeq experiments";')
    # a material entity, a measurement variable, an assay process, a numeric scale, all in the set
    w(scratch_db,
      'match $s isa ooevv-element-set, has id "ooevv-es-rnaseq";'
      'insert $m isa ooevv-material-entity, has id "ooevv-me-mouse", has name "mouse";'
      ' (element-set: $s, element: $m) isa ooevv-set-element;')
    w(scratch_db,
      'match $s isa ooevv-element-set, has id "ooevv-es-rnaseq";'
      'insert $v isa ooevv-variable, has id "ooevv-var-expr", has name "expression",'
      '  has ooevv-variable-role "measurement", has ooevv-ice-kind "measurement",'
      '  has kefed-efo-label "EFO:0000001";'
      ' (element-set: $s, element: $v) isa ooevv-set-element;')
    w(scratch_db,
      'match $s isa ooevv-element-set, has id "ooevv-es-rnaseq";'
      'insert $a isa ooevv-assay, has id "ooevv-assay-qpcr", has name "qPCR";'
      ' (element-set: $s, element: $a) isa ooevv-set-element;')
    rows = r(scratch_db,
      'match $s isa ooevv-element-set, has id "ooevv-es-rnaseq";'
      ' (element-set: $s, element: $e) isa ooevv-set-element; $e has name $n; fetch {"n": $n};')
    names = sorted(x["n"] for x in rows)
    assert names == ["expression", "mouse", "qPCR"]
    # role + ice-kind round-trip on the variable
    vr = r(scratch_db, 'match $v isa ooevv-variable, has id "ooevv-var-expr", has ooevv-variable-role $role,'
                       ' has ooevv-ice-kind $k; fetch {"role": $role, "k": $k};')
    assert vr[0]["role"] == "measurement" and vr[0]["k"] == "measurement"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_ooevv_elementset_and_elements -v`
Expected: FAIL — `ooevv-element-set` / `ooevv-material-entity` / `ooevv-variable` types do not exist yet.

- [ ] **Step 3: Add the schema (replace the OOEVV element block)**

In `schema.tql`, within the OOEVV protocol-graph block, add these BEFORE the entities (relations first),
and replace the old `ooevv-quality`/`ooevv-process`/standalone-entity definitions:

```tql
# --- OOEVV element vocabulary (ontological commitment for a class of experiments) ---
attribute ooevv-variable-role, value string;   # constant | parameter | measurement
attribute ooevv-ice-kind, value string;        # measurement | derived (for ICE variables in the bigraph)

relation ooevv-set-element,                     # an element-set groups its elements
    relates element-set, relates element;

# ELEMENT - base for everything an element-set contains. (concrete parent -> not @abstract)
entity ooevv-element sub alh-domain-thing,
    owns ooevv-definition, owns ooevv-long-form, owns scilit-curie,
    plays ooevv-set-element:element;

# ELEMENT-SET - the reusable vocabulary commitment for a CLASS of experiments (e.g. "RNASeq").
entity ooevv-element-set sub alh-artifact,
    owns ooevv-definition,
    plays ooevv-set-element:element-set;

# ENTITY split: material entity (obo:BFO_0000040) vs information content entity (obo:IAO_0000030).
entity ooevv-material-entity sub ooevv-element;        # obo:BFO_0000040
# VARIABLE - an ICE that takes values (obo:IAO_0000030); definitions ground to EFO via kefed-efo-label.
entity ooevv-variable sub ooevv-element,               # obo:IAO_0000030
    owns ooevv-variable-role,
    owns ooevv-ice-kind,
    owns kefed-efo-label,
    owns scilit-grounding-label, owns scilit-grounding-state, owns scilit-grounding-confidence,
    plays ooevv-measures:measured-variable,
    plays ooevv-has-scale:scaled-variable,
    plays ooevv-scale-parts:part-variable;

# PROCESS - a protocol step (obo:BFO_0000015); subtypes carry their OBI curie.
entity ooevv-process sub ooevv-element;                # obo:BFO_0000015
entity ooevv-assay sub ooevv-process;                  # obo:OBI_0000070
entity ooevv-material-processing sub ooevv-process;    # obo:OBI_0000094
entity ooevv-data-transformation sub ooevv-process;    # obo:OBI_0200000

# SCALE - the computational type of a variable's values (keep OOEVV's own taxonomy).
entity ooevv-scale sub ooevv-element,
    owns ooevv-unit,
    plays ooevv-has-scale:scale;
entity ooevv-nominal-scale sub ooevv-scale, owns ooevv-allowed-value @card(0..);
entity ooevv-binary-scale sub ooevv-scale, owns ooevv-allowed-value @card(0..);
entity ooevv-ordinal-scale sub ooevv-scale, owns ooevv-named-rank @card(0..);
entity ooevv-numeric-scale sub ooevv-scale, owns ooevv-min, owns ooevv-max;
entity ooevv-file-scale sub ooevv-scale;
entity ooevv-composite-scale sub ooevv-scale, plays ooevv-scale-parts:composite-scale;
```

Keep the existing `ooevv-measures` / `ooevv-has-scale` / `ooevv-scale-parts` relations (they still apply,
now to `ooevv-variable`). Remove the old `ooevv-quality` entity and the old standalone `ooevv-process`
plays-list (the bigraph plays are re-added in Task 3). Delete the `kefed-variable`-based plays-extensions
at lines ~833-856 (superseded by `ooevv-variable`).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_ooevv_elementset_and_elements -v`
Expected: PASS. (If TypeDB reports an unresolved `plays`, ensure the `ooevv-measures`/`ooevv-has-scale`/
`ooevv-scale-parts` relations are declared above these entities.)

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "feat(scilit): OOEVV element-set + element vocabulary (un-fuse from kefed-model)"
```

---

## Task 3: KEfED model — the entity-process bigraph

Define `kefed-model` as **just the bigraph** (built from one element-set): material-flow I/O edges,
parameter binding on BOTH entities and processes, an explicit subject role, and measurement-vs-derived
ICE typing via the producing process.

**Files:**
- Modify: `schema.tql` — replace `kefed-model`/`kefed-element`/`kefed-observed-via` (lines ~440-447, 513-529)
  and the protocol-graph relations (lines ~778-796) with the bigraph below.
- Modify: `tests/test_schema_roundtrip.py`.

**Interfaces:**
- Produces: `kefed-model` (entity, sub `alh-artifact`); relations `kefed-model-element(model, element)`,
  `ooevv-process-input(input-entity, consuming-process)`, `ooevv-process-output(producing-process, output-entity)`,
  `ooevv-parameter-binding(binding-bearer, bound-parameter)` where `binding-bearer` is played by BOTH
  `ooevv-process` AND `ooevv-material-entity`, `ooevv-subject(model, subject-entity)`.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_schema_roundtrip.py`:

```python
def _seed_elementset(db):
    w(db, 'insert $s isa ooevv-element-set, has id "ooevv-es-x", has name "X";')

def test_kefed_bigraph(scratch_db):
    _seed_elementset(scratch_db)
    # model + subject material entity + a manipulation process + a measurement variable
    w(scratch_db, 'insert $m isa kefed-model, has id "kefedm-1", has name "qPCR run",'
                  '  has content "protocol", has format "kefed-bigraph";')
    w(scratch_db, 'match $m isa kefed-model, has id "kefedm-1";'
                  'insert $subj isa ooevv-material-entity, has id "me-subj", has name "mouse";'
                  ' (model: $m, subject-entity: $subj) isa ooevv-subject;')
    w(scratch_db, 'match $subj isa ooevv-material-entity, has id "me-subj";'
                  'insert $p isa ooevv-material-processing, has id "mp-1", has name "knockout";'
                  ' (input-entity: $subj, consuming-process: $p) isa ooevv-process-input;')
    # a treatment parameter bound at the manipulation process AND a genotype param on the entity
    w(scratch_db, 'match $p isa ooevv-material-processing, has id "mp-1";'
                  'insert $par isa ooevv-variable, has id "var-treat", has name "treatment",'
                  '  has ooevv-variable-role "parameter";'
                  ' (binding-bearer: $p, bound-parameter: $par) isa ooevv-parameter-binding;')
    w(scratch_db, 'match $subj isa ooevv-material-entity, has id "me-subj";'
                  'insert $g isa ooevv-variable, has id "var-geno", has name "genotype",'
                  '  has ooevv-variable-role "parameter";'
                  ' (binding-bearer: $subj, bound-parameter: $g) isa ooevv-parameter-binding;')
    # subject reads back
    sj = r(scratch_db, 'match $m isa kefed-model, has id "kefedm-1";'
                       ' (model: $m, subject-entity: $e) isa ooevv-subject; $e has name $n; fetch {"n": $n};')
    assert sj[0]["n"] == "mouse"
    # BOTH a process and an entity bear a parameter
    bearers = r(scratch_db, 'match (binding-bearer: $b, bound-parameter: $par) isa ooevv-parameter-binding;'
                            ' $par has name $pn; fetch {"pn": $pn};')
    assert sorted(x["pn"] for x in bearers) == ["genotype", "treatment"]
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_kefed_bigraph -v`
Expected: FAIL — `kefed-model` bigraph roles / `ooevv-subject` / dual `binding-bearer` not defined.

- [ ] **Step 3: Add the schema (the bigraph)**

In `schema.tql`, replace the old `kefed-element`/`kefed-observed-via`/`kefed-model`/`kefed-variable`
definitions and the old protocol-graph relations with:

```tql
# --- KEfED bigraph: entities <-> processes, parameters borne by both ---
relation kefed-model-element,                   # a model groups the elements that form its bigraph
    relates model, relates element;
relation ooevv-subject,                         # the model's SOURCE node (experimental subject)
    relates model, relates subject-entity;
relation ooevv-process-input,                   # material flow: entity consumed by a process
    relates input-entity, relates consuming-process;
relation ooevv-process-output,                  # material flow: entity produced by a process
    relates producing-process, relates output-entity;
relation ooevv-parameter-binding,               # a parameter is set ON a process OR an entity (KEfED dependency)
    relates binding-bearer, relates bound-parameter;
relation ooevv-parameter-target,                # a parameter's value targets a curated entity (specificity)
    relates targeting-parameter, relates target-entity;
relation ooevv-produced-by,                     # a measurement/derived variable is produced by a process
    relates produced-variable, relates producing-process;

# KEFED-MODEL - the bigraph (built from one element-set). No ElementSet fusion, no slots.
entity kefed-model sub alh-artifact,
    plays kefed-model-element:model,
    plays ooevv-subject:model;

# bigraph plays for processes/entities/variables
entity ooevv-process
    plays kefed-model-element:element,
    plays ooevv-process-input:consuming-process,
    plays ooevv-process-output:producing-process,
    plays ooevv-parameter-binding:binding-bearer,
    plays ooevv-produced-by:producing-process;
entity ooevv-material-entity
    plays kefed-model-element:element,
    plays ooevv-subject:subject-entity,
    plays ooevv-process-input:input-entity,
    plays ooevv-process-output:output-entity,
    plays ooevv-parameter-binding:binding-bearer,   # entities ALSO bear parameters
    plays ooevv-parameter-target:target-entity;
entity ooevv-variable
    plays kefed-model-element:element,
    plays ooevv-parameter-binding:bound-parameter,
    plays ooevv-parameter-target:targeting-parameter,
    plays ooevv-produced-by:produced-variable;
```

Delete `kefed-variable`, `kefed-element`, `kefed-observed-via`, `kefed-variable-role`, `kefed-value-set`
(superseded by `ooevv-variable` + `ooevv-variable-role`). Keep `kefed-efo-label` (now owned by `ooevv-variable`).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_kefed_bigraph -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "feat(scilit): kefed-model as entity-process bigraph; parameters on entities and processes; subject role"
```

---

## Task 4: Data-transformation parameter-mapping rules

A `ooevv-data-transformation` declares typed rules for how its input parameters map to output parameters,
so a derived datum's index composes through the workflow (full provenance).

**Files:**
- Modify: `schema.tql` — add the mapping-rule relation + attribute near the process definitions.
- Modify: `tests/test_schema_roundtrip.py`.

**Interfaces:**
- Produces: attribute `ooevv-param-rule-kind` (`passthrough` | `aggregate-collapse-destroy` | `combine` |
  `derive`); relation `ooevv-param-mapping(transformation, in-parameter, out-parameter)` owning
  `ooevv-param-rule-kind`. (`in-parameter`/`out-parameter` played by `ooevv-variable`.)

- [ ] **Step 1: Write the failing test**

```python
def test_param_mapping_rules(scratch_db):
    w(scratch_db, 'insert $t isa ooevv-data-transformation, has id "dt-mean", has name "mean over replicates";')
    w(scratch_db, 'insert $i isa ooevv-variable, has id "var-rep", has name "replicate", has ooevv-variable-role "parameter";')
    w(scratch_db, 'insert $o isa ooevv-variable, has id "var-mean", has name "mean-expr", has ooevv-variable-role "measurement", has ooevv-ice-kind "derived";')
    # mean DESTROYS the replicate index: in-parameter present, out-parameter absent, kind=aggregate-collapse-destroy
    w(scratch_db, 'match $t isa ooevv-data-transformation, has id "dt-mean";'
                  ' $i isa ooevv-variable, has id "var-rep";'
                  'insert (transformation: $t, in-parameter: $i) isa ooevv-param-mapping,'
                  '  has ooevv-param-rule-kind "aggregate-collapse-destroy";')
    rows = r(scratch_db, 'match (transformation: $t, in-parameter: $i) isa ooevv-param-mapping,'
                         '  has ooevv-param-rule-kind $k; $i has name $n; fetch {"k": $k, "n": $n};')
    assert rows[0]["k"] == "aggregate-collapse-destroy" and rows[0]["n"] == "replicate"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_param_mapping_rules -v`
Expected: FAIL — `ooevv-param-mapping` / `ooevv-param-rule-kind` undefined.

- [ ] **Step 3: Add the schema**

```tql
attribute ooevv-param-rule-kind, value string;  # passthrough | aggregate-collapse-destroy | combine | derive

# how a data-transformation maps an input parameter to an output parameter (or destroys it).
relation ooevv-param-mapping,
    relates transformation,
    relates in-parameter @card(0..),
    relates out-parameter @card(0..),
    owns ooevv-param-rule-kind;

entity ooevv-data-transformation plays ooevv-param-mapping:transformation;
entity ooevv-variable plays ooevv-param-mapping:in-parameter,
    plays ooevv-param-mapping:out-parameter;
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_param_mapping_rules -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "feat(scilit): typed data-transformation parameter-mapping rules"
```

---

## Task 5: Template/instance + data table + warrant

Template = a `kefed-model` with no instantiated variables (a state, not a new type). A `kefed-instance`
records one paper's value-instantiations (data rows) + warrant. Retire `kefed-slot` / `kefed-template`.

**Files:**
- Modify: `schema.tql` — replace the `kefed-template`/`kefed-slot`/`kefed-instance`/`ooevv-datum`/`ooevv-cell`
  block (lines ~860-931) with the reconfigured instance/data/warrant layer.
- Modify: `tests/test_schema_roundtrip.py`.

**Interfaces:**
- Produces: attribute `kefed-model-state` (`template` | `instantiated`) on `kefed-model`; entity
  `kefed-instance` (sub `alh-artifact`); relations `ooevv-instance-of(instance, model)`,
  `ooevv-instance-datum(instance, datum)`, `ooevv-cell(datum, cell-variable)` owning
  `ooevv-cell-value`/`ooevv-cell-number`, `ooevv-datum-observation(datum, observation)`; entity
  `ooevv-datum`; attribute `scilit-warrant` on `kefed-instance`.

- [ ] **Step 1: Write the failing test**

```python
def test_instance_data_and_warrant(scratch_db):
    w(scratch_db, 'insert $m isa kefed-model, has id "kefedm-t", has name "design", has kefed-model-state "template";')
    w(scratch_db, 'insert $v isa ooevv-variable, has id "v-expr", has name "expr", has ooevv-variable-role "measurement";')
    w(scratch_db, 'match $m isa kefed-model, has id "kefedm-t";'
                  'insert $inst isa kefed-instance, has id "kefedi-1", has name "paperA run",'
                  '  has scilit-warrant "supports a WT-vs-KO contrast";'
                  ' (instance: $inst, model: $m) isa ooevv-instance-of;')
    w(scratch_db, 'match $inst isa kefed-instance, has id "kefedi-1"; $v isa ooevv-variable, has id "v-expr";'
                  'insert $d isa ooevv-datum, has id "dat-1";'
                  ' (instance: $inst, datum: $d) isa ooevv-instance-datum;'
                  ' (datum: $d, cell-variable: $v) isa ooevv-cell, has ooevv-cell-value "12.3", has ooevv-cell-number 12.3;')
    rows = r(scratch_db, 'match $inst isa kefed-instance, has id "kefedi-1", has scilit-warrant $war;'
                         ' (instance: $inst, datum: $d) isa ooevv-instance-datum;'
                         ' (datum: $d, cell-variable: $v) isa ooevv-cell, has ooevv-cell-number $num;'
                         ' fetch {"war": $war, "num": $num};')
    assert rows[0]["war"].startswith("supports") and rows[0]["num"] == 12.3
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_instance_data_and_warrant -v`
Expected: FAIL — `kefed-model-state` / `kefed-instance` / `ooevv-instance-of` undefined.

- [ ] **Step 3: Add the schema**

```tql
attribute kefed-model-state, value string;   # template (no values bound) | instantiated
attribute scilit-warrant, value string;       # what the instance's data licenses (derived from index sets)
attribute ooevv-cell-value, value string;
attribute ooevv-cell-number, value double;

entity kefed-model owns kefed-model-state;

relation ooevv-instance-of, relates instance, relates model;
relation ooevv-instance-datum, relates instance, relates datum;
relation ooevv-cell, relates datum, relates cell-variable, owns ooevv-cell-value, owns ooevv-cell-number;
relation ooevv-datum-observation, relates datum, relates observation;

# INSTANCE - one paper's execution of a model: value-instantiations (data rows) + warrant.
entity kefed-instance sub alh-artifact,
    owns scilit-warrant,
    plays ooevv-instance-of:instance,
    plays ooevv-instance-datum:instance;
# DATUM - one data row; cells hold per-variable values; links to its provenance observation.
entity ooevv-datum sub alh-domain-thing,
    plays ooevv-instance-datum:datum,
    plays ooevv-cell:datum,
    plays ooevv-datum-observation:datum;

entity kefed-model plays ooevv-instance-of:model;
entity ooevv-variable plays ooevv-cell:cell-variable;
```

Delete `kefed-template`, `kefed-slot`, `kefed-template-slot`, `ooevv-param-slot`, `ooevv-slot-binding`,
`kefed-slot-role`, `kefed-slot-kind` (slots fold into uninstantiated `ooevv-variable`s). Keep
`scilit-observation` plays `ooevv-datum-observation:observation` (re-declared in Task 6).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_instance_data_and_warrant -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "feat(scilit): template=uninstantiated model; instance carries data table + warrant; retire kefed-slot"
```

---

## Task 6: Rhetorical layer — span-anchored claims, AZ, hinges, gaps

One claim type, span-anchored to verbatim fragments, with an AZ property; typed hinges/gaps; the
claim->observation->measurement provenance chain. Retire the `scilit-claim`/`scilit-gap` legacy aliases.

**Files:**
- Modify: `schema.tql` — consolidate `scilit-reported-claim`/`scilit-reported-gap`/`scilit-observation`/
  `scilit-hinge`/`scilit-addresses` onto the clean rhetorical model; ensure span-anchoring via the existing
  `alh-derivation` (note->fragment) + fragment `offset`/`length`.
- Modify: `tests/test_schema_roundtrip.py`.

**Interfaces:**
- Produces: `scilit-claim` (sub `alh-sensemaking-note`, owns `scilit-claim-statement`, `scilit-claim-type`,
  `scilit-rhetorical-role`); `scilit-gap` (owns `scilit-knowledge-goal`); relations
  `scilit-claim-observation(claim, observation)`, `scilit-hinge(hinging-claim, hinged-to)` owning
  `scilit-hinge-term-id`, `scilit-addresses(addressing-note, gap)`; claims/observations play
  `alh-derivation:derivative` (anchored to `alh-fragment` source).

- [ ] **Step 1: Write the failing test**

```python
def test_rhetorical_span_anchored(scratch_db):
    # a paper + cached-less fragment (offset/length present), a claim anchored to it, AZ + hinge + obs link
    w(scratch_db, 'insert $p isa scilit-paper, has id "scilit-paper-r", has name "paperR";')
    w(scratch_db, 'insert $f isa scilit-sentence, has id "frag-1", has content "SIRT3 is required.", has offset 100, has length 18;')
    w(scratch_db, 'insert $c isa scilit-claim, has id "claim-1", has name "SIRT3 necessity",'
                  '  has scilit-claim-statement "SIRT3 is required for X", has scilit-claim-type "primary",'
                  '  has scilit-rhetorical-role "own-claim";')
    w(scratch_db, 'match $c isa scilit-claim, has id "claim-1"; $f isa scilit-sentence, has id "frag-1";'
                  'insert (derivative: $c, derived-from-source: $f) isa alh-derivation;')
    w(scratch_db, 'insert $o isa scilit-observation, has id "obs-1", has name "obs",'
                  '  has scilit-knowledge-level "association", has scilit-bio-scale "cellular";')
    w(scratch_db, 'match $c isa scilit-claim, has id "claim-1"; $o isa scilit-observation, has id "obs-1";'
                  'insert (claim: $c, observation: $o) isa scilit-claim-observation;')
    # claim -> anchored fragment offset
    rows = r(scratch_db, 'match $c isa scilit-claim, has id "claim-1", has scilit-rhetorical-role $az;'
                         ' (derivative: $c, derived-from-source: $f) isa alh-derivation;'
                         ' $f has offset $off, has length $len; fetch {"az": $az, "off": $off, "len": $len};')
    assert rows[0]["az"] == "own-claim" and rows[0]["off"] == 100 and rows[0]["len"] == 18
    # claim -> observation provenance hop
    obs = r(scratch_db, 'match (claim: $c, observation: $o) isa scilit-claim-observation; $o has id $oid; fetch {"oid": $oid};')
    assert obs[0]["oid"] == "obs-1"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_rhetorical_span_anchored -v`
Expected: FAIL — `scilit-claim` / `scilit-claim-observation` not defined under the clean model.

- [ ] **Step 3: Add the schema**

Reconcile the rhetorical block so a single `scilit-claim` exists (rename `scilit-reported-claim` ->
`scilit-claim`, `scilit-reported-gap` -> `scilit-gap`), each span-anchored:

```tql
attribute scilit-claim-type, value string;        # primary | secondary | peripheral
attribute scilit-claim-statement, value string;
# (scilit-rhetorical-role, scilit-knowledge-goal, scilit-knowledge-level, scilit-bio-scale,
#  scilit-hinge-term-id already declared earlier in schema.tql — reuse.)

relation scilit-claim-observation,                 # claim <- supporting observation (provenance grounds)
    relates claim, relates observation;

entity scilit-claim sub alh-sensemaking-note,
    owns scilit-claim-type, owns scilit-claim-statement, owns scilit-rhetorical-role,
    plays scilit-claim-observation:claim,
    plays scilit-hinge:hinging-claim, plays scilit-hinge:hinged-to,
    plays scilit-addresses:addressing-note,
    plays alh-derivation:derivative;                # span-anchored to fragments
entity scilit-gap sub alh-sensemaking-note,
    owns scilit-knowledge-goal,
    plays scilit-addresses:gap;
entity scilit-observation
    plays scilit-claim-observation:observation,
    plays ooevv-datum-observation:observation,
    plays alh-derivation:derivative;                # observations are span-anchored too
```

Delete `scilit-reported-claim`, `scilit-reported-gap`, and their `scilit-sensemaking-reported-*` relations;
re-point any other relations that referenced them to `scilit-claim`/`scilit-gap`. Ensure `scilit-paper`
still plays `scilit-hinge:hinged-to` (paper-level citation).

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_rhetorical_span_anchored -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "feat(scilit): unified span-anchored scilit-claim/gap with AZ + provenance chain"
```

---

## Task 7: Investigation + first-class iterations

An investigation owns an ordered sequence of `scilit-iteration` objects; each iteration owns a corpus
configuration and its five stage notes.

**Files:**
- Modify: `schema.tql` — add the iteration layer; re-point stage threading from investigation to iteration.
- Modify: `tests/test_schema_roundtrip.py`.

**Interfaces:**
- Produces: entity `scilit-iteration` (sub `alh-note`, owns `scilit-iteration-index` (integer)); relations
  `scilit-investigation-iteration(investigation, iteration)`, `scilit-iteration-corpus(iteration, corpus)`,
  `scilit-iteration-stage(iteration, stage)`; `scilit-investigation-phase` re-typed to play `iteration-stage:stage`.

- [ ] **Step 1: Write the failing test**

```python
def test_investigation_iterations(scratch_db):
    w(scratch_db, 'insert $i isa scilit-investigation, has id "scinv-1", has name "inv", has content "goal";')
    w(scratch_db, 'insert $c isa scilit-corpus, has id "collection-1", has name "corpus";')
    w(scratch_db, 'match $i isa scilit-investigation, has id "scinv-1";'
                  'insert $it isa scilit-iteration, has id "scit-1", has name "iteration 1", has scilit-iteration-index 1;'
                  ' (investigation: $i, iteration: $it) isa scilit-investigation-iteration;')
    w(scratch_db, 'match $it isa scilit-iteration, has id "scit-1"; $c isa scilit-corpus, has id "collection-1";'
                  'insert (iteration: $it, corpus: $c) isa scilit-iteration-corpus;')
    w(scratch_db, 'match $it isa scilit-iteration, has id "scit-1";'
                  'insert $ph isa scilit-investigation-phase, has id "scph-1", has name "discovery", has scilit-phase "discovery";'
                  ' (iteration: $it, stage: $ph) isa scilit-iteration-stage;')
    rows = r(scratch_db, 'match $i isa scilit-investigation, has id "scinv-1";'
                         ' (investigation: $i, iteration: $it) isa scilit-investigation-iteration;'
                         ' $it has scilit-iteration-index $idx;'
                         ' (iteration: $it, stage: $ph) isa scilit-iteration-stage; $ph has scilit-phase $stage;'
                         ' fetch {"idx": $idx, "stage": $stage};')
    assert rows[0]["idx"] == 1 and rows[0]["stage"] == "discovery"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_investigation_iterations -v`
Expected: FAIL — `scilit-iteration` / `scilit-investigation-iteration` undefined.

- [ ] **Step 3: Add the schema**

```tql
attribute scilit-iteration-index, value integer;

relation scilit-investigation-iteration,        # investigation owns an ordered list of iterations
    relates investigation, relates iteration;
relation scilit-iteration-corpus,               # an iteration's corpus configuration (its paper set for the round)
    relates iteration, relates corpus;
relation scilit-iteration-stage,                # an iteration owns its 5 stage notes
    relates iteration, relates stage;

entity scilit-iteration sub alh-note,
    owns scilit-iteration-index,
    plays scilit-investigation-iteration:iteration,
    plays scilit-iteration-corpus:iteration,
    plays scilit-iteration-stage:iteration;
entity scilit-investigation plays scilit-investigation-iteration:investigation;
entity scilit-corpus plays scilit-iteration-corpus:corpus;
entity scilit-investigation-phase plays scilit-iteration-stage:stage;
```

Remove the old `scilit-investigation-phasing` (investigation->phase) wiring superseded by iteration->stage.

- [ ] **Step 4: Run to verify it passes**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py::test_investigation_iterations -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "feat(scilit): first-class investigation iterations owning corpus-config + stage notes"
```

---

## Task 8: Full-schema load gate + retirement sweep

Confirm the whole reconfigured `schema.tql` loads cleanly with NO references to retired types, and the
full layer suite passes together.

**Files:**
- Modify: `schema.tql` — grep-and-remove any lingering references to retired types.
- Modify: `tests/test_schema_roundtrip.py` — add a guard test.

- [ ] **Step 1: Write the retirement guard test**

```python
def test_no_retired_types_remain():
    import re, pathlib
    txt = pathlib.Path(__file__).resolve().parent.parent.joinpath("schema.tql").read_text()
    retired = ["kefed-slot", "kefed-template ", "kefed-variable", "kefed-element ",
               "kefed-observed-via", "scilit-reported-claim", "scilit-reported-gap", "ooevv-quality"]
    present = [t for t in retired if t in txt]
    assert not present, f"retired types still referenced: {present}"
```

- [ ] **Step 2: Run the full DB-backed suite (all layers together)**

Run: `uv run --python 3.12 pytest tests/test_schema_roundtrip.py -v`
Expected: every layer test PASSES and `test_no_retired_types_remain` PASSES. Fix any lingering retired
reference in `schema.tql` that the guard or a load error surfaces.

- [ ] **Step 3: Confirm a clean full load via alhazen-core (mirrors the SessionStart hook)**

Run:
```bash
TYPEDB_DATABASE=alh_scilit_schema_test uv run --project ~/skillful-alhazen/local_skills/alhazen-core \
  python ~/skillful-alhazen/local_skills/alhazen-core/alhazen_core.py load-schema \
  ~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/schema.tql
```
Expected: `{"success": true, ... "schema": "loaded"}` with no `[DEX*]`/`[SYR*]` errors.

- [ ] **Step 4: Run the existing pure-logic unit tests (no regressions)**

Run: `uv run --python 3.12 pytest tests/ -v --ignore=tests/test_schema_roundtrip.py`
Expected: existing `test_paper_identity` / `test_entity_identity` / `test_grounding_qc` /
`test_cluster_synthesis` / `test_ontology_grounding` / `test_upsert_paper` all PASS unchanged.

- [ ] **Step 5: Commit**

```bash
git add schema.tql tests/test_schema_roundtrip.py
git commit -m "chore(scilit): retirement sweep + full reconfigured schema load gate"
```

---

## Follow-on plans (Sub-project 1, after this lands)

- **Plan 2 — `kqed.py` + CLI re-alignment.** Reconfigure `kqed.py` authoring verbs (`add_kefed_model` ->
  bigraph builder, `add_observation` without `kefed-observed-via`, drop `scilit-claim`/`scilit-gap` drift,
  add element-set / instance / param-mapping / iteration authoring) and the `scientific_literature.py`
  `cmd_*` / `_load_*` handlers to read/write the clean model. Each verb gets a DB-backed round-trip test
  using the Task 1 harness.
- **Plan 3 — Data teardown + worked-example re-curation.** `make db-export` snapshot; teardown script drops
  the old curation-layer instances from `alh_deep_research`; re-curate the hallmarks/SIRT3 record end-to-end
  on the clean model (element-set, bigraph, instantiated data table + warrant, span-anchored claims,
  iteration/stage), verifying counts and round-trips.

Then **Sub-project 2 — the investigation-first dashboard rewrite** (separate spec section §3 → own plan).

---

## Self-review notes

- **Spec coverage:** §2A OOEVV element-set -> Task 2; §2B bigraph + subject + dual param binding -> Task 3;
  §2B parameter-mapping rules -> Task 4; §2B template=uninstantiated + data table + warrant -> Task 5;
  §2C span-anchored claims/AZ/hinges/gaps + provenance chain -> Task 6; §2D first-class iterations -> Task 7;
  retirement of `kefed-slot`/`kefed-observed-via`/fused `kefed-model` -> Tasks 3/5/8. CLI + data move are
  explicitly deferred to Plans 2/3 (scope split, per writing-plans guidance).
- **Type consistency:** role names used in tests match the relations defined in the same task
  (`element-set`/`element`; `model`/`subject-entity`; `binding-bearer`/`bound-parameter`;
  `transformation`/`in-parameter`/`out-parameter`; `instance`/`model`/`datum`/`cell-variable`;
  `claim`/`observation`; `investigation`/`iteration`/`corpus`/`stage`).
- **Open risk:** exact retirement edits in `schema.tql` depend on the current relation web; Task 8's guard
  test + full-load gate catch any dangling `plays`/`relates` to a deleted type. If a retired type is still
  referenced by a relation we keep, re-point that relation to its clean replacement in the same task.
