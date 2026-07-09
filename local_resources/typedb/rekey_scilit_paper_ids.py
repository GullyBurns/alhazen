#!/usr/bin/env python
"""Rekey scilit-paper/scilit-preprint entities from a legacy id onto the
canonical deterministic paper_identity() id (see scientific-literature's
paper_identity.py). `id` is a @key attribute, so this is delete-old +
insert-new + relink, not an attribute update -- modeled directly on the
precedent local_resources/typedb/migrate_observation_to_experience.py.

Scope for this run is an explicit candidate list (--candidates), not a
database-wide scan: this is a one-off migration for a specific set of
already-known ids, not a general dedup tool. For each candidate, the target
id is RECOMPUTED from paper_identity() and compared to the current id --
never inferred from the current id's shape (a random scilit-paper-<hex> id
from the old insert_paper() fallback looks identical in shape to a correct
deterministic one, so shape-matching would silently miss it).

Relations preserved (role the paper plays -> the relation's other role):
  alh-representation:referent -> alh-artifact
  alh-collection-membership:member -> collection
  alh-tagging:tagged-entity -> tag
  alh-aboutness:subject (bare) -> note
  scilit-investigation-focus:focal-paper -> investigation
  scilit-sensemaking-paper:paper -> sensemaking
  scilit-impact-citation:citing-paper -> impact
  scilit-hinge:hinged-to -> hinging-claim
  scilit-dataset-usage:paper-entity -> dataset-entity
  scilit-supplementary-material:paper -> supplement
  scilit-claim-mechanism:mechanism -> claim
Relation-owned attributes (created-at, provenance, scilit-hinge-term-id,
scilit-usage-type) are captured and copied onto the re-inserted relation
where present; anything not on this short list is a known simplification of
this one-off migration (documented, not a silent drop).

Also, per rekeyed paper with a fulltext artifact: renames its on-disk cache
directory `~/.alhazen/cache/fulltext/<old-id>/` -> `.../<new-id>/` and updates
that artifact's cache-path/source-uri. And, database-wide: rewrites any
scilit-reference-key value elsewhere that starts with "<old-id>:" to use the
new id (see schema.tql:40 -- a citing-paper-id soft reference).

Run from the worktree root with the project venv:
    uv run python local_resources/typedb/rekey_scilit_paper_ids.py --dry-run
    uv run python local_resources/typedb/rekey_scilit_paper_ids.py --apply
"""
import argparse, os, sys
sys.path.insert(0, os.path.expanduser(
    "/Users/gburns/Documents/Github/skillful-alhazen/local_skills/scientific-literature"))
from paper_identity import paper_identity
from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB

DB = os.getenv("TYPEDB_DATABASE", "alh_deep_research")
HOST = os.getenv("TYPEDB_HOST", "localhost"); PORT = os.getenv("TYPEDB_PORT", "1729")
USER = os.getenv("TYPEDB_USERNAME", "admin"); PW = os.getenv("TYPEDB_PASSWORD", "password")
CACHE_FULLTEXT = os.path.expanduser("~/.alhazen/cache/fulltext")

# This session's ANVIL/IPF candidate set (20 unique PMID-cited papers + 2
# bioRxiv preprints; see conversation for provenance). PACS2-TRPV1 is expected
# to be a no-op (already on the correct scheme) -- kept as a built-in sanity check.
CANDIDATE_OLD_IDS = [
    "doi-10_1164-rccm_200802-313oc",       # PMID 18635891
    "doi-10_1016-j_matbio_2018_03_015",    # PMID 29567124
    "doi-10_1007-s00109-019-01787-9",      # PMID 31025089 (CHOP -- verification target)
    "doi-10_1165-rcmb_2010-0347oc",        # PMID 21169555
    "scilit-paper-0868d8250bbd",           # PMID 35212819 (PACS2-TRPV1 -- expected no-op)
    "doi-10_1371-journal_pone_0189467",    # PMID 29281671
    "doi-10_1164-rccm_200804-550oc",       # PMID 18635888
    "doi-10_1038-s41401-018-0007-9",       # PMID 29925920
    "doi-10_1111-his_14334",               # PMID 33432658
    "doi-10_1371-journal_pone_0158367",    # PMID 27362652 (miR-34)
    "doi-10_21037-jtd_2019_02_11",         # PMID 31019774
    "doi-10_1111-acel_12643",              # PMID 28722352
    "doi-10_1165-rcmb_2019-0071oc",        # PMID 31513752
    "doi-10_1152-ajplung_00220_2017",      # PMID 28860144
    "doi-10_1002-jcp_22448",               # PMID 20945383
    "doi-10_1136-thorax_56_12_907",        # PMID 11713352
    "doi-10_1172-jci_insight_96352",       # PMID 29263297 (pericyte)
    "doi-10_1038-s41598-018-36063-2",      # PMID 30560874
    "doi-10_1152-ajplung_00382_2007",      # PMID 18390830
    "doi-10_1073-pnas_1107559108",         # PMID 21670280
    "scilit-paper-163395a2ea20",           # bioRxiv 2022.03.09.483638 (preprint)
    "scilit-paper-7af438f2622c",           # bioRxiv 2025.06.23.661212 (preprint)
]

# (relation-type, paper's-role, other-role) -- see module docstring for provenance.
ROLE_MAP = [
    ("alh-representation", "referent", "alh-artifact"),
    ("alh-collection-membership", "member", "collection"),
    ("alh-tagging", "tagged-entity", "tag"),
    ("alh-aboutness", "subject", "note"),
    ("scilit-investigation-focus", "focal-paper", "investigation"),
    ("scilit-sensemaking-paper", "paper", "sensemaking"),
    ("scilit-impact-citation", "citing-paper", "impact"),
    ("scilit-hinge", "hinged-to", "hinging-claim"),
    ("scilit-dataset-usage", "paper-entity", "dataset-entity"),
    ("scilit-supplementary-material", "paper", "supplement"),
]
# Only the attributes each relation TYPE actually declares -- TypeDB's type
# inference rejects `has` (even inside try{}) on an attribute the type doesn't
# own at all, so a blanket "try every attribute on every type" is not safe.
RELATION_OWNED_ATTRS = {
    "alh-representation": [],
    "alh-collection-membership": ["created-at", "provenance"],
    "alh-tagging": ["created-at", "provenance"],
    "alh-aboutness": [],
    "scilit-investigation-focus": [],
    "scilit-sensemaking-paper": [],
    "scilit-impact-citation": [],
    "scilit-hinge": ["scilit-hinge-term-id"],
    "scilit-dataset-usage": ["scilit-usage-type", "provenance"],
    "scilit-supplementary-material": [],
}

# Single-valued attributes to copy, by concrete entity type.
SCALAR_ATTRS = {
    "scilit-paper": [
        "name", "abstract-text", "publication-date", "scilit-doi", "scilit-pmid",
        "scilit-pmcid", "scilit-arxiv-id", "scilit-journal-name", "scilit-journal-volume",
        "scilit-journal-issue", "scilit-page-range", "scilit-publication-year",
        "scilit-acquisition-status", "scilit-target-genre", "scilit-citation-load",
        "created-at",
    ],
    "scilit-review": [
        "name", "abstract-text", "publication-date", "scilit-doi", "scilit-pmid",
        "scilit-pmcid", "scilit-arxiv-id", "scilit-journal-name", "scilit-journal-volume",
        "scilit-journal-issue", "scilit-page-range", "scilit-publication-year",
        "scilit-acquisition-status", "scilit-target-genre", "scilit-citation-load",
        "created-at",
    ],
    "scilit-preprint": ["name", "abstract-text", "publication-date", "scilit-doi",
                        "scilit-arxiv-id", "created-at"],
}
MULTI_ATTRS = {
    "scilit-paper": ["scilit-keyword", "scilit-reference-key"],
    "scilit-review": ["scilit-keyword", "scilit-reference-key"],
    "scilit-preprint": [],
}


def esc(s):
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def driver():
    return TypeDB.driver(f"{HOST}:{PORT}", Credentials(USER, PW), DriverOptions(is_tls_enabled=False))


def read_paper(tx, old_id):
    rows = list(tx.query(
        f'match $p isa! $t, has id "{esc(old_id)}"; fetch {{ "type": $t }};'
    ).resolve())
    if not rows:
        return None
    ptype = rows[0]["type"]["label"] if isinstance(rows[0]["type"], dict) else rows[0]["type"]
    doi_rows = list(tx.query(f'match $p has id "{esc(old_id)}"; try {{ $p has scilit-doi $d; }}; '
                              f'fetch {{ "d": $d }};').resolve())
    pmid_rows = list(tx.query(f'match $p has id "{esc(old_id)}"; try {{ $p has scilit-pmid $m; }}; '
                               f'fetch {{ "m": $m }};').resolve())
    doi = doi_rows[0].get("d") if doi_rows else None
    pmid = pmid_rows[0].get("m") if pmid_rows else None

    scalars = {}
    for attr in SCALAR_ATTRS.get(ptype, []):
        rows = list(tx.query(
            f'match $p has id "{esc(old_id)}"; try {{ $p has {attr} $v; }}; fetch {{ "v": $v }};'
        ).resolve())
        if rows and rows[0].get("v") is not None:
            scalars[attr] = rows[0]["v"]

    multis = {}
    for attr in MULTI_ATTRS.get(ptype, []):
        rows = list(tx.query(f'match $p has id "{esc(old_id)}", has {attr} $v; fetch {{ "v": $v }};').resolve())
        vals = [r["v"] for r in rows if r.get("v") is not None]
        if vals:
            multis[attr] = vals

    return {"type": ptype, "doi": doi, "pmid": pmid, "scalars": scalars, "multis": multis}


def read_relations(tx, old_id):
    """For each (reltype, paper_role, other_role) in ROLE_MAP, capture every
    relation instance of that exact type where old_id plays paper_role,
    including the relation's own owned attributes and the other role-player."""
    found = []
    for reltype, prole, orole in ROLE_MAP:
        rows = list(tx.query(
            f'match $p has id "{esc(old_id)}"; $r isa! {reltype}, links ({prole}: $p); '
            f'$r links ({orole}: $o); $o isa! $ot, has id $oid; '
            f'fetch {{ "oid": $oid, "otype": $ot }};'
        ).resolve())
        for row in rows:
            otype = row["otype"]["label"] if isinstance(row["otype"], dict) else row["otype"]
            entry = {"reltype": reltype, "prole": prole, "orole": orole,
                     "other_id": row["oid"], "other_type": otype, "attrs": {}}
            for attr in RELATION_OWNED_ATTRS.get(reltype, []):
                arows = list(tx.query(
                    f'match $p has id "{esc(old_id)}"; $r isa! {reltype}, links ({prole}: $p), '
                    f'links ({orole}: $o); $o has id "{esc(row["oid"])}"; '
                    f'try {{ $r has {attr} $v; }}; fetch {{ "v": $v }};'
                ).resolve())
                if arows and arows[0].get("v") is not None:
                    entry["attrs"][attr] = arows[0]["v"]
            found.append(entry)
    return found


DATETIME_ATTRS = {"created-at", "publication-date"}


def _typeql_literal(v, attr=None):
    if attr in DATETIME_ATTRS:
        # bare (unquoted) datetime literal, seconds precision, no fractional suffix
        return str(v).strip().replace(" ", "T").split(".")[0]
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    return f'"{esc(v)}"'


def plan_for(driver_, old_id):
    with driver_.transaction(DB, TransactionType.READ) as tx:
        paper = read_paper(tx, old_id)
        if not paper:
            return {"old_id": old_id, "error": "not found"}
        target_id, tier, value = paper_identity({"doi": paper["doi"], "pmid": paper["pmid"]})
        if target_id == old_id:
            return {"old_id": old_id, "target_id": target_id, "noop": True}
        collision = list(tx.query(f'match $x has id "{esc(target_id)}"; fetch {{ "id": $x.id }};').resolve())
        if collision:
            return {"old_id": old_id, "target_id": target_id,
                     "error": f"target id already exists on a different entity -- ABORTING this one"}
        relations = read_relations(tx, old_id)
    return {"old_id": old_id, "target_id": target_id, "tier": tier, "value": value,
            "type": paper["type"], "scalars": paper["scalars"], "multis": paper["multis"],
            "relations": relations, "noop": False}


def apply_rekey(driver_, plan):
    old_id, new_id, ptype = plan["old_id"], plan["target_id"], plan["type"]
    with driver_.transaction(DB, TransactionType.WRITE) as tx:
        for rel in plan["relations"]:
            tx.query(
                f'match $p isa {ptype}, has id "{esc(old_id)}"; $r isa! {rel["reltype"]}, '
                f'links ({rel["prole"]}: $p), links ({rel["orole"]}: $o); '
                f'$o has id "{esc(rel["other_id"])}"; delete $r;'
            ).resolve()
        tx.query(f'match $p isa {ptype}, has id "{esc(old_id)}"; delete $p;').resolve()

        attrs = [f'has id "{new_id}"', f'has scilit-identity-basis "{esc(plan["tier"])}"',
                 f'has scilit-identity-value "{esc(plan["value"])}"']
        for attr, v in plan["scalars"].items():
            attrs.append(f'has {attr} {_typeql_literal(v, attr)}')
        for attr, vals in plan["multis"].items():
            for v in vals:
                attrs.append(f'has {attr} {_typeql_literal(v, attr)}')
        tx.query(f'insert $p isa {ptype}, {", ".join(attrs)};').resolve()

        for rel in plan["relations"]:
            rattrs = [f'has {a} {_typeql_literal(v, a)}' for a, v in rel["attrs"].items()]
            rattrs_clause = (", " + ", ".join(rattrs)) if rattrs else ""
            tx.query(
                f'match $p isa {ptype}, has id "{new_id}"; $o isa! {rel["other_type"]}, has id "{esc(rel["other_id"])}"; '
                f'insert $r isa {rel["reltype"]} ({rel["prole"]}: $p, {rel["orole"]}: $o){rattrs_clause};'
            ).resolve()
        tx.commit()

    # Rename the on-disk fulltext cache dir + fix up the artifact's cache-path/source-uri.
    old_dir = os.path.join(CACHE_FULLTEXT, old_id)
    new_dir = os.path.join(CACHE_FULLTEXT, new_id)
    if os.path.isdir(old_dir) and not os.path.exists(new_dir):
        os.rename(old_dir, new_dir)
        with driver_.transaction(DB, TransactionType.WRITE) as tx:
            arts = list(tx.query(
                f'match $p isa {ptype}, has id "{new_id}"; $a isa alh-artifact, has cache-path $cp; '
                f'(alh-artifact: $a, referent: $p) isa alh-representation; '
                f'fetch {{ "aid": $a.id, "cp": $cp }};'
            ).resolve())
            for art in arts:
                old_cp = art["cp"]
                if old_id in old_cp:
                    new_cp = old_cp.replace(old_id, new_id)
                    tx.query(f'match $a isa alh-artifact, has id "{esc(art["aid"])}", has cache-path $v; '
                              f'delete has $v of $a;').resolve()
                    tx.query(f'match $a isa alh-artifact, has id "{esc(art["aid"])}"; '
                              f'insert $a has cache-path "{esc(new_cp)}";').resolve()
            tx.commit()


def fixup_reference_keys(driver_, id_map, dry_run):
    """Rewrite scilit-reference-key values elsewhere in the DB whose citing-paper-id
    prefix is one of the ids we just rekeyed."""
    changes = []
    with driver_.transaction(DB, TransactionType.READ) as tx:
        rows = list(tx.query(
            'match $p isa scilit-paper, has id $pid, has scilit-reference-key $k; '
            'fetch { "pid": $pid, "k": $k };'
        ).resolve())
    for row in rows:
        pid, key = row["pid"], row["k"]
        for old_id, new_id in id_map.items():
            prefix = f"{old_id}:"
            if key.startswith(prefix):
                new_key = new_id + ":" + key[len(prefix):]
                changes.append((pid, key, new_key))
    if not dry_run:
        with driver_.transaction(DB, TransactionType.WRITE) as tx:
            for pid, old_key, new_key in changes:
                tx.query(f'match $p isa scilit-paper, has id "{esc(pid)}", '
                          f'has scilit-reference-key "{esc(old_key)}"; '
                          f'delete $p has scilit-reference-key "{esc(old_key)}";').resolve()
                tx.query(f'match $p isa scilit-paper, has id "{esc(pid)}"; '
                          f'insert $p has scilit-reference-key "{esc(new_key)}";').resolve()
            tx.commit()
    return changes


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    if not (args.apply or args.dry_run):
        print("specify --dry-run or --apply"); sys.exit(2)

    drv = driver()
    try:
        plans = [plan_for(drv, oid) for oid in CANDIDATE_OLD_IDS]
        id_map = {}
        for p in plans:
            print(f"--- {p['old_id']} ---")
            if p.get("error"):
                print(f"  ERROR: {p['error']}")
                continue
            if p.get("noop"):
                print(f"  already correct ({p['target_id']}) -- no-op")
                continue
            print(f"  -> {p['target_id']}  (tier={p['tier']}, type={p['type']})")
            print(f"  relations to preserve: {len(p['relations'])}")
            for rel in p["relations"]:
                print(f"    {rel['reltype']} ({rel['prole']} -> {rel['orole']}) -> {rel['other_type']} {rel['other_id']}")
            id_map[p["old_id"]] = p["target_id"]

        ref_changes = fixup_reference_keys(drv, id_map, dry_run=True)
        print(f"\nscilit-reference-key rewrites needed: {len(ref_changes)}")
        for pid, old_key, new_key in ref_changes:
            print(f"  {pid}: {old_key!r} -> {new_key!r}")

        if args.dry_run:
            print("\nDRY-RUN: no writes.")
            return

        for p in plans:
            if p.get("error") or p.get("noop"):
                continue
            print(f"Rekeying {p['old_id']} -> {p['target_id']} ...")
            apply_rekey(drv, p)
        applied_changes = fixup_reference_keys(drv, id_map, dry_run=False)
        print(f"Rewrote {len(applied_changes)} scilit-reference-key value(s).")
        print("MIGRATION COMPLETE")
    finally:
        drv.close()


if __name__ == "__main__":
    main()
