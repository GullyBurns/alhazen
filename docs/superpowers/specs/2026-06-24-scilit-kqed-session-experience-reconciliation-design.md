# Reconcile `scilit-session` + experience notes into the KQED model

**Date:** 2026-06-24
**Skill:** scientific-literature (scilit) — external repo `alhazen-skill-examples/skills/biomed/scientific-literature`
**Status:** Design approved; pending spec review → implementation plan

## Problem

Two entity types were created ad-hoc in the live DB during the CAIS 2026 meeting-survey work and restored from backup on 2026-06-24:

- **`scilit-session`** (`sub alh-domain-thing`) — conference sessions (keynote/workshop/tutorial), owns `scilit-session-type`, `scilit-speaker`, `scilit-affiliation`, `scilit-session-url`, `scilit-publication-year`. 9 instances live.
- **`scilit-observation-note`** (`sub alh-note`) — first-person capture of a talk ("I placed myself at the top of the stack… Konwinski suggested OpenJarvis"), owns `scilit-observation-event`, `scilit-observation-context`. 10 instances live.

Two problems:
1. **Name collision.** KQED already defines `scilit-observation` (`sub alh-note`) as an *epistemic* measurement node (System 2 / KEfED D-node, owns `scilit-knowledge-level`, `scilit-bio-scale`). The CAIS `scilit-observation-note` is a *rhetorical/discourse* capture — a different concept with a colliding name. Both are live.
2. **Not in the model.** Neither type exists in the committed `schema.tql`; they are live-only, so any `make db-init`/`build-db` drops them again (durability gap).

## Conceptual positioning

KQED has three representational systems: **S1 Rhetorical** (claims / gaps / hinges — *domain-neutral*, Teufel + Boguslav), **S2 Epistemic-KEfED** and **S3 Mechanistic** (both *biomed-shaped*: KEfED protocols, bio-scale, bioentities). A conference talk has no experiment and no bio-mechanism — it is pure **discourse**. Therefore sessions + experience notes form scilit's **domain-neutral discourse/source layer**, which sits beside the biomed paper-deep-dive (S2/S3) and never touches it. This is the structural reason a CAIS meeting-survey and a SIRT3 deep-dive can share one schema.

Decision (approved): **lightweight rename** — keep one freeform note per talk, rename it to free the `observation` name, and formalize the session as a first-class source. No decomposition of talk content into claim/gap/hinge primitives in this pass.

## Design

### 1. `scilit-session` → first-class discourse **source** (sibling of `scilit-paper`)

```tql
entity scilit-session sub alh-domain-thing,
    owns scilit-session-type,            # keynote | workshop | tutorial | talk | panel (plain value-set)
    owns scilit-speaker @card(0..),
    owns scilit-affiliation @card(0..),
    owns scilit-session-url,
    owns scilit-publication-year,
    plays scilit-hinge:hinged-to;        # NEW — a claim can cite a talk, exactly as it cites a paper
```

`alh-aboutness:subject` and `alh-collection-membership:member` are already inherited from `alh-domain-thing`. The single KQED-S1 touchpoint is `scilit-hinge:hinged-to`, mirroring the existing `entity scilit-paper plays scilit-hinge:hinged-to`. `scilit-session-type` stays a plain attribute (consistent with the schema's "only small structural value-sets are plain attributes" convention).

### 2. `scilit-observation-note` → `scilit-experience-note`

```tql
entity scilit-experience-note sub alh-sensemaking-note,   # S1 rhetorical layer
    owns scilit-experience-event;        # renamed from scilit-observation-event (e.g. "CAIS 2026 keynote")
```

- A first-person anecdote / engagement record; `about` a source (session / paper) or person via the inherited `alh-aboutness:note` role.
- **Drop** `scilit-observation-context` — 0 live instances use it.
- Frees `scilit-observation` for its KQED epistemic meaning. Collision resolved.
- Namespacing: kept `scilit-` (engagement with scholarly/discourse sources; the meeting-survey is a scilit workflow). Promotion to a core `alh-experience-note` is a clean future move if experiences spread across skills — out of scope here.

### 3. Live migration (`alhazen_notebook`)

1. `make db-export` (backup; verify zip).
2. Schema define: attribute `scilit-experience-event`; entity `scilit-experience-note`; formalize `scilit-session` (idempotent re-define + add `plays scilit-hinge:hinged-to`).
3. Migrate the **10** `scilit-observation-note` instances → `scilit-experience-note`. TypeDB 3.x cannot retype an instance in place, so per note, in one transaction: read content / `name` / `created-at` / `scilit-observation-event` + enumerate all relations (aboutness etc.) → delete old instance → insert new instance with the **same `id`** typed `scilit-experience-note`, mapping `scilit-observation-event` → `scilit-experience-event` → re-link all relations. The 9 `scilit-session` instances stay; they only gain the formalized type + new play.
4. `undefine` old `scilit-observation-note`, then attributes `scilit-observation-event` and `scilit-observation-context` (order: instances migrated → entity → owns → attributes).
5. Verify: 10 `scilit-experience-note`, 0 `scilit-observation-note`, relations preserved, `scilit-observation` (epistemic) untouched. `make db-export` to lock in.

### 4. Upstream commit (`alhazen-skill-examples`) — also closes the durability gap

- Add both entity types + the `scilit-experience-event` attribute to the committed `schema.tql`: `scilit-session` in the sources section (near `scilit-paper`), `scilit-experience-note` in the sensemaking-note section (near the other `scilit-*-note` types), with comments marking them the **discourse/source layer**.
- Update `USAGE.md`: document the **meeting-survey** workflow — sessions as discourse sources, experience notes as first-person engagement records, and how the `survey`-type investigation (e.g. the CAIS 2026 survey) uses them.
- Branch in `alhazen-skill-examples`, commit, push (external-skill-fix-upstream rule). Note: external skill-repo edits are globally visible and not branch-isolated in the parent repo.

## Out of scope (YAGNI)

- Decomposing talk content into `scilit-claim` / `scilit-gap` / `scilit-hinge` primitives (the "fully KQED-native S1" option) — deferred.
- A shared abstract `scilit-source` supertype over paper + session — not needed; both already get the source roles they require.
- Promoting `scilit-experience-note` to a core `alh-experience-note`.
- Generalizing KQED's S2/S3 (biomed-shaped) for non-biomed domains.

## Verification

- Schema: `describe-schema` shows `scilit-session` (+ `hinged-to` play) and `scilit-experience-note` (+ `scilit-experience-event`); `scilit-observation-note` and its two attrs gone; `scilit-observation` (epistemic) intact.
- Data: counts (10 experience, 9 session), spot-check one migrated note's content + `scilit-experience-event` + preserved aboutness link.
- Durability: a fresh `db-init` against the committed schema re-creates both types (no live-only drift).
- Upstream: `git log`/PR in `alhazen-skill-examples` shows the schema + USAGE additions.
