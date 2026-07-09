# Integrating Mem0 (STM) with Skillful Alhazen (LTM)

> Architecture design doc. Status: **reframed proposal** (see §1.5 — fork created, no code yet).
> Audience: anyone extending the Alhazen memory layer, or contributing to Mem0.
> **Read §1.5 first:** Mem0's v3 rewrite deleted the graph store, so the contribution is now a
> pluggable *typed entity/relation store* for the v3 pipeline, with TypeDB as the reference impl.
> The fork lives at `github.com/GullyBurns/mem0` (cloned to `~/Documents/Github/mem0`).

## 1. Motivation

We ran a tech-recon investigation — **"Agentic Memory Systems: Benchmark Gap Analysis"**
(`tri-91e04d6993bb`) — that scored Mem0, Zep, Letta/MemGPT, Cognee and others against six
*schema-first curation* dimensions. The result is not a verdict that one system beats another;
it is a clean **complementarity**.

Mem0 is a three-layer memory system (vector store + optional graph store + SQLite audit log)
whose real strength is an **automatic extraction pipeline**: raw conversation turns are passed
to an LLM that extracts facts, searches existing memories, and decides ADD / UPDATE / DELETE /
NONE for each — then writes concurrently to its stores. It is fast, automatic, and schemaless,
with session scoping via `user_id` / `agent_id` / `run_id`.

That same schemalessness is its weakness. Scored against the six dimensions:

| Dimension | Mem0 | Note |
|---|---|---|
| Episodic recall | **2/3** | Decent conversational QA (LoCoMo J≈66.9%) |
| Relational reasoning | **1/3** | Graph variant *underperformed* base on multi-hop |
| Schema conformance | **0/3** | No schema; silent drift across LLM versions |
| Provenance | **0/3** | Facts not traced to source |
| Contradiction handling | **1/3** | Stochastic LLM similarity, not logical resolution |
| Longitudinal stability | **0/3** | No drift measurement; benchmarks too short |

The three `0/3` dimensions — **schema, provenance, longitudinal stability** — are precisely
what TypeDB + Alhazen is built for:

- **Schema conformance** via TypeDB's typed schema and `redefine` migration.
- **Provenance** via `alh-aboutness`, `episode` / `alh-episode-mention`, and confidence on
  every claim.
- **Longitudinal stability** via `nbmem-memory-claim-note` consolidation and `valid-until`
  invalidation (history is preserved, never silently dropped).

**The thesis: this is a hippocampus → neocortex split.** Mem0 is the fast episodic buffer
(short-term memory). TypeDB + Alhazen is the slow, schema-governed semantic store (long-term
memory). A **consolidation** step moves facts from STM into LTM — the way memory consolidation
moves the day's experience into durable, structured knowledge.

There are **two ways to do that consolidation**, distinguished by *where ontological commitment
happens*:

- **Approach A — schema-on-write (§4):** type each fact at ingestion against the existing
  TypeDB schema; untypeable facts become explicit `schema-gap` signals.
- **Approach B — emergent schema (§5):** accept every fact into a minimal-commitment loose
  triple graph in TypeDB, then *lift the schema out by analysis afterward*, materializing a
  derived typed layer that coexists with the raw triples.

A is immediate and disciplined but commits early. B never drops an untypeable fact and lets the
schema emerge from evidence, at the cost of a second (derived) layer. They are not exclusive —
§5.5 shows how B can feed A.

## 1.5 Reframe — Mem0 v3 deleted the graph store (2026-05-30)

> This section supersedes the "don't use Mem0's graph store" framing below wherever they
> conflict. §§2–10 were written against Mem0's pre-v3 three-layer design; the architecture has
> since changed materially. The complementarity thesis is unchanged — the *contribution* is.

**Finding.** When we forked `mem0ai/mem0` to build a TypeDB graph backend, we discovered that
Mem0's **v3 pipeline rewrite** (PR #4805, *"port v3 pipeline with hybrid search, entity
extraction, and additive scoring"* — the most recent major commit on `main`) **removed all
graph-store support**, in Python *and* TypeScript: `mem0/graphs/`, `graph_memory.py`,
`memgraph_memory.py`, the Neptune backends, the `GraphStoreFactory`, configs, tools, prompts, and
all graph tests are gone. The duck-typed `MemoryGraph` contract + factory-dict registration that
a graph-backend contribution would have targeted **no longer exists**.

**What v3 is instead** (entity-centric, not graph-native):

- **Entity extraction is spaCy-based** (`mem0/utils/entity_extraction.py`) — only four *syntactic*
  categories: PROPER / COMPOUND / QUOTED / NOUN. No LLM typing, **no relations or triples at all**.
- **Entities live in a vector collection.** The `entity_store` property (`mem0/memory/main.py:388`)
  just creates a second collection `{collection}_entities` via `VectorStoreFactory.create(...)`.
  Each entity is a vector with payload `{data, entity_type, linked_memory_ids, user_id, …}` —
  a 1:N link to memories, **not** a relation between entities. The entity store is **hardcoded**
  to the vector-store provider (`main.py:408`); there is no abstraction or config hook for it.
- **Extraction is ADD-only.** v3 dropped Mem0's old ADD/UPDATE/DELETE/NONE decisioning; new facts
  are hash-deduped and inserted. No invalidation, no supersession.
- **Retrieval = semantic + BM25 + additive "entity boost"** (`mem0/utils/scoring.py`,
  `ENTITY_BOOST_WEIGHT = 0.5`): query entities are matched against the entity store and used to
  boost the scores of their `linked_memory_ids`. No graph traversal.
- **Config** (`mem0/configs/base.py`) exposes only `vector_store` / `llm` / `embedder` /
  `reranker`. No graph / relational / entity-store seam remains.

**Why this strengthens, not weakens, the thesis.** v3 is now *demonstrably* weak on the same six
dimensions: untyped syntactic entities (schema 0/3), ADD-only with no supersession (longitudinal
0/3, contradiction down), **relations removed entirely** (relational regressed), provenance still
minimal. And it left a clean, load-bearing seam — the entity store — that is currently a flat
vector collection begging to be typed.

**The reframed contribution.** Instead of a graph *backend* for a subsystem that was deleted, we
contribute a **pluggable typed entity/relation store for the live v3 pipeline, with TypeDB as the
reference implementation** — restoring the relational capability the team just removed, but in a
*typed, schema-governed, provenance-stamped* form. Layering (locked in this session) is preserved:

- **Base = Mem0 v3** — the underlying schemaless capture engine. TypeDB is *one possible backend*
  for its entity/relation layer, alongside the default vector collection.
- **Extension = an Alhazen notebook** — a domain `schema.tql` (the shareable "theory") + dashboard,
  **loaded from a GitHub repo** via the same mechanism Alhazen uses (`skills-registry.yaml` →
  `make skills-install` git-clone → `db_init.py` loads `schema.tql`). Notebooks are never invented
  inline; they are discoverable repos.

**Three injection seams** (in priority order):

| Seam | Where | What it does |
|------|-------|--------------|
| **A — pluggable typed entity store** *(foundation)* | `entity_store` property `main.py:388`; new `EntityStoreConfig` in `configs/base.py`; new `mem0/entity_stores/` module mirroring `vector_stores/` | Turn the flat `{collection}_entities` vector collection into a typed, TypeQL-queryable store. Interface: `search/insert/update/delete/list/search_batch`. |
| **B — post-extraction relation store** *(the differentiator)* | Phase-7 entity linking, `main.py:865–950`; new LLM relation-extraction step | Extract `(subject, predicate, object)` triples (the thing v3 dropped) and persist them to TypeDB with provenance + `valid-until`. Restores the graph dimension, typed. |
| **C — relational entity boost** *(retrieval payoff)* | `_compute_entity_boosts` `main.py:1440–1499` | Extend the additive boost to traverse relations (path-decayed), so multi-hop neighbours boost retrieval — the multi-hop win the old graph variant *failed* to deliver. |

**Server/UI reality:** `server/docker-compose.yaml` now runs FastAPI + **pgvector** + a Next.js
dashboard. `openmemory/` is being **sunset** (redirects to `server/`). The Alhazen-style TypeDB
container + a typed/lineage dashboard view attach to `server/`, not `openmemory/`.

The remaining sections (§§2–10) still describe the *target LTM properties* and the test (§10
"Einstein runs a job search") correctly — read them as the **specification the typed store must
satisfy**, with "Mem0's graph store" reinterpreted as "v3's entity store, made typed."

## 2. Layered architecture

```
                     ┌─────────────────────────────────────────────┐
   conversation ───▶ │  STM  —  Mem0 (vector-only, self-hosted)     │
   turns             │  user_id=operator  run_id=episode            │
                     │  auto-extract facts · ADD/UPDATE/DELETE       │
                     │  fast semantic recall · decays / prunes       │
                     └───────────────────────┬─────────────────────┘
                                              │  consolidation bridge
                                              │  (session close / explicit)
                                              ▼
                     ┌─────────────────────────────────────────────┐
                     │  LTM  —  TypeDB + Alhazen notebooks          │
                     │  nbmem-memory-claim-note (typed, sourced)    │
                     │  episode · alh-aboutness · entity-alias      │
                     │  schema-governed · provenance · valid-until  │
                     └─────────────────────────────────────────────┘
```

| Layer | System | Scope | Properties |
|-------|--------|-------|------------|
| **STM** | Mem0 (vector-only) | live + recent sessions | fast, automatic, schemaless, decays/prunes |
| **LTM** | TypeDB + Alhazen | durable knowledge | schema-governed, provenance-stamped, contradiction-resolved, never silently dropped |

**Deployment:** Mem0 runs **self-hosted** (`mem0ai` OSS), with its vector store pointed at the
**Qdrant instance Alhazen already runs**. No external API; data stays local.

**Deliberate exclusion — do not use Mem0's graph store.** It is schemaless and *underperformed*
base Mem0 on multi-hop reasoning in the assessment. TypeDB *is* the graph and the LTM. This holds
for **both** approaches: neither writes to Mem0's Neo4j-style backend. Approach B still builds a
graph, but it builds it *in TypeDB* (the reified-triple layer, §5.1) and reuses Mem0 only as the
extraction engine. Keeping Mem0 vector-only — plus, for B, intercepting its extracted triples —
keeps the boundary between the two systems clean.

## 3. Identity & scoping map

The two systems share one operator and one notion of a "session." The mapping is intentionally
1:1 so that nothing is lost in translation.

| Mem0 concept | Alhazen concept |
|---|---|
| `user_id` | operator id (`op-f25ab4b15b0f`) |
| `run_id` | `episode` id (one run = one session = one episode) |
| Mem0 collection | dedicated Qdrant collection `mem0_stm` (separate from `alhazen_papers` and other LTM embedding collections) |
| Mem0 fact item | candidate for an `nbmem-memory-claim-note` |
| Mem0 ADD/UPDATE/DELETE history | episode operation tracking + claim `valid-until` invalidation |

Using `run_id = episode id` is the keystone: it means the consolidation bridge can pull exactly
the facts captured during a session and attach them to the episode that already represents that
session in LTM.

## 4. Approach A — schema-on-write (the consolidation bridge)

This runs at **session close** (when `create-episode` is called)
or on demand via an explicit `consolidate-session` command. For each Mem0 fact captured under
the session's `run_id`:

1. **Pull** — read the session's Mem0 memories (`m.get_all(run_id=<episode>)`).
2. **Classify** — assign a fact-type from the existing `nbmem-memory-claim-note` vocabulary:
   `knowledge | decision | goal | preference | schema-gap`.
3. **Resolve subject** — map the fact to an existing TypeDB entity via semantic `search` +
   `entity-alias` resolution; create the entity if (and only if) the schema supports its type.
4. **Schema check** — if the fact references a type or relation the schema *cannot* represent,
   do **not** drop it. Emit a **`schema-gap`** claim instead.
   *This turns Mem0's biggest weakness into a feature:* schemaless capture becomes a sensor for
   schema-evolution pressure, feeding the existing skilllog / schema-gap detection in the
   verification layer.
5. **Contradiction check** — `recall` existing claims about the subject. If the new fact
   supersedes an existing one, `invalidate` the old (set `valid-until`) and add the new, with
   the supersession recorded on the episode. This is **logical** resolution against stored
   claims — not Mem0's stochastic similarity judgement.
6. **Write** — create the `nbmem-memory-claim-note` with full provenance:
   - `confidence`
   - subject link via `alh-aboutness`
   - session link via `alh-episode-mention`
   - embed into the LTM Qdrant collection for later semantic recall.

**No new primitives required.** Every step maps to an existing `agentic_memory.py` verb:

| Bridge step | CLI verb |
|---|---|
| Pull | (Mem0 SDK `get_all`) |
| Resolve subject | `search` |
| Contradiction check | `recall`, `invalidate` |
| Write claim | `consolidate` |
| Session linkage | `create-episode`, `link-episode` |

The only new code is a `consolidate-session` **driver** that orchestrates these — it adds no new
TypeDB schema.

## 5. Approach B — emergent schema (loose triple graph + inference)

Approach B inverts *where* ontological commitment happens. Rather than typing facts at write
time, it accepts everything into a minimal-commitment graph in TypeDB and **lifts the schema out
by analysis afterward**. This is a closer fit to how Mem0 actually behaves — nothing untypeable
is ever deferred or dropped — and it turns schema discovery itself into a first-class capability.

### 5.1 Capture — the reified-triple layer (minimal ontology)

TypeDB is schema-mandatory: you cannot `MERGE` an arbitrary label the way Neo4j does. But you
get a Mem0-style open graph with a **reified-triple** schema, about as minimal as commitment
gets:

```tql
entity mem-node,
    owns name,            # normalized surface form
    owns node-type,       # LLM-generated type STRING (not a TypeDB type)
    owns embedding,
    plays mem-triple:subj,
    plays mem-triple:obj;

relation mem-triple,      # one generic edge type for everything
    relates subj,
    relates obj,
    owns predicate,       # LLM-generated relationship STRING
    owns confidence,
    owns source-episode,  # provenance, for free
    owns valid-from,
    owns valid-until;
```

That is the entire ontology: **node + type-string + reified edge carrying the predicate as a
string**. Mem0's extracted `(source, relationship, destination, source_type, destination_type)`
tuples drop straight in. **Reuse Mem0 as the extraction engine** — intercept its
`establish_relationships` tool-call output (`mem0/graphs/tools.py:85`) and write the triples here.
Don't write to Mem0's own graph backend (TypeDB isn't one of its five).

This raw layer is the **immutable source of truth**: append-only, fully provenanced, bitemporal
(`valid-from`/`valid-until`). Types and predicates live as *string attributes*, so there is zero
TypeDB-type commitment — yet provenance and longitudinal history are already satisfied,
independent of any inference.

### 5.2 Inference — build the derived typed layer

A periodic consolidation pass mines the triple layer (the systems-consolidation half of the
hippocampus → neocortex metaphor):

- **Relation-type induction** — cluster `predicate` strings (embedding + string similarity) into
  canonical relations (`professor_of` / `is_professor` / `teaches_at` → one relation).
- **Entity-type induction** — cluster `node-type` strings into canonical entity types.
- **Role / domain-range inference** — for each predicate, examine which node-types occur as
  `subj` vs `obj` to infer the relation's roles and type constraints.
- **Data-level inference** — entity resolution (Mem0's 0.7-similarity dedup, but as a graph pass
  rather than a write-time guess), link prediction, contradiction detection over conflicting
  triples.

It emits three things: **(a)** a proposed schema, **(b)** materialized typed instances in a
*separate* derived layer, and **(c)** lineage links from each derived instance back to the source
triples it was inferred from.

### 5.3 Two coexisting layers

```
   Mem0 extraction ──▶ ┌────────────────────────────┐
                       │  RAW triple layer (TypeDB)  │   immutable · append-only
                       │  mem-node · mem-triple      │   provenance · bitemporal
                       │  type/predicate = STRINGS   │   = source of truth
                       └─────────────┬──────────────┘
                                     │  inference pass (recomputable)
                                     ▼  + lineage links
                       ┌────────────────────────────┐
                       │  DERIVED typed layer        │   real TypeDB types
                       │  person · works-at · …      │   constraints · polymorphism
                       │  projection of the triples  │   recomputed as understanding grows
                       └────────────────────────────┘
```

- **Raw layer** — deliberately dumb, never mutated except append + `valid-until`. It *is* the
  audit trail.
- **Derived layer** — a recomputable projection, rebuilt (or incrementally updated) as the
  inference improves. **This is where TypeDB earns its keep**: real types, constraints,
  polymorphic queries, the reasoner. Inferred types can be gated through the existing
  `docs/schema-lifecycle.md` PR flow — living in the derived/experimental layer until "blessed"
  into the canonical schema.

### 5.4 The crux

A minimal-commitment TypeDB, *on its own*, is "TypeDB used as a dumb triple store" — at which
point you've discarded the type system you're paying for and could have used Neo4j. **The entire
payoff lives in the promotion step (§5.2).** The two-layer model is what resolves this: the raw
layer is supposed to be dumb (that's its job as an audit substrate), and the derived layer is the
smart projection that delivers TypeDB's strengths *without* premature commitment.

### How Approach B closes the three gaps

- **Provenance (0/3 → native):** every triple carries `source-episode`; every derived instance
  carries lineage back to its triples.
- **Longitudinal (0/3 → preserved *and improving*):** the raw layer is immutable + bitemporal;
  the derived layer is recomputable, so the schema *improves* over time instead of drifting.
- **Schema conformance (0/3 → evidential):** schema is *induced* from accumulated evidence with
  role/domain-range constraints, then materialized as real TypeDB types — conformance achieved
  bottom-up rather than imposed top-down.

### 5.5 Approach A vs B

| | A — schema-on-write | B — emergent / derived layer |
|--|--|--|
| Commit point | ingestion | deferred to inference |
| Untypeable facts | → `schema-gap` claim | accepted as triples, typed later (or never) |
| Queryable types | immediately | after first inference pass |
| Storage | one typed layer | raw triples + derived projection |
| Curation cost | per write | batched in the inference pass |
| Main risk | premature / wrong commitment | derived layer lags reality; "dumb triple store" if never promoted |
| Best when | schema is stable and known | schema is unknown / evolving; *discovery is the goal* |

**They are not exclusive.** Approach B's promotion step can *populate* Approach A's
`nbmem-memory-claim-note` / typed-entity model. A reasonable end-state runs **B as the substrate**
(loose triples = capture) and uses **A's claim-note machinery as the "blessed" derived layer**
(consolidated, provenanced facts) — emergent discovery feeding disciplined long-term memory.

## 6. Unified retrieval

Add Mem0 as **Stage 0 (STM)** in front of the existing agentic-memory three-stage retrieval
pipeline:

- **Stage 0 — STM (Mem0):** `m.search(query, user_id, run_id?)` for hot / recent / session-scoped
  facts. Sub-second. These facts may not yet be consolidated into LTM.
- **Stage A — Plan (LTM):** understand schema, pick graph-only / embedding / hybrid strategy.
- **Stage B — Execute (LTM):** TypeQL graph traversal + Qdrant semantic search.
- **Stage C — Organize (LTM):** synthesize with provenance and confidence.

**Merge rule.** STM hits are **candidate / uncommitted** — fast but without a provenance
guarantee. LTM hits are **committed** — typed and sourced. The agent presents both but tags each
with its provenance status, so it knows which facts it can *defend* and which are still
provisional working memory.

Under **Approach B** this is a three-tier read: Mem0 STM → raw triple layer (provenanced but
untyped) → derived typed layer (typed, queryable). The derived layer answers structured queries;
the raw layer is the fallback when a fact exists as a triple but hasn't been promoted yet.

## 7. Forgetting & decay

- **STM (Mem0) is allowed to forget.** It is a buffer: pruning and expiry are expected and fine.
  Anything important is consolidated to LTM before it decays.
- **LTM never silently forgets.** Facts are retired by setting `valid-until`, which preserves
  history rather than deleting it. This is exactly the longitudinal-stability property Mem0
  scored `0/3` on — the bridge supplies it. Under Approach B this is stronger still: the raw
  triple layer is append-only, and the derived layer is *recomputed*, so "forgetting" a wrong
  inference just means the next pass doesn't reproduce it — the evidence stays.

## 8. Open tensions (not resolved here)

- **Consolidation trigger granularity** — every turn vs. session-close vs. explicit.
  *Recommendation:* session-close, with an explicit override for long sessions.
- **Extraction ownership** — rely on Mem0's LLM extraction, or run our own extraction prompt for
  tighter schema alignment? *Recommendation:* Mem0 extracts candidates; the bridge re-types them
  against the schema (keeps Mem0's automation, adds our discipline).
- **Duplicate Mem0 entries** — the DB already has two `Mem0` `trec-system` rows
  (`trs-48232127a658`, `trs-e4085f8b174e`). Data-hygiene cleanup; out of scope here.
- **`MEMORY.md` fate** — retire vs. keep. *Recommendation:* keep as a generated, human-readable
  *index* over the LTM working set, not the primary store.
- **A vs B (or both)** — which consolidation model to commit to. *Recommendation:* prototype B's
  capture + one inference pass first (it subsumes A's substrate), then decide whether the derived
  layer *is* the claim-note model or feeds it.
- **Inference cadence (B)** — when to run the inference pass: every N triples, on a timer, or on
  demand. Trades derived-layer freshness against compute.
- **Promotion threshold (B)** — how much evidence (cluster size, role consistency) before an
  inferred type is materialized, and what gets it "blessed" into the canonical schema vs. left in
  the derived/experimental layer.

## 9. Proposed PoC (follow-up)

Per the tech-recon eval-notes mapping ("Evaluation → Integration prototype"): a script that
**connects Mem0 to TypeDB, stores a memory, retrieves it, and verifies round-trip.** Concretely:

1. Stand up self-hosted Mem0 against the existing Qdrant (`mem0_stm` collection).
2. Feed it a short scripted conversation; let it auto-extract facts under
   `user_id=op-…`, `run_id=<test-episode>`.
3. Run `consolidate-session` over that `run_id`: classify → resolve → schema-check →
   contradiction-check → write `nbmem-memory-claim-note`s with provenance.
4. Verify: every consolidated fact is `recall`-able from TypeDB with a subject link and an
   episode link; at least one engineered contradiction produces an `invalidate`; at least one
   untypeable fact produces a `schema-gap` claim.
5. Report the discrepancy between what was captured in STM and what survived into LTM (the real
   measure of consolidation quality).

**Approach B PoC** (the discovery-oriented variant):

1. Define the reified-triple schema (§5.1) in a scratch TypeDB database.
2. Intercept Mem0's `establish_relationships` output over a sample conversation; write the
   triples to the raw layer with provenance.
3. Run one inference pass: cluster predicates and node-types, infer roles, materialize a small
   derived typed layer with lineage links back to the triples.
4. Verify: the derived types are recoverable from the raw triples alone (recompute → same result);
   each derived instance traces back to its source triples; a deliberately messy set of predicate
   synonyms collapses to one canonical relation.
5. Report the induced schema and how much of the loose graph it covers (the real measure of
   emergent-schema quality).

### How the design closes Mem0's three gaps

- **Schema conformance (0/3 → governed):** every consolidated fact is typed against the TypeDB
  schema; untypeable facts become explicit `schema-gap` signals rather than silent drift.
- **Provenance (0/3 → tracked):** every claim links to its subject (`alh-aboutness`) and its
  originating session (`alh-episode-mention`), with confidence.
- **Longitudinal stability (0/3 → preserved):** supersession via `valid-until` keeps full
  history; LTM does not silently lose or duplicate facts over time.

## 10. Testing scenario — "Einstein runs a job search"

A scenario is only useful if it **discriminates A from B** — it has to stress exactly where the
two approaches diverge: untypeable facts, schema discovery, predicate/type synonymy, temporal
supersession, recompute-improvement, and the promotion threshold. A clean conversational-recall
benchmark (e.g. LoCoMo) won't do this, because casual preference facts fit a thin schema and
never force the discovery question B exists to answer.

We ground the test in the real `jobhunt` skill schema and a synthetic, historically-flavoured
narrative: **Albert Einstein's 1932–33 job search**, in which he networks, collects referrals,
goes through an interview/negotiation, weighs competing offers, and finally lands at the Institute
for Advanced Study (IAS). It runs in a **scratch TypeDB database** (do not touch the live
notebook), with Mem0 as the shared extraction front-end so both pipelines compare *consolidation*,
not extraction.

### 10.1 The deliberately partial seed schema

Seed the scratch DB with only *part* of the `jhunt` ontology, so some facts type cleanly (A's
happy path) and some cannot (forcing B's discovery / A's `schema-gap`):

| Seeded (schema knows) | Withheld (must be discovered / gapped) |
|---|---|
| `jhunt-candidate` (Einstein), `alh-person` (contacts) | `jhunt-contact-for-opportunity` — the networking/referral structure |
| `jhunt-company` (IAS, Caltech, Oxford) | the `jhunt-lead` / `jhunt-engagement` / `jhunt-position` *stage* distinction (seed knows only generic `jhunt-opportunity`) |
| `jhunt-position`, `jhunt-opportunity` | interview structure (`jhunt-interview-note`, rounds, `interviewed-by`) |
| `jhunt-opportunity-at-organization`, `jhunt-position-at-company` | referral / recommendation relations (Veblen→Einstein→Flexner; a Born reference letter) |
| `jhunt-seeker-pipeline` (seeker↔opportunity, with status) | offer + salary negotiation |

The **withheld set is the answer key** for scoring B's induced schema — it must be fixed up front.

### 10.2 The narrative (one session = one episode)

| Session | Facts (paraphrased) | Stressors planted |
|---|---|---|
| **S1 Networking** | Einstein meets Abraham Flexner, who is *founding* a new institute; Millikan (Caltech) and Lindemann (Oxford) also express interest | contacts + orgs (typeable); `founding` + early **leads** (novel); org aliases ("the Institute"/IAS/Princeton) |
| **S2 Referrals** | Oswald Veblen *recommended* Einstein to Flexner; Max Born *wrote a reference letter*; Einstein *agrees to consider* IAS | `referred-by` / `recommended-by` (novel → A gaps, B captures); person alias (Dr. Einstein = Albert) |
| **S3 Interview/negotiation** | Einstein *met with* Flexner several times; Flexner *offered* $10,000; Einstein *countered* ~$3,000 | `interviewed-by`/`met-with` synonyms (→ promotion threshold); `offer` + `negotiation` (novel) |
| **S4 Decision** | Einstein *declines* Caltech and Oxford; *accepts* IAS; affiliation moves Berlin → Princeton | temporal **supersession** of opportunity status + affiliation |
| **S5 Noise** | "Einstein played violin at Flexner's home"; "chatted about sailing with Veblen" | one-off relations that must **not** promote |

Planted **synonyms**: applied / agreed to consider / put his name forward · met with / spoke to /
was introduced to / interviewed by · recommended / referred / put in a good word.
Planted **aliases**: Einstein = {Albert, Dr. Einstein, A. Einstein}; IAS = {the Institute,
Institute for Advanced Study, Princeton}.

### 10.3 Probe queries (asked identically of both pipelines)

| Probe | What it reveals |
|---|---|
| "Which opportunity did Einstein accept, and its status?" | typed retrieval + supersession |
| "Who referred Einstein to IAS?" | withheld `referred-by` — **A: gap · B: discovered** |
| "Where & when did we learn Einstein accepted IAS?" | provenance / lineage |
| count distinct relation types for the *met/interviewed* concept | synonym collapse (cluster purity) |
| re-ask after S5: "is `interviewed-by` a known relation now?" | B **recompute/improvement**; A flat |
| fraction of *all* ingested facts retrievable | B's "nothing dropped" coverage |
| "What competing opportunities did Einstein weigh?" | did the early informal **leads** survive? |

### 10.4 Scorecard — the six dimensions

Score both runs against `skills/tech-recon/schema/memory_eval.yaml` (the same rubric the
investigation used), which turns this scenario into the **schema-first curation benchmark** the
investigation flagged as missing:

- **Fact coverage/recall** — % ingested facts retrievable (B's headline; *longitudinal*).
- **Schema-gap debt** (A) — count of facts that couldn't be typed = the curation cost A imposes.
- **Induced-schema quality** (B) — precision/recall of discovered types vs. the withheld answer
  key + predicate-cluster purity (*schema conformance*).
- **Time-to-queryable & cost** — A immediate; B needs an inference pass (measure lag + LLM calls).
- **Stability under re-run** — does B's derived schema converge or thrash across S1→S5? Does A's
  gap debt accumulate? (*longitudinal*).
- **Provenance completeness** — can each answer source+timestamp for a sampled fact set?
- **Contradiction handling** — was the Caltech/Oxford → IAS supersession resolved correctly?

**Controls:** full-context (no memory layer) and raw Mem0 (no TypeDB), so the contribution of each
layer is visible — the same framing the investigation used.

### 10.5 Pitfalls to respect

- **Ground truth first** — fix the narrative script, the withheld target ontology, and the
  alias/supersession answers before running anything.
- **Extraction is nondeterministic** — fix the seed + script, run multiple trials, report variance.
- **A "win" for B only counts if you actually promote** — otherwise you are scoring a dumb triple
  store (the §5.4 crux).
