#!/usr/bin/env python
"""Migrate scilit-observation-note -> scilit-experience-note (KQED reconciliation).

Idempotent. Run from the worktree root with the project venv:
    uv run python local_resources/typedb/migrate_observation_to_experience.py --dry-run
    uv run python local_resources/typedb/migrate_observation_to_experience.py --apply
"""
import argparse, os, sys
from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB

DB = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
HOST = os.getenv("TYPEDB_HOST", "localhost"); PORT = os.getenv("TYPEDB_PORT", "1729")
USER = os.getenv("TYPEDB_USERNAME", "admin"); PW = os.getenv("TYPEDB_PASSWORD", "password")

def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

def dt(s):  # TypeDB datetime literal, seconds precision, bare (no quotes)
    return str(s).strip().replace(" ", "T").split(".")[0]

def driver():
    return TypeDB.driver(f"{HOST}:{PORT}", Credentials(USER, PW), DriverOptions(is_tls_enabled=False))

SCHEMA_ADD = """
define
attribute scilit-experience-event, value string;
entity scilit-experience-note sub alh-sensemaking-note,
  owns scilit-experience-event;
entity scilit-session plays scilit-hinge:hinged-to;
"""

def type_exists(tx, label):
    # variable-bound (never `match X sub Y;` with two concrete labels)
    rows = list(tx.query(f"match $t sub {label}; fetch {{ \"l\": $t }};").resolve())
    return len(rows) > 0

def read_notes(drv):
    notes = {}
    with drv.transaction(DB, TransactionType.READ) as tx:
        for r in tx.query(
            'match $n isa scilit-observation-note, has id $id, has content $c;'
            ' try { $n has name $nm; }; try { $n has created-at $ca; };'
            ' try { $n has scilit-observation-event $ev; };'
            ' fetch { "id": $id, "c": $c, "nm": $nm, "ca": $ca, "ev": $ev };'
        ).resolve():
            j = r.to_json() if hasattr(r, "to_json") else r
            nid = j["id"]
            notes[nid] = {"id": nid, "content": j.get("c"), "name": j.get("nm"),
                          "created_at": j.get("ca"), "event": j.get("ev"), "subjects": []}
        for r in tx.query(
            'match $n isa scilit-observation-note, has id $nid;'
            ' $r isa alh-aboutness, links (note: $n, subject: $s); $s isa! $st, has id $sid;'
            ' fetch { "nid": $nid, "sid": $sid, "st": $st };'
        ).resolve():
            j = r.to_json() if hasattr(r, "to_json") else r
            st = j["st"]["label"] if isinstance(j["st"], dict) else j["st"]
            if j["nid"] in notes:
                notes[j["nid"]]["subjects"].append((j["sid"], st))
    return list(notes.values())

def apply_schema(drv):
    with drv.transaction(DB, TransactionType.SCHEMA) as tx:
        tx.query(SCHEMA_ADD).resolve(); tx.commit()

def migrate(drv, notes):
    for n in notes:
        with drv.transaction(DB, TransactionType.WRITE) as tx:
            # delete old aboutness rels + old note
            tx.query(f'match $n isa scilit-observation-note, has id "{esc(n["id"])}";'
                     f' $r isa alh-aboutness, links (note: $n); delete $r;').resolve()
            tx.query(f'match $n isa scilit-observation-note, has id "{esc(n["id"])}"; delete $n;').resolve()
            # insert new experience-note (same id)
            parts = [f'has id "{esc(n["id"])}"', f'has content "{esc(n["content"])}"']
            if n.get("name"): parts.append(f'has name "{esc(n["name"])}"')
            if n.get("created_at"): parts.append(f'has created-at {dt(n["created_at"])}')
            if n.get("event"): parts.append(f'has scilit-experience-event "{esc(n["event"])}"')
            tx.query("insert $n isa scilit-experience-note, " + ", ".join(parts) + ";").resolve()
            # re-link aboutness to each subject (match subject by its concrete type)
            for sid, stype in n["subjects"]:
                tx.query(f'match $n isa scilit-experience-note, has id "{esc(n["id"])}";'
                         f' $s isa {stype}, has id "{esc(sid)}";'
                         f' insert (note: $n, subject: $s) isa alh-aboutness;').resolve()
            tx.commit()

def drop_old(drv):
    with drv.transaction(DB, TransactionType.SCHEMA) as tx:
        if type_exists(tx, "scilit-observation-note"):
            tx.query("undefine owns scilit-observation-event from scilit-observation-note;").resolve()
            tx.query("undefine owns scilit-observation-context from scilit-observation-note;").resolve()
            tx.query("undefine scilit-observation-note;").resolve()
        if type_exists(tx, "scilit-observation-event"):
            tx.query("undefine scilit-observation-event;").resolve()
        if type_exists(tx, "scilit-observation-context"):
            tx.query("undefine scilit-observation-context;").resolve()
        tx.commit()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if not (a.apply or a.dry_run):
        print("specify --dry-run or --apply"); sys.exit(2)
    drv = driver()
    try:
        notes = read_notes(drv)
        print(f"scilit-observation-note instances to migrate: {len(notes)}")
        for n in notes:
            print(f"  {n['id']}  event={n['event']!r}  subjects={len(n['subjects'])}")
        if a.dry_run:
            print("DRY-RUN: no writes."); return
        apply_schema(drv);  print("schema add OK")
        migrate(drv, notes); print(f"migrated {len(notes)} notes")
        drop_old(drv);       print("old type/attrs undefined")
        print("MIGRATION COMPLETE")
    finally:
        drv.close()

if __name__ == "__main__":
    main()
