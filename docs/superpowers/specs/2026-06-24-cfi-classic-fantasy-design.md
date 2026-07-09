# Classic Fantasy Imperative (CFI) as a system in mythras-gm

**Date:** 2026-06-24
**Status:** Design approved, pending spec review
**Target repo:** `fourth-wall-gaming/mythras-gm` (the external skill; `skills/mythras-gm/`)
**Source SRD:** https://github.com/raleel/cfi-srd

## Goal

Make the Classic Fantasy Imperative ruleset playable through the **same**
Gamesmaster framework as Mythras Imperative. CFI is "Mythras with D&D bones":
the d100 dice engine is identical; what differs is the content layer (classes,
ranks, alignment, arcane/divine spell lists) and how characters are built.

Both systems coexist in one skill. Each campaign declares a `system`
(`mythras` | `classic-fantasy`) that scopes the rules the GM sees and how
characters are created.

## Non-goals (v1)

- No changes to `mythras_engine.py` (dice math is shared and correct).
- No changes to existing Mythras content.
- No dashboard (mythras-gm has none).
- No new novelization styles.

## Architecture

### Reused as-is
- **`mythras_engine.py`** — characteristics, derived attributes, hit locations,
  damage modifier, special effects, magic points. System-agnostic.
- **`campaign_io.py`, `novelist.py`** — campaign persistence and novelization.
- **`myth-character`** entity — already stores everything as JSON, including an
  `extras-json` "lossless bag" for system-specific fields and a system-keyed
  `spells-json`. Class / rank / alignment / spells-in-memory fit here with **no
  new character schema**.

### Schema changes (myth- namespace, additive `define` — non-destructive)
Both default to Mythras so all existing data is untouched:

```
attribute myth-system, value string;        # mythras | classic-fantasy
attribute myth-rule-system, value string;   # mythras | classic-fantasy

myth-campaign owns myth-system;
myth-rule     owns myth-rule-system;
```

Additive `define` is non-destructive in TypeDB 3.x; existing rows keep working
(absence of the attribute is read as `mythras`). Back up the shared DB first
regardless (`make db-export`).

### CLI changes (`mythras_gm.py`)

1. **`create-campaign --system classic-fantasy`** (default `mythras`) — stores
   `myth-system` on the campaign.

2. **`load-rules --system <s>` becomes system-scoped.** *This is the key change.*
   Today `load-rules` clears the **entire** rules graph (all `myth-rule`,
   `myth-rule-facet`, tags, links) then reloads from one directory — so two
   systems cannot coexist. New behavior:
   - Reads `system:` from each piece's frontmatter (default `mythras`).
   - Clears/reloads **only the pieces matching `--system`** (and the facets/tags
     they own); leaves the other system's graph intact.
   - Tags each loaded piece with `myth-rule-system`.

3. **`query-rules` / `list-rules` gain `--system`**; results filter to that
   system. `get-context` surfaces the campaign's `myth-system` and defaults rule
   queries to it, so play only ever sees the active ruleset.

4. **Character creation stays CLI-light.** `create-character` already takes
   characteristics/skills/equipment as JSON and lets the engine derive the rest.
   CFI adds **USAGE guidance** for a class/rank/alignment-driven flow; the GM
   passes computed class-skill values and racial modifiers as JSON and records
   `class`, `rank`, `alignment` in `extras-json`. No deep CLI rewrite.

### Content — full SRD

Slice the 12 CFI SRD chapters (~105k words) into small frontmatter'd rule pieces
under a **new `rules-cfi/` tree** (parallel to `rules/`), each carrying
`system: classic-fantasy` and following the existing facet conventions
(`id/title/category/domain/topic/kind/summary/facets/links`).

Approximate decomposition (one subagent per chapter, disjoint subdirs):

| Chapter | Pieces |
|---|---|
| 0001 Characters | characteristics, derived attrs, creation steps |
| 0002 Culture & Races | one piece per race (Human, Dwarf, Elf, Gnome, ½Elf, ½Orc, Halfling) |
| 0003 Classes | one piece per class + rank-structure overview |
| 0004 Alignment & Passions | alignment, oaths, passions |
| 0005 Skills | standard/professional skills, class skills |
| 0006 Money & Equipment | currency, gear, common magic items |
| 0007 Game System | aging, asphyxiation, rests, leveling/rank advancement, misc procedures |
| 0008 Combat | CFI-specific combat deltas vs the shared engine |
| 0009 Magic | casting, magic points, disciplines, learning |
| 0010 Spells | **one piece per spell** (arcane + divine — the 37k-word bulk) |
| Appendix A | monsters & treasures (creature templates / reference) |
| Appendix B | conversion tables |

Plus USAGE.md sections: CFI campaign setup, CFI character creation, CFI magic.

## Workflow / worktree plan

1. **Back up the shared DB** (`make db-export`, verify the zip).
2. **Feature worktree of the external repo** — the live skill (symlinked to the
   repo's `main` working tree) stays untouched:
   `git worktree add ../mythras-gm-cfi -b feat/classic-fantasy-imperative`
   (run from `/Users/gullyburns/Documents/GitHub/mythras-gm`).
3. Apply the additive schema `define` to the shared DB once (myth- is a disjoint
   namespace; safe after backup).
4. **Plumbing first:** schema + the four CLI changes; verify a CFI campaign can
   be created and `load-rules --system classic-fantasy` coexists with Mythras
   rules (Mythras `query-rules` still returns only Mythras pieces).
5. **Fan out content slicing:** one subagent per SRD chapter, each writing to a
   disjoint `rules-cfi/<chapter>/` subdir (no file collisions). Operator reviews
   the merged result.
6. **End-to-end test** from the worktree path: create-campaign (classic-fantasy)
   → create-character (a class) → `query-rules --system classic-fantasy` →
   one combat round via the shared engine.
7. **Commit, push upstream, merge to `main`** (which updates the live symlinked
   skill). Then `make skills-update` is a no-op / pulls the merged content.

## Risks & mitigations

- **`load-rules` destructiveness** — mitigated by making it system-scoped
  (step 4 verifies Mythras rules survive a CFI load and vice versa).
- **Shared TypeDB** — additive `define` only; full export taken first; myth-
  namespace is disjoint from other skills.
- **SRD volume / consistency** — parallel slicing risks uneven frontmatter;
  mitigated by giving every subagent the same frontmatter template + an existing
  rule file as the worked example, then an operator review pass.

## Success criteria

- A `classic-fantasy` campaign and a class-based character can be created.
- `query-rules --system classic-fantasy` returns CFI pieces; a Mythras campaign
  still returns only Mythras pieces (no cross-contamination).
- Full SRD content is loaded as queryable rule pieces.
- All work merged to `fourth-wall-gaming/mythras-gm` main; live skill updated.
