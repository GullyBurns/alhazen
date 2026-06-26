"""
Id-preserving, scope-gated subgraph copier between TypeDB databases.

Copies a namespaced subgraph from a source DB to a target DB PRESERVING original
`id @key` values (no skolemization), so cross-references stay intact. Used for
the per-repo database split (alhazen_notebook -> alh_core / alh_deep_research /
alh_personal / ...), where each migration is a same-schema copy, not a transform.

What it copies, given a scope:
  1. Every ENTITY whose direct type is in scope, with all its attributes,
     preserving `id` (idempotent: skipped if `id` already exists in target).
  2. Every RELATION instance (of any type present) whose role-players are ALL in
     the copied id-set S -- this carries a skill's own relations (scilit-*, ...)
     AND the connecting core relations (alh-aboutness, alh-note-threading, ...)
     while naturally excluding cross-skill relations (a player outside S).

Scope is by ENTITY TYPE LABEL, never by id string: id prefixes do not always
match type prefixes (e.g. `scilit-citation-impact` has ids like `scimpact-...`).
Two scope modes:
  --prefix scilit- --prefix kefed-     (one or more type-label prefixes)
  --types dm-domain,dm-experiment      (explicit allowlist; REQUIRED for `dm-`,
                                        which collides between curation-skill-builder
                                        and dismech-notebook)

Usage:
  uv run python -m skillful_alhazen.utils.subgraph_migrator copy \
      --source-db alh_jun20 --target-db alh_deep_research \
      --prefix scilit- --prefix kefed- [--dry-run]
  uv run python -m skillful_alhazen.utils.subgraph_migrator verify \
      --source-db alh_jun20 --target-db alh_deep_research --prefix scilit-
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")


def get_driver():
    from typedb.driver import Credentials, DriverOptions, TypeDB

    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


# ---------------------------------------------------------------------------
# Value formatting -> TypeQL literal
# ---------------------------------------------------------------------------

def _escape(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def attr_literal(concept: Any) -> str:
    """Render an attribute concept's value as a TypeQL literal."""
    if concept.is_boolean():
        return "true" if concept.try_get_boolean() else "false"
    if concept.is_integer():
        return str(concept.try_get_integer())
    if concept.is_double():
        return repr(concept.try_get_double())
    if concept.is_decimal():
        return f"{concept.try_get_decimal()}dec"
    if concept.is_datetime():
        # python datetime -> 2026-06-04T06:16:21 (T separator, no quotes)
        return concept.try_get_datetime().isoformat()
    if concept.is_datetime_tz():
        return str(concept.try_get_datetime_tz()).replace(" ", "T")
    if concept.is_duration():
        return str(concept.try_get_duration())
    # string (default)
    return '"' + _escape(concept.try_get_string()) + '"'


def _role_name(role_label: str) -> str:
    """`alh-aboutness:subject` -> `subject` (unqualified role for insert)."""
    return role_label.split(":")[-1]


# ---------------------------------------------------------------------------
# Scope
# ---------------------------------------------------------------------------

def in_scope(label: str, prefixes: list[str], types: set[str]) -> bool:
    if types and label in types:
        return True
    return any(label.startswith(p) for p in prefixes)


def _types_with_instances(tx) -> list:
    """Return the list of type concepts that currently have >=1 instance."""
    q = "match $x isa $t; reduce $c = count groupby $t;"
    return [r.get("t") for r in tx.query(q).resolve()]


def scoped_entity_types(tx, prefixes: list[str], types: set[str]) -> list[str]:
    out = []
    for t in _types_with_instances(tx):
        if not t.is_entity_type():
            continue
        label = t.get_label()
        if in_scope(label, prefixes, types):
            out.append(label)
    return sorted(set(out))


def relation_types_present(tx) -> list[str]:
    out = [t.get_label() for t in _types_with_instances(tx) if t.is_relation_type()]
    return sorted(set(out))


def schema_relation_types(tx) -> set[str]:
    """All relation types DEFINED in this DB's schema (regardless of instances)."""
    return {r.get("t").get_label() for r in tx.query("match relation $t;").resolve()}


# ---------------------------------------------------------------------------
# Read source subgraph into memory
# ---------------------------------------------------------------------------

def read_entities(tx, etype: str, direct: bool = False) -> list[dict]:
    """All instances of etype as {id, type, attrs:[(attr_type_label, concept)]}.

    Grouped by `id`; every identifiable-entity owns exactly one `id @key`.
    `direct=True` uses `isa!` (this exact type only, no subtypes) -- needed when
    copying a bare base type (e.g. bare `alh-note`) without dragging its
    namespaced subtypes (scilit-*, jhunt-*) along.
    """
    isa = "isa!" if direct else "isa"
    # `isa! $dt` also captures each instance's direct type, so a `direct` read of
    # an abstract-ish base still records the concrete type for re-insert.
    rows = tx.query(f'match $e {isa} {etype}, has id $id; $e isa! $dt; $e has $a;').resolve()
    by_id: dict[str, dict] = {}
    for r in rows:
        eid = r.get("id").try_get_string()
        a = r.get("a")
        ent = by_id.setdefault(eid, {"id": eid, "type": r.get("dt").get_label(), "attrs": []})
        ent["attrs"].append((a.get_type().get_label(), a))
    return list(by_id.values())


def closure_notes(tx, scope_ids: set[str], note_types: list[str]) -> list[dict]:
    """Bare notes (direct type in note_types) whose aboutness subject -- or, by
    threading, whose parent note -- is in scope. Iterated to a fixpoint so a
    note threaded onto an in-scope note is also pulled. Returns the note entities.
    """
    # candidate notes: id -> (direct type, subject_ids, thread_parent_ids)
    cand: dict[str, dict] = {}
    for nt in note_types:
        for r in tx.query(
            f'match $n isa! {nt}, has id $nid;'
            f' $r isa alh-aboutness, links (note: $n, subject: $s); $s has id $sid;'
        ).resolve():
            c = cand.setdefault(r.get("nid").try_get_string(), {"type": nt, "subj": set(), "parent": set()})
            c["subj"].add(r.get("sid").try_get_string())
    # note-threading parents (note -> earlier note)
    for nt in note_types:
        try:
            for r in tx.query(
                f'match $n isa! {nt}, has id $nid;'
                f' $r isa alh-note-threading, links ($ro1: $n, $ro2: $p); $p has id $pid;'
            ).resolve():
                nid = r.get("nid").try_get_string()
                if nid in cand:
                    cand[nid]["parent"].add(r.get("pid").try_get_string())
        except Exception:
            pass
    included: set[str] = set()
    changed = True
    while changed:
        changed = False
        for nid, c in cand.items():
            if nid in included:
                continue
            if (c["subj"] & scope_ids) or (c["parent"] & (scope_ids | included)):
                included.add(nid)
                changed = True
    # read full entities for included notes
    out = []
    for nt in note_types:
        for ent in read_entities(tx, nt, direct=True):
            if ent["id"] in included:
                out.append(ent)
    return out


def read_relation_instances(tx, rtype: str) -> list[dict]:
    """All instances of rtype as {iid, type, players:[(role, player_id)], attrs:[...]}.

    Grouped by relation IID (relations have no id @key). Relation attributes are
    read separately and guarded: a relation type that owns no attributes raises
    [INF11] on `has $a`, which we treat as "no attributes".
    """
    by_iid: dict[str, dict] = {}
    # `isa! {rtype}`: read this relation by its DIRECT type only, so an instance
    # whose supertype is ALSO enumerated isn't read twice (and isn't re-inserted
    # under the wrong supertype). `isa! $pt` likewise captures each player's
    # direct type, needed so the insert binds a role-compatible type (a free
    # `isa $t` infers a too-general supertype -> [INF4]).
    pq = f'match $r isa! {rtype}, links ($role: $p); $p isa! $pt, has id $pid;'
    try:
        rows = list(tx.query(pq).resolve())
    except Exception:
        # [INF11]: abstract relation type with no direct instances -- its
        # instances are all concrete subtypes, enumerated separately. Skip.
        return []
    for r in rows:
        rel = r.get("r")
        iid = rel.get_iid()
        rec = by_iid.setdefault(iid, {"iid": iid, "type": rtype, "players": [], "attrs": []})
        rec["players"].append((
            _role_name(r.get("role").get_label()),
            r.get("pid").try_get_string(),
            r.get("pt").get_label(),
        ))
    # relation attributes (optional)
    try:
        aq = f'match $r isa! {rtype}, has $a;'
        for r in tx.query(aq).resolve():
            iid = r.get("r").get_iid()
            if iid in by_iid:
                by_iid[iid]["attrs"].append((r.get("a").get_type().get_label(), r.get("a")))
    except Exception:
        pass  # [INF11]: this relation type owns no attributes
    return list(by_iid.values())


# ---------------------------------------------------------------------------
# Target existence checks (idempotency)
# ---------------------------------------------------------------------------

def existing_ids(driver, target_db: str, ids: list[str], chunk: int = 400) -> set[str]:
    from typedb.driver import TransactionType

    found: set[str] = set()
    for i in range(0, len(ids), chunk):
        with driver.transaction(target_db, TransactionType.READ) as tx:
            for eid in ids[i:i + chunk]:
                q = f'match $x isa $t, has id "{_escape(eid)}"; limit 1;'
                if list(tx.query(q).resolve()):
                    found.add(eid)
    return found


def relation_exists(tx, rec: dict) -> bool:
    """True if a relation of the same type with the same role-players exists."""
    links = ", ".join(f"{role}: $p{i}" for i, (role, _, _) in enumerate(rec["players"]))
    binds = "".join(
        f' $p{i} isa {ptype}, has id "{_escape(pid)}";'
        for i, (_, pid, ptype) in enumerate(rec["players"])
    )
    q = f'match $r isa {rec["type"]}, links ({links});{binds} limit 1;'
    try:
        return bool(list(tx.query(q).resolve()))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Insert builders
# ---------------------------------------------------------------------------

def entity_insert_tql(ent: dict) -> str:
    has = ", ".join(f"has {atype} {attr_literal(a)}" for atype, a in ent["attrs"])
    return f'insert $e isa {ent["type"]}, {has};'


def relation_insert_tql(rec: dict) -> str:
    match_parts, link_parts = [], []
    for i, (role, pid, ptype) in enumerate(rec["players"]):
        match_parts.append(f'$p{i} isa {ptype}, has id "{_escape(pid)}";')
        link_parts.append(f"{role}: $p{i}")
    links = ", ".join(link_parts)
    has = "".join(f", has {atype} {attr_literal(a)}" for atype, a in rec["attrs"])
    match = "match " + " ".join(match_parts)
    return f'{match} insert $r links ({links}), isa {rec["type"]}{has};'


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

DEFAULT_NOTE_TYPES = ["alh-note"]


def copy(source_db: str, target_db: str, prefixes: list[str], types: set[str],
         dry_run: bool, also_types: list[str] | None = None,
         closure_note_types: list[str] | None = None, batch: int = 200) -> dict:
    from typedb.driver import TransactionType

    also_types = also_types or []
    driver = get_driver()
    report: dict[str, Any] = {"entities": {}, "relations": {}, "scope_types": [],
                              "closure_notes": 0, "dry_run": dry_run}
    try:
        # --- 1. scope + read entities (scoped types + always-include shared types) ---
        with driver.transaction(source_db, TransactionType.READ) as tx:
            etypes = scoped_entity_types(tx, prefixes, types)
        etypes = sorted(set(etypes) | set(also_types))
        report["scope_types"] = etypes
        all_entities: list[dict] = []
        for et in etypes:
            with driver.transaction(source_db, TransactionType.READ) as tx:
                # direct=True: read by exact type (isa!) so an instance whose
                # parent type is ALSO in scope isn't read twice -> no duplicate
                # id insert ([CNT9] @key violation).
                ents = read_entities(tx, et, direct=True)
            report["entities"][et] = len(ents)
            all_entities.extend(ents)
        scope_ids = {e["id"] for e in all_entities}

        # --- 1b. aboutness closure: pull bare notes about in-scope subjects ---
        if closure_note_types:
            with driver.transaction(source_db, TransactionType.READ) as tx:
                notes = closure_notes(tx, scope_ids, closure_note_types)
            for n in notes:
                if n["id"] not in scope_ids:
                    all_entities.append(n)
                    scope_ids.add(n["id"])
            report["closure_notes"] = len(notes)

        # --- 2. read relations whose players are all in scope AND whose type
        #        exists in the TARGET schema (a shared-ref-only relation like
        #        kefed-licenses must not leak into a DB without kefed types). ---
        with driver.transaction(source_db, TransactionType.READ) as tx:
            rtypes = relation_types_present(tx)
        with driver.transaction(target_db, TransactionType.READ) as tx:
            target_rtypes = schema_relation_types(tx)
        skipped_rtypes = []
        all_recs: list[dict] = []
        for rt in rtypes:
            if rt not in target_rtypes:
                skipped_rtypes.append(rt)
                continue
            with driver.transaction(source_db, TransactionType.READ) as tx:
                all_recs.extend(read_relation_instances(tx, rt))
        if skipped_rtypes:
            report["relation_types_absent_in_target"] = sorted(skipped_rtypes)

        # A relation is in scope when every role-player is either being copied now
        # (scope_ids) OR already present in the target DB (e.g. scilit-paper copied
        # in a prior pass, referenced now by a trec-system-paper-reference). This
        # is what lets cross-skill relations wire up when a shared DB is populated
        # incrementally -- copy the referenced entities FIRST, then the referrers.
        ext_ids = {pid for rec in all_recs for _, pid, _ in rec["players"] if pid not in scope_ids}
        present_ext = existing_ids(driver, target_db, sorted(ext_ids)) if ext_ids else set()
        allowed = scope_ids | present_ext
        report["resolved_external_players"] = len(present_ext)
        # Keep a relation when: every player resolves (in scope now OR already in
        # target) AND at least one player is in the CURRENT scope. The second
        # clause stops us from re-processing relations that live entirely among
        # already-present entities (those were copied by their own pass) -- e.g.
        # a pure scilit-session->scilit-note aboutness must not ride along on the
        # trec copy (and would fail anyway if the source type was since renamed).
        in_scope_rels = []
        for rec in all_recs:
            pids = [pid for _, pid, _ in rec["players"]]
            if pids and all(pid in allowed for pid in pids) and any(pid in scope_ids for pid in pids):
                report["relations"][rec["type"]] = report["relations"].get(rec["type"], 0) + 1
                in_scope_rels.append(rec)

        if dry_run:
            report["totals"] = {
                "entities": len(all_entities),
                "relations": len(in_scope_rels),
            }
            return report

        # --- 3. insert entities (idempotent on id) ---
        already = existing_ids(driver, target_db, [e["id"] for e in all_entities])
        to_insert = [e for e in all_entities if e["id"] not in already]
        inserted_e = 0
        for i in range(0, len(to_insert), batch):
            with driver.transaction(target_db, TransactionType.WRITE) as tx:
                for ent in to_insert[i:i + batch]:
                    tx.query(entity_insert_tql(ent)).resolve()
                    inserted_e += 1
                tx.commit()
        report["inserted_entities"] = inserted_e
        report["skipped_entities"] = len(already)

        # --- 4. insert relations (idempotent on type+players) ---
        inserted_r = skipped_r = 0
        for i in range(0, len(in_scope_rels), batch):
            with driver.transaction(target_db, TransactionType.WRITE) as tx:
                for rec in in_scope_rels[i:i + batch]:
                    if relation_exists(tx, rec):
                        skipped_r += 1
                        continue
                    tx.query(relation_insert_tql(rec)).resolve()
                    inserted_r += 1
                tx.commit()
        report["inserted_relations"] = inserted_r
        report["skipped_relations"] = skipped_r
        return report
    finally:
        driver.close()


def verify(source_db: str, target_db: str, prefixes: list[str], types: set[str]) -> dict:
    """Compare per-entity-type counts between source (in scope) and target."""
    from typedb.driver import TransactionType

    def count(db: str, etype: str) -> int:
        with driver.transaction(db, TransactionType.READ) as tx:
            try:
                rows = list(tx.query(f"match $e isa {etype}; reduce $c = count;").resolve())
                return rows[0].get("c").try_get_integer() if rows else 0
            except Exception:
                return 0

    driver = get_driver()
    out: dict[str, Any] = {"per_type": {}, "ok": True}
    try:
        with driver.transaction(source_db, TransactionType.READ) as tx:
            etypes = scoped_entity_types(tx, prefixes, types)
        for et in etypes:
            sc, tc = count(source_db, et), count(target_db, et)
            out["per_type"][et] = {"source": sc, "target": tc, "match": sc == tc}
            if sc != tc:
                out["ok"] = False
        return out
    finally:
        driver.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _scope_args(p):
    p.add_argument("--source-db", required=True)
    p.add_argument("--target-db", required=True)
    p.add_argument("--prefix", action="append", default=[], help="type-label prefix (repeatable)")
    p.add_argument("--types", default="", help="comma-separated explicit type allowlist")


def main():
    import json

    ap = argparse.ArgumentParser(description="Id-preserving subgraph copier between TypeDB DBs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    cp = sub.add_parser("copy", help="copy a scoped subgraph")
    _scope_args(cp)
    cp.add_argument("--also-types", default="",
                    help="comma-separated shared types to ALWAYS include (e.g. alh-vocabulary,alh-vocabulary-type,alh-tag)")
    cp.add_argument("--closure-notes", default="",
                    help="comma-separated bare note types to pull via aboutness closure "
                         "(default 'alh-note' if flag given with no value)")
    cp.add_argument("--dry-run", action="store_true")
    vp = sub.add_parser("verify", help="compare per-type counts source vs target")
    _scope_args(vp)
    args = ap.parse_args()

    prefixes = args.prefix or []
    types = {t.strip() for t in args.types.split(",") if t.strip()}
    if not prefixes and not types:
        ap.error("provide at least one --prefix or --types")

    if args.cmd == "copy":
        also = [t.strip() for t in args.also_types.split(",") if t.strip()]
        closure = [t.strip() for t in args.closure_notes.split(",") if t.strip()]
        if args.closure_notes == "":
            closure = None
        elif not closure:
            closure = DEFAULT_NOTE_TYPES
        rep = copy(args.source_db, args.target_db, prefixes, types, args.dry_run,
                   also_types=also, closure_note_types=closure)
    else:
        rep = verify(args.source_db, args.target_db, prefixes, types)
    print(json.dumps(rep, indent=2, default=str))


if __name__ == "__main__":
    main()
