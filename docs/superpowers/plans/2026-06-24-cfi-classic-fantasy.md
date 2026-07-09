# Classic Fantasy Imperative (CFI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Classic Fantasy Imperative (CFI) playable through the existing mythras-gm Gamesmaster framework by adding a per-campaign `system` flag, system-scoped rules loading, and the full CFI SRD content — without changing the dice engine.

**Architecture:** CFI reuses `mythras_engine.py`/`campaign_io.py`/`novelist.py` unchanged. Two additive schema attributes (`myth-system` on campaign, `myth-rule-system` on rule) let both rulesets coexist. `load-rules` becomes system-scoped so CFI and Mythras rules live in one graph. CFI content is sliced from the SRD into frontmatter'd rule pieces under a new `rules-cfi/` tree.

**Tech Stack:** Python 3.11–3.13, `typedb-driver>=3.8.0,<3.9`, `pyyaml`, pytest. TypeDB 3.8 (shared Docker container).

## Global Constraints

- **Target repo:** `fourth-wall-gaming/mythras-gm`; skill code under `skills/mythras-gm/`. All work on branch `feat/classic-fantasy-imperative` in a worktree at `/Users/gullyburns/Documents/GitHub/mythras-gm-cfi`.
- **Python:** `requires-python = ">=3.11,<3.14"`. Run the CLI with `uv run --project skills/mythras-gm python skills/mythras-gm/mythras_gm.py <cmd>`.
- **TypeDB is shared.** `make db-export` (in the alhazen repo) BEFORE any schema change. Only additive `define` — never `db-init`/`build-db`.
- **Default system is `mythras`** everywhere: absent `myth-system`/`myth-rule-system`/frontmatter `system:` reads as `"mythras"`. Existing data must keep working untouched.
- **TypeDB 3.x gotchas:** bind a variable in every match (never `match X sub Y;`); generate JSON with `ensure_ascii=False`; relation match uses `links (role: $x)`; `delete $x;` (no type qualifier); no `limit` in fetch; ASCII-only in schema files.
- **External skill rule:** fixes/content live upstream. The live skill is the symlinked `main` working tree; nothing ships to players until merged to `main`.
- **Tests:** pure logic → pytest in `tests/` (no TypeDB, per existing convention). DB integration → CLI smoke-test steps with cleanup.

---

## Phase A — Plumbing

### Task 1: Isolated worktree + verified DB backup

**Files:**
- Create (worktree): `/Users/gullyburns/Documents/GitHub/mythras-gm-cfi` (branch `feat/classic-fantasy-imperative`)

**Interfaces:**
- Produces: the working tree all later tasks edit; a verified DB backup zip.

- [ ] **Step 1: Back up the shared TypeDB** (run in the alhazen repo, separate tool call — never chain with `rm`/`make build`)

Run: `cd /Users/gullyburns/skillful-alhazen && make db-export`
Expected: prints a timestamped zip path under `~/.alhazen/cache/typedb/`.

- [ ] **Step 2: Verify the backup zip exists and is non-trivial**

Run: `ls -la ~/.alhazen/cache/typedb/*.zip | tail -1`
Expected: a zip > 100 KB dated today.

- [ ] **Step 3: Create the feature worktree** (separate tool call)

Run: `git -C /Users/gullyburns/Documents/GitHub/mythras-gm worktree add ../mythras-gm-cfi -b feat/classic-fantasy-imperative`
Expected: `Preparing worktree (new branch 'feat/classic-fantasy-imperative')`.

- [ ] **Step 4: Confirm the live skill is untouched**

Run: `readlink /Users/gullyburns/skillful-alhazen/local_skills/mythras-gm`
Expected: still points at `.../GitHub/mythras-gm/skills/mythras-gm` (the `main` tree, NOT the worktree).

- [ ] **Step 5: Copy the spec into the worktree and commit**

```bash
mkdir -p /Users/gullyburns/Documents/GitHub/mythras-gm-cfi/docs/specs
cp /Users/gullyburns/skillful-alhazen/docs/superpowers/specs/2026-06-24-cfi-classic-fantasy-design.md \
   /Users/gullyburns/Documents/GitHub/mythras-gm-cfi/docs/specs/
git -C /Users/gullyburns/Documents/GitHub/mythras-gm-cfi add docs/specs/2026-06-24-cfi-classic-fantasy-design.md
git -C /Users/gullyburns/Documents/GitHub/mythras-gm-cfi commit -m "docs: add CFI system design spec"
```

> All subsequent file paths are relative to the worktree root `/Users/gullyburns/Documents/GitHub/mythras-gm-cfi`.

---

### Task 2: Additive schema — `myth-system` + `myth-rule-system`

**Files:**
- Modify: `skills/mythras-gm/schema.tql` (attributes block + `myth-campaign` owns + `myth-rule` owns)

**Interfaces:**
- Produces: live DB attributes `myth-system`, `myth-rule-system` (value string), owned by `myth-campaign` and `myth-rule` respectively.

- [ ] **Step 1: Add the two attribute declarations** to `schema.tql` in the ATTRIBUTES section, after the existing `myth-rule-*` attributes (near line 62):

```tql
attribute myth-system, value string;       # mythras | classic-fantasy (campaign ruleset)
attribute myth-rule-system, value string;  # mythras | classic-fantasy (which ruleset a rule belongs to)
```

- [ ] **Step 2: Add `owns myth-system` to `myth-campaign`** — change the entity block (near line 109) so it reads:

```tql
entity myth-campaign sub alh-collection,
    owns myth-system,
    owns myth-game-date,
    owns myth-current-scene,
    owns myth-session-number,
    plays myth-campaign-membership:campaign;
```

- [ ] **Step 3: Add `owns myth-rule-system` to `myth-rule`** — change the entity block (near line 208) so it reads:

```tql
entity myth-rule sub alh-note,
    owns myth-rule-system,
    owns myth-rule-category,
    owns myth-rule-kind,
    owns myth-rule-domain,
    owns myth-rule-topic,
    plays myth-rule-tagged:rule,
    plays myth-rule-link:rule,
    plays myth-rule-link:linked;
```

- [ ] **Step 4: Apply the additive define to the live shared DB** (separate tool call; backup already taken in Task 1)

```bash
cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi
uv run --project skills/mythras-gm python - <<'PY'
import sys; sys.path.insert(0, "skills/mythras-gm")
from mythras_gm import get_driver, _write
DEFINE = """define
attribute myth-system, value string;
attribute myth-rule-system, value string;
entity myth-campaign owns myth-system;
entity myth-rule owns myth-rule-system;
"""
with get_driver() as d:
    _write(d, DEFINE)
print("defined")
PY
```
Expected: prints `defined` with no error. (If `_write` signature differs, use `driver.transaction(db, TransactionType.SCHEMA)` + `tx.query(DEFINE).resolve()` + `tx.commit()`.)

- [ ] **Step 5: Verify the attributes exist** (bind a variable — never a bare `sub`)

```bash
uv run --project skills/mythras-gm python - <<'PY'
import sys; sys.path.insert(0, "skills/mythras-gm")
from mythras_gm import get_driver, _fetch
with get_driver() as d:
    rows = _fetch(d, 'match $c isa myth-campaign, has id $i; fetch { "id": $i };')
print("campaigns still queryable:", len(rows))
PY
```
Expected: prints a count (existing campaigns survive — additive define is non-destructive).

- [ ] **Step 6: Commit**

```bash
git add skills/mythras-gm/schema.tql
git commit -m "feat(schema): add myth-system and myth-rule-system for dual-ruleset support"
```

---

### Task 3: `create-campaign --system` and surface system in reads

**Files:**
- Modify: `skills/mythras-gm/mythras_gm.py` — `cmd_create_campaign` (line ~240), `cmd_get_campaign` (line ~256), `cmd_get_context` (line ~1441), argparse `create-campaign` (line ~1531)

**Interfaces:**
- Consumes: `args.system` (new).
- Produces: campaigns carry `myth-system`; `get-campaign`/`get-context` output includes `"system"` (defaulting to `"mythras"` when absent).

- [ ] **Step 1: Add `--system` to the argparse block** (line ~1531):

```python
    s = sub.add_parser("create-campaign")
    s.add_argument("--name", required=True)
    s.add_argument("--description")
    s.add_argument("--game-date")
    s.add_argument("--system", default="mythras",
                   choices=["mythras", "classic-fantasy"],
                   help="ruleset for this campaign (default: mythras)")
```

- [ ] **Step 2: Persist `myth-system` in `cmd_create_campaign`** — change the insert (line ~243) to:

```python
    q = f'''insert $c isa myth-campaign,
        has id "{cid}", has name "{escape_string(args.name)}",
        has myth-system "{escape_string(args.system)}",
        has myth-session-number 0, has created-at {ts}'''
```

- [ ] **Step 3: Surface `system` in `cmd_get_campaign`** — add `"myth-system"` to the attr list (line ~258):

```python
        c = _get_entity(driver, "myth-campaign", args.campaign,
                        ["myth-system", "description", "content", "myth-game-date",
                         "myth-current-scene", "myth-session-number"])
    if not c:
        fail(f"No campaign '{args.campaign}'")
    c.setdefault("myth-system", "mythras")
    out({"success": True, "campaign": c})
```

- [ ] **Step 4: Surface `system` in `cmd_get_context`** — add `"myth-system"` to the campaign attr list (line ~1441) and default it:

```python
        camp = _get_entity(driver, "myth-campaign", args.campaign,
                           ["myth-system", "description", "content", "myth-game-date",
                            "myth-current-scene", "myth-session-number"])
        if not camp:
            fail(f"No campaign '{args.campaign}'")
        camp.setdefault("myth-system", "mythras")
```

- [ ] **Step 5: Smoke-test (live DB, with cleanup)**

```bash
cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi
CLI="uv run --project skills/mythras-gm python skills/mythras-gm/mythras_gm.py"
CID=$($CLI create-campaign --name "CFI Smoke" --system classic-fantasy 2>/dev/null | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
$CLI get-campaign --campaign "$CID" 2>/dev/null | python -c "import sys,json;c=json.load(sys.stdin)['campaign'];assert c['myth-system']=='classic-fantasy',c;print('OK system=',c['myth-system'])"
# cleanup
uv run --project skills/mythras-gm python - "$CID" <<'PY'
import sys; sys.path.insert(0,"skills/mythras-gm")
from mythras_gm import get_driver,_write
cid=sys.argv[1]
with get_driver() as d: _write(d, f'match $c isa myth-campaign, has id "{cid}"; delete $c;')
print("cleaned")
PY
```
Expected: `OK system= classic-fantasy` then `cleaned`.

- [ ] **Step 6: Verify a default-system campaign reads as mythras**

```bash
CID=$($CLI create-campaign --name "Default Smoke" 2>/dev/null | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
$CLI get-campaign --campaign "$CID" 2>/dev/null | python -c "import sys,json;c=json.load(sys.stdin)['campaign'];assert c['myth-system']=='mythras',c;print('OK default mythras')"
uv run --project skills/mythras-gm python - "$CID" <<'PY'
import sys; sys.path.insert(0,"skills/mythras-gm")
from mythras_gm import get_driver,_write
with get_driver() as d: _write(d, f'match $c isa myth-campaign, has id "{sys.argv[1]}"; delete $c;')
print("cleaned")
PY
```
Expected: `OK default mythras` then `cleaned`.

- [ ] **Step 7: Commit**

```bash
git add skills/mythras-gm/mythras_gm.py
git commit -m "feat(cli): create-campaign --system; surface system in get-campaign/get-context"
```

---

### Task 4: System-scoped `load-rules`

**Files:**
- Modify: `skills/mythras-gm/mythras_gm.py` — add pure helper `_piece_system`, rewrite `cmd_load_rules` (line ~1253), argparse `load-rules` (line ~1741)
- Test: `tests/test_rules_system.py` (new, pure — no TypeDB)

**Interfaces:**
- Produces: `_piece_system(meta) -> str` (frontmatter `system`, default `"mythras"`); `load-rules --system <s> [--dir <d>]` that loads only pieces whose frontmatter system == `<s>`, clears only that system's existing pieces, and tags each loaded `myth-rule` with `myth-rule-system`.
- Consumed by: Tasks 6–19 (content loading), Task 21 (e2e).

- [ ] **Step 1: Write the failing pure-logic test** — `tests/test_rules_system.py`:

```python
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "mythras-gm"))
import mythras_gm as gm

def test_piece_system_defaults_to_mythras():
    assert gm._piece_system({"id": "combat/impale"}) == "mythras"

def test_piece_system_reads_frontmatter():
    assert gm._piece_system({"id": "cfi/spell-heal", "system": "classic-fantasy"}) == "classic-fantasy"

def test_piece_system_strips_and_lowercases():
    assert gm._piece_system({"system": " Classic-Fantasy "}) == "classic-fantasy"
```

- [ ] **Step 2: Run it to confirm it fails**

Run: `cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi && uv run --project skills/mythras-gm python -m pytest tests/test_rules_system.py -v`
Expected: FAIL — `AttributeError: module 'mythras_gm' has no attribute '_piece_system'`.

- [ ] **Step 3: Add the `_piece_system` helper** just above `cmd_load_rules` (line ~1253):

```python
def _piece_system(meta):
    """The ruleset a rule piece belongs to; frontmatter `system`, default mythras."""
    return str(meta.get("system", "mythras")).strip().lower() or "mythras"
```

- [ ] **Step 4: Run the pure test to confirm it passes**

Run: `uv run --project skills/mythras-gm python -m pytest tests/test_rules_system.py -v`
Expected: PASS (3 tests).

- [ ] **Step 5: Rewrite `cmd_load_rules`** (line ~1253) to be system-scoped. Replace the whole function body with:

```python
def cmd_load_rules(args):
    """Walk <dir>/*.md (frontmatter + body) and (re)build the rules graph for ONE
    system. Idempotent per-system: clears only this system's myth-rule pieces,
    their tags, and their links, then reloads. Shared facets are reused, never
    deleted (the other system may still tag them). Rules are GLOBAL (no campaign).
    """
    import campaign_io
    system = (args.system or "mythras").strip().lower()
    rules_dir = args.dir or RULES_DIR
    if not os.path.isdir(rules_dir):
        fail(f"No rules directory: {rules_dir}")

    pieces = []
    for root, _dirs, files in os.walk(rules_dir):
        for fn in sorted(files):
            if not fn.endswith(".md"):
                continue
            meta, body = campaign_io._parse_md(os.path.join(root, fn))
            if not meta.get("id"):
                continue
            if _piece_system(meta) != system:
                continue
            meta["content"] = body
            pieces.append(meta)

    if not pieces:
        fail(f"No rule files with frontmatter `id` and system '{system}' under {rules_dir}")

    with get_driver() as driver:
        # Clear ONLY this system's graph. Delete tags/links that touch a rule of
        # this system, then the rule entities. Leave facets (shared) in place.
        _write(driver, f'''
            match $r isa myth-rule, has myth-rule-system "{escape_string(system)}";
                  $rel isa myth-rule-tagged, links (rule: $r);
            delete $rel;''')
        _write(driver, f'''
            match $r isa myth-rule, has myth-rule-system "{escape_string(system)}";
                  $rel isa myth-rule-link, links (rule: $r);
            delete $rel;''')
        _write(driver, f'''
            match $r isa myth-rule, has myth-rule-system "{escape_string(system)}";
            delete $r;''')

        ts = get_timestamp()
        for p in pieces:
            rid = p["id"]
            q = f'''insert $r isa myth-rule,
                has id "{escape_string(rid)}",
                has name "{escape_string(p.get("title", rid))}",
                has myth-rule-system "{escape_string(system)}",
                has myth-rule-category "{escape_string(p.get("category", p.get("domain", "core")))}",
                has myth-rule-kind "{escape_string(p.get("kind", "reference"))}",
                has myth-rule-domain "{escape_string(p.get("domain", p.get("category", "core")))}",
                has myth-rule-topic "{escape_string(p.get("topic", ""))}",
                has created-at {ts}'''
            if p.get("summary"):
                q += f', has description "{escape_string(p["summary"])}"'
            if p.get("content"):
                q += f', has content "{escape_string(p["content"])}"'
            q += ";"
            _write(driver, q)

            for dim, values in (p.get("facets") or {}).items():
                for value in (values if isinstance(values, list) else [values]):
                    fid = _get_or_create_facet(driver, dim, str(value))
                    _write(driver, f'''
                        match
                          $r isa myth-rule, has id "{escape_string(rid)}";
                          $f isa myth-rule-facet, has id "{escape_string(fid)}";
                        insert (rule: $r, facet: $f) isa myth-rule-tagged;''')

        # Links in a second pass. A CFI piece may link to a Mythras piece, so do
        # not constrain target system here; just require the target to exist.
        link_count = 0
        for p in pieces:
            rid = p["id"]
            for target in (p.get("links") or []):
                if _fetch(driver, f'''
                        match $t isa myth-rule, has id "{escape_string(target)}";
                        fetch {{ "id": $t.id }};'''):
                    _write(driver, f'''
                        match
                          $r isa myth-rule, has id "{escape_string(rid)}";
                          $t isa myth-rule, has id "{escape_string(target)}";
                        insert (rule: $r, linked: $t) isa myth-rule-link;''')
                    link_count += 1

    out({"success": True, "system": system,
         "rules_loaded": len(pieces), "links_loaded": link_count})
```

- [ ] **Step 6: Add `--system` to the `load-rules` argparse** (line ~1741):

```python
    s = sub.add_parser("load-rules",
                       help="(Re)build the rules graph for one system from <dir>/*.md")
    s.add_argument("--dir", help="rules directory (default: skill's rules/)")
    s.add_argument("--system", default="mythras",
                   choices=["mythras", "classic-fantasy"],
                   help="only load/replace pieces of this ruleset (default: mythras)")
```

- [ ] **Step 7: Coexistence smoke-test** — load Mythras, then a tiny CFI fixture, and confirm neither clobbers the other:

```bash
cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi
CLI="uv run --project skills/mythras-gm python skills/mythras-gm/mythras_gm.py"
# (a) reload mythras from its own tree (frontmatter has no system -> defaults mythras)
$CLI load-rules --system mythras 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);assert d['rules_loaded']>0;print('mythras loaded',d['rules_loaded'])"
# (b) make a 1-file CFI fixture and load it
mkdir -p /tmp/cfi-fix/magic
cat > /tmp/cfi-fix/magic/spell-heal.md <<'MD'
---
id: "cfi/magic/spell-heal"
title: "Heal"
system: "classic-fantasy"
category: "magic"
domain: "magic"
topic: "divine-spells"
kind: "spell"
summary: "Restores hit points to a single location."
facets: {"magic-system": ["divine"], "kind": ["spell"]}
links: []
---
**Heal** restores hit points to a single damaged location.
MD
$CLI load-rules --system classic-fantasy --dir /tmp/cfi-fix 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);assert d['rules_loaded']==1,d;print('cfi loaded',d['rules_loaded'])"
# (c) mythras pieces still present after the CFI load
$CLI list-rules 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);print('total rules now',d['count']);assert d['count']>1"
rm -rf /tmp/cfi-fix
```
Expected: `mythras loaded N`, `cfi loaded 1`, `total rules now N+1` — Mythras pieces survive the CFI load.

- [ ] **Step 8: Commit**

```bash
git add skills/mythras-gm/mythras_gm.py tests/test_rules_system.py
git commit -m "feat(cli): system-scoped load-rules; per-system clear+reload, shared facets preserved"
```

---

### Task 5: `--system` filter on `query-rules` / `list-rules` / `get-rule`

**Files:**
- Modify: `skills/mythras-gm/mythras_gm.py` — `RULE_ATTRS` (line ~1203), `cmd_list_rules` (~1331), `cmd_query_rules` (~1382), argparse for both (~1745, ~1758)

**Interfaces:**
- Consumes: `args.system` (optional; `None` = no filter).
- Produces: each rule result includes `"myth-rule-system"`; passing `--system <s>` returns only that system's pieces.

- [ ] **Step 1: Add `myth-rule-system` to `RULE_ATTRS`** (line ~1203) so reads surface it:

```python
RULE_ATTRS = ["description", "content", "myth-rule-system", "myth-rule-category",
              "myth-rule-kind", "myth-rule-domain", "myth-rule-topic"]
```

- [ ] **Step 2: Add `--system` to both argparse blocks** (lines ~1745 and ~1758), each:

```python
    s.add_argument("--system", choices=["mythras", "classic-fantasy"],
                   help="restrict to one ruleset (default: all)")
```

- [ ] **Step 3: Filter in `cmd_list_rules`** — bind the system attr and filter. Change the fetch + filtering (line ~1340):

```python
        rows = _fetch(driver, '''
            match $r isa myth-rule, has id $i, has name $n,
                  has myth-rule-system $sys,
                  has myth-rule-domain $dm,
                  has myth-rule-topic $tp, has myth-rule-kind $k;
            fetch { "id": $i, "title": $n, "system": $sys,
                    "domain": $dm, "topic": $tp, "kind": $k };''')
        if args.system:
            rows = [r for r in rows if r["system"] == args.system]
        if args.category:
            rows = [r for r in rows if r["domain"] == args.category]
```

- [ ] **Step 4: Filter in `cmd_query_rules`** — after building `ranked` (line ~1406), drop ids not of the requested system before fetching full pieces. Insert right after `ranked = sorted(...)`:

```python
        if args.system:
            keep = set()
            for rid, _ in ranked:
                row = _fetch(driver, f'''
                    match $r isa myth-rule, has id "{escape_string(rid)}",
                          has myth-rule-system "{escape_string(args.system)}";
                    fetch {{ "id": $r.id }};''')
                if row:
                    keep.add(rid)
            ranked = [(rid, sc) for rid, sc in ranked if rid in keep]
```

- [ ] **Step 5: Smoke-test the filter** (uses the CFI fixture again)

```bash
cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi
CLI="uv run --project skills/mythras-gm python skills/mythras-gm/mythras_gm.py"
mkdir -p /tmp/cfi-fix/magic
cat > /tmp/cfi-fix/magic/spell-heal.md <<'MD'
---
id: "cfi/magic/spell-heal"
title: "Heal"
system: "classic-fantasy"
category: "magic"
domain: "magic"
topic: "divine-spells"
kind: "spell"
facets: {"magic-system": ["divine"], "kind": ["spell"]}
---
**Heal** restores hit points.
MD
$CLI load-rules --system classic-fantasy --dir /tmp/cfi-fix 2>/dev/null >/dev/null
$CLI list-rules --system classic-fantasy 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);assert all(r['system']=='classic-fantasy' for r in d['rules']);assert d['count']>=1;print('cfi-only list OK',d['count'])"
$CLI list-rules --system mythras 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);assert all(r['system']=='mythras' for r in d['rules']);print('mythras-only list OK',d['count'])"
rm -rf /tmp/cfi-fix
```
Expected: `cfi-only list OK 1`, `mythras-only list OK N` — clean separation.

- [ ] **Step 6: Commit**

```bash
git add skills/mythras-gm/mythras_gm.py
git commit -m "feat(cli): --system filter on list-rules/query-rules; surface rule system"
```

---

### Task 6: Backfill existing Mythras rules with `myth-rule-system`

**Files:** none (operational — runs the new CLI).

**Interfaces:**
- Produces: every pre-existing `myth-rule` now carries `myth-rule-system="mythras"`, so `--system` filters are complete.

- [ ] **Step 1: Reload Mythras content through the new loader** (frontmatter has no `system:`, so defaults to mythras and back-tags):

```bash
cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi
uv run --project skills/mythras-gm python skills/mythras-gm/mythras_gm.py load-rules --system mythras 2>/dev/null | python -c "import sys,json;print(json.load(sys.stdin))"
```
Expected: `{'success': True, 'system': 'mythras', 'rules_loaded': N, ...}` with N matching the count of `rules/**/*.md` pieces.

- [ ] **Step 2: Confirm no untagged rules remain**

```bash
uv run --project skills/mythras-gm python - <<'PY'
import sys; sys.path.insert(0,"skills/mythras-gm")
from mythras_gm import get_driver, _fetch
with get_driver() as d:
    total=_fetch(d,'match $r isa myth-rule, has id $i; fetch {"id":$i};')
    tagged=_fetch(d,'match $r isa myth-rule, has id $i, has myth-rule-system $s; fetch {"id":$i};')
print("total",len(total),"tagged",len(tagged))
assert len(total)==len(tagged), "some rules missing myth-rule-system"
print("OK all rules tagged")
PY
```
Expected: `total N tagged N` then `OK all rules tagged`.

---

## Phase B — CFI SRD Content (parallelizable)

### Task 7: Content scaffolding — `rules-cfi/` tree, frontmatter contract, validation test

**Files:**
- Create: `skills/mythras-gm/rules-cfi/.gitkeep`
- Create: `skills/mythras-gm/rules-cfi/FRONTMATTER.md` (the contract every slicing task follows)
- Create: `tests/test_cfi_content.py` (walks `rules-cfi/`, validates frontmatter — pure, no TypeDB)

**Interfaces:**
- Produces: the directory layout + the frontmatter contract + a committed validator that every content task must pass.

- [ ] **Step 1: Create the directory and contract doc** — `skills/mythras-gm/rules-cfi/FRONTMATTER.md`:

```markdown
# CFI rule-piece frontmatter contract

Every `.md` file under `rules-cfi/` is ONE small rule piece: YAML frontmatter
then a short Markdown body. Required keys:

- `id`: unique, kebab, prefixed `cfi/<domain>/<slug>` (e.g. `cfi/class/cleric`)
- `title`: human title
- `system`: ALWAYS `"classic-fantasy"`
- `category` / `domain`: one of core|combat|magic|system|character|skill|creature
- `topic`: hierarchy topic within the domain
- `kind`: procedure|table|modifier|special-effect|condition|reference-list|formula|spell|class|race
- `summary`: one-sentence description (becomes the rule's `description`)
- `facets`: dict of dim -> [values]; dims: phase action effect weapon trigger
  body severity condition magic-system stat kind class race
- `links`: list of related rule ids (may target `mythras` pieces by their id)

Worked example — `rules-cfi/magic/spell-heal.md`:

    ---
    id: "cfi/magic/spell-heal"
    title: "Heal"
    system: "classic-fantasy"
    category: "magic"
    domain: "magic"
    topic: "divine-spells"
    kind: "spell"
    summary: "Restores hit points to a single location."
    facets: {"magic-system": ["divine"], "kind": ["spell"]}
    links: ["cfi/magic/casting"]
    ---
    **Heal** restores hit points to a single damaged location...

ASCII only. Keep bodies short — the GM fetches these live during play.
```

- [ ] **Step 2: Write the failing validator test** — `tests/test_cfi_content.py`:

```python
import os, sys, glob
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "skills", "mythras-gm"))
import campaign_io

CFI_DIR = os.path.join(os.path.dirname(__file__), "..", "skills", "mythras-gm", "rules-cfi")
REQUIRED = {"id", "title", "system", "category", "domain", "topic", "kind", "summary"}

def _pieces():
    files = glob.glob(os.path.join(CFI_DIR, "**", "*.md"), recursive=True)
    return [(f, campaign_io._parse_md(f)[0]) for f in files
            if os.path.basename(f) != "FRONTMATTER.md"]

def test_every_piece_has_required_frontmatter():
    bad = []
    for f, meta in _pieces():
        missing = REQUIRED - set(meta)
        if missing:
            bad.append((f, missing))
    assert not bad, f"frontmatter gaps: {bad}"

def test_every_piece_is_classic_fantasy():
    for f, meta in _pieces():
        assert meta.get("system") == "classic-fantasy", f

def test_ids_are_unique_and_prefixed():
    seen = {}
    for f, meta in _pieces():
        rid = meta.get("id", "")
        assert rid.startswith("cfi/"), f
        assert rid not in seen, f"dup id {rid} in {f} and {seen.get(rid)}"
        seen[rid] = f
```

- [ ] **Step 3: Run it — passes vacuously on an empty tree**

Run: `cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi && uv run --project skills/mythras-gm python -m pytest tests/test_cfi_content.py -v`
Expected: PASS (0 pieces — the test asserts over an empty set). This guards every later content task.

- [ ] **Step 4: Commit**

```bash
git add skills/mythras-gm/rules-cfi/FRONTMATTER.md tests/test_cfi_content.py
git commit -m "feat(cfi): rules-cfi scaffolding + frontmatter contract + validator"
```

---

### Content Slicing Procedure (shared by Tasks 8–19)

Each content task is dispatched to its own subagent. The subagent receives: this procedure, the `rules-cfi/FRONTMATTER.md` contract, the worked example `rules/combat/special-effect-impale.md` from the repo, and its row from the table below.

**Procedure (identical for every chapter):**
1. Read the source SRD chapter from a local clone of `https://github.com/raleel/cfi-srd` (clone once to `~/.alhazen/cache/repos/cfi-srd`).
2. Decompose the chapter into small, single-purpose pieces per the "Expected pieces" column. One concept per file (one class, one race, one spell, one procedure, one table).
3. Write each piece to `skills/mythras-gm/rules-cfi/<subdir>/<slug>.md` with frontmatter matching the contract (`system: "classic-fantasy"`, `id: "cfi/<domain>/<slug>"`). Bodies are concise (the GM reads them live). ASCII only; no non-ASCII punctuation.
4. Choose facets from the allowed dims so the GM can retrieve the piece situationally (e.g. a spell → `{"magic-system":["arcane"|"divine"],"kind":["spell"]}`; a class → `{"class":["fighter"],"kind":["class"]}`).
5. Run `uv run --project skills/mythras-gm python -m pytest tests/test_cfi_content.py -v` — must PASS.
6. Commit: `git add skills/mythras-gm/rules-cfi/<subdir> && git commit -m "content(cfi): <chapter>"`.

**Chapter assignment table** (source files in the cfi-srd clone):

| Task | Source file | `rules-cfi/` subdir | domain | Expected pieces |
|---|---|---|---|---|
| 8  | `0001_Characters.md` | `character/` | character | characteristics, derived-attributes, creation-steps, hit-points, luck/magic points |
| 9  | `0002_Culture_and_Races.md` | `race/` | character | one piece per race (human, dwarf, elf, gnome, half-elf, half-orc, halfling) + culture overview |
| 10 | `0003_Classes.md` | `class/` | character | rank-structure overview + one piece per class (cleric, fighter, magic-user, thief, and every other class in the chapter) |
| 11 | `0004_Alignment_and_Passions.md` | `character/` | character | alignment, oaths, passions |
| 12 | `0005_Skills.md` | `skill/` | skill | standard skills, professional skills, class-skill rules |
| 13 | `0006_Money_and_Equipment.md` | `equipment/` | core | currency, weapons table, armor table, gear, common magic items |
| 14 | `0007_Game_System.md` | `system/` | system | one piece per procedure (aging, asphyxiation, falling, rests, rank-advancement/leveling, etc.) |
| 15 | `0008_Combat.md` | `combat/` | combat | only CFI-specific combat deltas vs the shared engine (turn undead, class combat features, etc.) |
| 16 | `0009_Magic.md` | `magic/` | magic | casting, magic points, disciplines, learning, spells-in-memory |
| 17 | `0010_Spells.md` | `magic/` | magic | **one piece per spell** (every arcane and divine spell). `facets.magic-system` = arcane or divine. |
| 18 | `Appendix_A_Monsters_And_Treasures.md` | `creature/` | creature | one reference piece per monster + treasure tables |
| 19 | `Appendix_B_Conversion_Tables.md` | `system/` | system | conversion tables as reference pieces |

> **Note (no silent caps):** Tasks 10 and 17 are open-ended — slice EVERY class and EVERY spell present in the chapter, not a representative subset. If a chapter is too large for one subagent pass, split by sub-section and `log` what remains.

### Tasks 8–19

- [ ] **Task 8** — slice `0001_Characters.md` per the Procedure → `rules-cfi/character/`. Acceptance: `pytest tests/test_cfi_content.py` PASS; pieces committed.
- [ ] **Task 9** — slice `0002_Culture_and_Races.md` → `rules-cfi/race/`. Acceptance: one file per race; validator PASS; committed.
- [ ] **Task 10** — slice `0003_Classes.md` → `rules-cfi/class/`. Acceptance: rank overview + every class as its own piece; validator PASS; committed.
- [ ] **Task 11** — slice `0004_Alignment_and_Passions.md` → `rules-cfi/character/`. Acceptance: alignment/oaths/passions pieces; validator PASS; committed.
- [ ] **Task 12** — slice `0005_Skills.md` → `rules-cfi/skill/`. Acceptance: standard/professional/class-skill pieces; validator PASS; committed.
- [ ] **Task 13** — slice `0006_Money_and_Equipment.md` → `rules-cfi/equipment/`. Acceptance: currency/weapons/armor/gear/magic-items pieces; validator PASS; committed.
- [ ] **Task 14** — slice `0007_Game_System.md` → `rules-cfi/system/`. Acceptance: one piece per procedure incl. rank-advancement; validator PASS; committed.
- [ ] **Task 15** — slice `0008_Combat.md` → `rules-cfi/combat/`. Acceptance: CFI-specific combat deltas only; validator PASS; committed.
- [ ] **Task 16** — slice `0009_Magic.md` → `rules-cfi/magic/`. Acceptance: casting/points/disciplines/learning pieces; validator PASS; committed.
- [ ] **Task 17** — slice `0010_Spells.md` → `rules-cfi/magic/`. Acceptance: one piece PER spell, `magic-system` facet set; validator PASS; committed.
- [ ] **Task 18** — slice `Appendix_A_Monsters_And_Treasures.md` → `rules-cfi/creature/`. Acceptance: per-monster + treasure pieces; validator PASS; committed.
- [ ] **Task 19** — slice `Appendix_B_Conversion_Tables.md` → `rules-cfi/system/`. Acceptance: conversion-table pieces; validator PASS; committed.

---

## Phase C — Integration

### Task 20: USAGE.md CFI sections

**Files:**
- Modify: `skills/mythras-gm/USAGE.md` (add CFI sections); `skills/mythras-gm/SKILL.md` (one-line pointer)

**Interfaces:**
- Produces: GM-facing operating guidance for running a CFI campaign.

- [ ] **Step 1: Add a "Running a Classic Fantasy Imperative campaign" section to USAGE.md** covering:
  - Selecting the system at creation: `create-campaign --system classic-fantasy`.
  - Loading content once: `load-rules --system classic-fantasy --dir rules-cfi`.
  - CFI character creation flow (class → rank from class-skill thresholds → alignment/oath → racial mods), storing `class`/`rank`/`alignment` in the character's `extras-json` and passing class-skill values via `create-character --skills`.
  - CFI magic: arcane vs divine disciplines, spells-in-memory by rank, recording known spells in `spells-json` under `arcane`/`divine` keys.
  - During play, query CFI rules with `query-rules --system classic-fantasy --facet ...`.

- [ ] **Step 2: Add a one-line pointer in SKILL.md** under the rules-graph bullet:

```markdown
  - For Classic Fantasy Imperative campaigns, rules are loaded from `rules-cfi/`
    and filtered with `--system classic-fantasy`. See USAGE.md.
```

- [ ] **Step 3: Commit**

```bash
git add skills/mythras-gm/USAGE.md skills/mythras-gm/SKILL.md
git commit -m "docs(cfi): USAGE guidance for Classic Fantasy campaigns + char creation + magic"
```

---

### Task 21: End-to-end CFI smoke test

**Files:** none (exercises the full stack against the live DB; cleans up).

**Interfaces:**
- Consumes: everything above.
- Produces: evidence a CFI campaign is fully playable.

- [ ] **Step 1: Load the full CFI content**

```bash
cd /Users/gullyburns/Documents/GitHub/mythras-gm-cfi
CLI="uv run --project skills/mythras-gm python skills/mythras-gm/mythras_gm.py"
$CLI load-rules --system classic-fantasy --dir skills/mythras-gm/rules-cfi 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);print('CFI pieces:',d['rules_loaded']);assert d['rules_loaded']>50"
```
Expected: `CFI pieces: N` with N in the hundreds (full SRD).

- [ ] **Step 2: Create a CFI campaign + a class-based PC, query a CFI rule, run one combat roll, then clean up**

```bash
CID=$($CLI create-campaign --name "CFI E2E" --system classic-fantasy 2>/dev/null | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
PC=$($CLI create-character --name "Brother Aldric" --type pc --species human --roll \
     --campaign "$CID" 2>/dev/null | python -c "import sys,json;print(json.load(sys.stdin)['id'])")
$CLI get-context --campaign "$CID" --compact 2>/dev/null | python -c "import sys,json;c=json.load(sys.stdin);assert c['campaign']['myth-system']=='classic-fantasy';print('context system OK')"
$CLI query-rules --system classic-fantasy --facet kind=spell --limit 3 2>/dev/null | python -c "import sys,json;d=json.load(sys.stdin);assert d['count']>=1;assert all(r['myth-rule-system']=='classic-fantasy' for r in d['rules']);print('cfi spell query OK',d['count'])"
$CLI roll-skill --id "$PC" --skill Brawn 2>/dev/null | python -c "import sys,json;json.load(sys.stdin);print('roll OK')"
# cleanup campaign + PC
uv run --project skills/mythras-gm python - "$CID" "$PC" <<'PY'
import sys; sys.path.insert(0,"skills/mythras-gm")
from mythras_gm import get_driver,_write
cid,pc=sys.argv[1],sys.argv[2]
with get_driver() as d:
    _write(d, f'match $c isa myth-character, has id "{pc}"; delete $c;')
    _write(d, f'match $c isa myth-campaign, has id "{cid}"; delete $c;')
print("cleaned")
PY
```
Expected: `context system OK`, `cfi spell query OK N`, `roll OK`, `cleaned`.

- [ ] **Step 3: Full test suite green**

Run: `uv run --project skills/mythras-gm python -m pytest tests/ -v`
Expected: all pass (engine, novelist, rules-system, cfi-content).

---

### Task 22: Push upstream + merge to main

**Files:** none (git/GitHub).

- [ ] **Step 1: Push the feature branch**

```bash
git -C /Users/gullyburns/Documents/GitHub/mythras-gm-cfi push -u origin feat/classic-fantasy-imperative
```

- [ ] **Step 2: Open a PR**

```bash
gh -R fourth-wall-gaming/mythras-gm pr create \
  --head feat/classic-fantasy-imperative --base main \
  --title "feat: Classic Fantasy Imperative system" \
  --body "Adds CFI as a per-campaign system: myth-system/myth-rule-system schema, system-scoped load-rules, --system filters, and the full CFI SRD content under rules-cfi/. Mythras content unchanged. See docs/specs/2026-06-24-cfi-classic-fantasy-design.md."
```

- [ ] **Step 3: After review, merge** (operator decision), then confirm the live skill picks up CFI:

```bash
git -C /Users/gullyburns/Documents/GitHub/mythras-gm checkout main && git -C /Users/gullyburns/Documents/GitHub/mythras-gm pull
ls /Users/gullyburns/skillful-alhazen/local_skills/mythras-gm/rules-cfi/ | head
```
Expected: `rules-cfi/` now present in the live (symlinked) skill.

- [ ] **Step 4: Tear down the worktree**

```bash
git -C /Users/gullyburns/Documents/GitHub/mythras-gm worktree remove ../mythras-gm-cfi
git -C /Users/gullyburns/Documents/GitHub/mythras-gm branch -d feat/classic-fantasy-imperative
```

---

## Self-Review

**Spec coverage:** schema (Task 2) ✓; create-campaign --system (Task 3) ✓; system-scoped load-rules (Task 4) ✓; query/list --system (Task 5) ✓; backfill (Task 6) ✓; rules-cfi/ + full SRD content (Tasks 7–19) ✓; USAGE/char-gen/magic guidance (Task 20) ✓; worktree + DB backup + push upstream (Tasks 1, 22) ✓; e2e success criteria (Task 21) ✓.

**Risks covered:** load-rules destructiveness → per-system clear + coexistence smoke-test (Task 4 Step 7, Task 5 Step 5); shared TypeDB → backup first + additive define only (Tasks 1–2); SRD volume/consistency → frontmatter contract + committed validator gating every content task (Task 7).
