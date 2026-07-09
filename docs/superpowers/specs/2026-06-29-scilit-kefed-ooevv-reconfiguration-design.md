# Design Spec — Reconfigure scientific-literature: clean OOEVV / KEfED / rhetorical model + investigation-first dashboard

**Date:** 2026-06-29
**Status:** approved design (Sub-project 1 ready for implementation planning)
**Skill:** `scientific-literature` — upstream `sciknow-io/alhazen-skill-deep-research`,
working dir `~/Documents/GitHub/alhazen-skill-deep-research/skills/scientific-literature/`,
DB `alh_deep_research`.

---

## 1. Context & motivation

The `scientific-literature` skill is mature but has a muddled epistemic core and a jumbled UI:

- **The OOEVV/KEfED schema is unclear where it matters most.** `kefed-model` is annotated *"the OOEVV
  ElementSet = ONE experiment"* (schema.tql:842), fusing three distinct ideas — the *class vocabulary*,
  the *one-experiment bigraph*, and *one experiment*. A prototype layer (`kefed-model` /
  `kefed-variable` / `kefed-observed-via`) coexists with the live template/instance layer, and an
  observation attaches to experimental structure two different ways (`kefed-observed-via` vs
  `ooevv-datum-observation`).
- **The dashboard is "super jumbled."** ~10 pages, weak IA, orphan pages (kqed, acquisition), layout
  primitives scattered across feature files, duplicated header markup, raw-JSON/script dumps, and —
  critically — **no access to the original full text** of papers and **no clean traversal** from a claim
  to the text and data that ground it.

**Decision: reconfigure, not add.** We author the clean target model from first principles (the KEfED /
OOEVV semantics below) and reconfigure the existing scilit work onto it — *replacing* the muddled types
rather than layering beside them. **Delete + reingest is acceptable** (no id-preserving migration). The
dashboard is then rebuilt against the clean model.

**Intended outcome:** an epistemically precise, legible knowledge model whose dashboard gives a
researcher direct access to (a) the curation data, (b) the original paper text, and (c) a traversable
path from any claim → its argumentative role → the verbatim text → the experimental data and warrant
behind it.

---

## 2. The reconfigured conceptual model

### 2A. OOEVV vocabulary layer — building blocks (ontological commitment)

An **OOEVV ElementSet** exhaustively defines the reusable vocabulary for a *class* of experiments
("this is how we describe RNASeq experiments"). It is a **first-class object**, distinct from any one
experiment, template, or instance. Its elements:

| Element | Kinds |
|---|---|
| **Entity** | `material-entity` (obo:BFO_0000040) OR `information-content-entity` (obo:IAO_0000030) — the latter subsumes datasets |
| **Process** | `assay` \| `material-processing` \| `data-transformation` |
| **Variable** (an ICE that takes values) | role ∈ { `constant`, `parameter`, `measurement` } |
| **Measurement scale** (value mapping for a variable) | `nominal` \| `binary` \| `ordinal` \| `numeric` \| `file` \| `composite` |

> **Core fix:** the ElementSet (class vocabulary) becomes its own type (`ooevv-element-set`), **un-fused**
> from `kefed-model`.

### 2B. KEfED model layer — the bigraph

A **KEfED model** is a **bipartite graph of entities ↔ processes**, built from exactly one ElementSet:

- entities are the **inputs and outputs** of processes;
- **both entities and processes carry variables as parameters** — the schema currently binds parameters
  only at processes; entity-borne parameters are a **missing edge** to add;
- any ICE in the graph is a **measurement** (assay output) or a **derived** ICE (transformation output).

**Subject-first spine.** A model reads top-to-bottom: **subject material → manipulations
(`material-processing` binding treatment params) → assays → measured variables → data.** The subject is
the **source node** (no incoming output edge), marked with an **explicit role** so the renderer always
knows where the protocol begins.

**Template = a model with no variables instantiated.** Template and a filled-in experiment are the *same
object type in two states* (zero values bound = template; values bound = a described experiment).
Consequently the separate `kefed-slot` type **collapses into uninstantiated entity-valued parameter
variables** — a "slot kind" (`gene | chemical | cell-type`) is just the entity-type that variable's
value targets, and "filling a slot" is "instantiating that variable."

**Indexing is the point of KEfED:** which **parameters** index the **measurements** and downstream data.

- A **raw measurement's index set** is **derived by upstream traversal** of the bigraph (the
  parameter-bearing entities/processes on the paths producing it). Stored only as the graph + values;
  the index is *computed*.
- **Derived data breaks simple traversal** — a computation combines parameters non-trivially.
  **Decision: full computational provenance.** Every `data-transformation` is modeled as a **typed
  function over (input data + parameters) → output** that **declares explicit parameter-mapping rules**
  for how its input parameters propagate into output parameters (the transformation can change or destroy
  parameters as a hidden part of the computation, so this must be curated, not inferred). Rule kinds
  include:
  - **passthrough** — an input parameter carries to the output unchanged;
  - **aggregate-collapse / destroy** — a set-reducing op (e.g. a **mean over replicates**) **consumes
    and destroys** the index parameter of the measurements it folds together, so the output is no longer
    indexed by it;
  - **combine** — two (or more) parameters fold into a single derived index (e.g. a fold-change yielding
    a *contrast* of conditions; a ratio collapsing two contexts);
  - **derive** — the computation introduces a *new* output parameter not present on any input.

  A derived datum's **index set is computed by applying these rules** to its inputs' index sets — so
  indexing **composes through the workflow** and stays machine-derivable end to end. Many mapping rules
  are possible per computation; the rule set is part of the curated transformation.

**Data table + warrant are persisted curation.** Instantiating variables produces recorded rows (each
row = one measurement context); the table **and** the derived **warrant** (what each measurement
licenses, following from its index set) are preserved as curation artifacts — today's
instance/datum/cell layer, reconfigured onto the clean model.

### 2C. Rhetorical layer — span-anchored claims

- Every **claim / observation is anchored to one or more verbatim text fragments** (char offsets into
  the cached full text), so the UI can traverse a claim → the exact supporting sentence(s).
- The **AZ (argumentative zone)** rides as a **property** of each claim.
- **Hinges** (Teufel CFC, claim↔claim / claim↔paper) and **gaps** are **typed relations** over the
  anchored claims.

**Claim ↔ evidence = linked but unconstrained.** A traversable provenance chain, *not* a gate:

```
claim → supporting observation(s) → measurement(s) → index set → data row → verbatim source text
```

The KEfED **warrant is shown beside the claim** (so over/under-claiming is visible) but nothing forces
the claim's asserted strength to match it — the human judges fit.

### 2D. Investigation / iteration layer — the dashboard backbone

- An **investigation** is the top-level, goal-driven unit.
- It owns an **ordered sequence of first-class iteration objects**. Each **iteration** is a
  self-contained round of effort with **its own corpus configuration** (paper set + selection criteria
  for that round) and **its own five stage notes**: `discovery → ingest → sensemaking → analysis →
  report`.
- The dashboard sidebar shows the five stages of the **selected iteration**; an iteration switcher picks
  the round.

---

## 3. The dashboard (investigation-first IA) — *Sub-project 2, designed here for coherence*

1. **Landing = list of investigations** (not corpora).
2. **Investigation page** — iteration switcher + left sidebar of the 5 stages for the selected iteration:
   - **A · Discovery** — the criteria/queries used to build the corpora in this iteration.
   - **B · Ingestion** — paged list of papers with ingestion status (`missing` / `abstract` /
     `full-text` / `full-text + supplements`) and links to view each paper's **artifacts and fragments**,
     including the original cached full text.
   - **C · Sensemaking** — list of papers; click-through to the notes for each paper, then deeper
     click-through into the **KQED / KEfED / OOEVV** extractions for that paper.
   - **D · Analysis** — workflows + visualizations + analysis for this iteration (faceting pipelines, etc.).
   - **E · Reports** — audience-facing writeups.
3. **OOEVV browser** — a browsable + searchable list of **typed entities formatted per the OOEVV paper**,
   showing the properties and definitions of each term.
4. **KEfED template view** — the **complete parameterized experimental protocol**: subject →
   manipulations on the animal/sample → assays → data. We don't pre-specify many templates; the view
   renders whatever exists.
5. **Claim ↔ text ↔ data traversal** — claims always grounded in text with links back to supporting
   verbatim spans, displayed together with the rhetorical (AZ) constructs and the epistemic KEfED data
   tables / observations.

**Build mechanics:** source-of-truth is `dashboard/{components,lib.ts,pages,routes}` in the upstream
skill repo; `make build-dashboard` copies the 4 slots into `dashboard/src/`. NEVER edit `dashboard/src/`
directly. External-skill changes are pushed upstream.

---

## 4. Decomposition & sequencing — schema-first

Two sub-projects, foundation-up. **Sub-project 1 is built fully first**; the dashboard is a later cycle
(the dashboard can't surface a clean model that doesn't exist yet).

### Sub-project 1 — Reconfigured schema + teardown + CLI  *(the active work)*

**Critical files (all upstream):**
- `schema.tql` — reconfigure the OOEVV/KEfED/KQED/investigation blocks (~lines 422–963).
- `kqed.py` — reconfigure authoring verbs (`add_kefed_model`, `add_observation`, grounding, etc.).
- `scientific_literature.py` — reconfigure the KEfED/OOEVV/investigation authoring `cmd_*` and read
  `_load_*` paths onto the clean model.
- `migrations/` — a **teardown script** deleting the reconfigured curation-layer instances so they can
  be re-curated. No id-preserving copy.
- `tests/` — update/extend support-module tests.

**Target type changes (concept → schema):**
- **New `ooevv-element-set`** grouping its entities/processes/variables/scales — un-fused from `kefed-model`.
- **Entities** split `material-entity` (obo:BFO_0000040) vs `information-content-entity`
  (obo:IAO_0000030); ICEs typed *measurement* vs *derived*.
- **Variables** keep `constant|parameter|measurement`; **add entity-borne parameter binding**.
- **Processes** `assay|material-processing|data-transformation`; **data-transformation carries typed
  parameter-mapping rules** (`passthrough` / `aggregate-collapse-destroy` / `combine` / `derive`) over
  (input data + params) → output, so the derived-datum index composes through the workflow (full
  computational provenance).
- **`kefed-model` = the bigraph only** (built from one element-set); **subject role** marks the source node.
- **Template = uninstantiated model**; **retire `kefed-slot`**; reconcile `kefed-template`/`kefed-instance`
  into the single model-with-state + persisted data-table/warrant.
- **Retire `kefed-observed-via`** (dual observation link); observation↔data bridges via the datum link only.
- **Rhetorical:** span-anchored claims/observations; AZ as property; typed hinges/gaps; linked-unconstrained
  claim→evidence chain.
- **Investigation/iteration:** first-class **iteration** object; investigation owns ordered iterations;
  each iteration owns corpus-config + 5 stage notes — reconfigure current phase-threading.

**Data approach — delete + reingest (approved).** No id-preserving migration. Take a `make db-export`
snapshot first (repo rule), then **drop the reconfigured curation layer** (KEfED / OOEVV / rhetorical /
investigation instances) and **re-curate** it into the clean model. **Keep the raw ingested layer** —
papers, corpora, cached full-text artifacts/fragments (clean and costly to re-fetch); scope is widenable.
Recovery via `make db-import` from the snapshot.

### Sub-project 2 — Investigation-first dashboard rewrite  *(later cycle)*

The IA in §3, built against the clean model. Separate spec → plan → execution.

---

## 5. Verification (Sub-project 1)

- `make db-export` snapshot taken and verified first; schema reloads cleanly; papers/corpora/full-text
  layer intact afterward.
- CLI round-trips the clean model (author → read-back) by **re-curating a worked example** (e.g. the
  hallmarks/SIRT3 record) into the new model end-to-end: element-set, bigraph, instantiated data table +
  warrant, span-anchored claims, iteration/stage structure.
- Support-module + CLI tests pass.

---

## 6. Open / deferred

- **OOEVV vocabulary grounding — default: YES (reversible).** Ground the full element vocabulary to
  upper ontologies, consistent with the entity split: `process` → `obo:BFO_0000015`; `assay` →
  `obo:OBI_0000070`; `material-processing` → `obo:OBI_0000094`; `data-transformation` →
  `obo:OBI_0200000`; `measurement` → `obo:IAO_0000109`; entities per §2A. **Variable definitions ground
  to EFO** (Experimental Factor Ontology) factor terms — the variable structurally subsumes under
  `obo:IAO_0000030` (ICE), but its grounding target is an EFO factor (consistent with the existing
  `kefed-efo-label` intent). **Measurement scales keep OOEVV's own taxonomy** (no crisp BFO/IAO parent).
  Each element type carries its CURIE via the existing `scilit-curie` slot.
- Exact AZ zone inventory and CFC hinge-type vocabulary (curated as `alh-vocabulary` terms; finalize
  during implementation).
- OOEVV-browser term-card layout fidelity to the OOEVV paper (Sub-project 2).
- Whether the "keep raw ingested layer" boundary widens to re-fetch any papers.

---

## 7. Addendum (2026-07-01) — first-class value-specifications + grounding policy (implemented)

Refines the OOEVV vocabulary layer per Gully:

- **Value-specifications are first-class + shared.** A `variable = a shared QUALITY (semantics) + a shared
  VALUE-SPECIFICATION (the value space + method)`. A **value-specification IS an `ooevv-scale`** (nominal /
  binary / ordinal / numeric / file / composite), now **named, reusable and grounded-capable** (it already
  subs `ooevv-element`). NEW relation **`ooevv-quality-scale`** lets a quality **enumerate its canonical
  value-specs**, so the *same* quality can be measured *different* ways (e.g. `age` → `{ordinal
  young<mature<old}` + `{numeric days}`). A variable **references** a shared value-spec (one scale, many
  variables) via `ooevv-has-scale`. Verbs: `ensure-value-spec`, `add-variable --value-spec`,
  `list-value-specs`; grounding-owns moved up to `ooevv-element`.
- **Grounding is correctness-gated (not fabricated).** Attach a `scilit-curie` **only** when a verified,
  definition-matching ontology term exists; otherwise mark `grounding-state "ungrounded"` and keep the
  precise local definition. Never approximate or guess a curie.
- **Curation is vocabulary-first, recognize→reuse→extend.** Qualities + value-specs are the DB-grown source
  of truth; curation lists and reuses them, extending (and grounding, where verifiable) as needed. See
  `SKILL.md` §"KEfED Model Authoring" for the operational method.
