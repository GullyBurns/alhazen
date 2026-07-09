#!/usr/bin/env python3
"""
Ingest staged ChEMBL JSON data into TypeDB using the demo schema.

Loads target, compounds, assays, and bioactivities from the data/ directory
into the alhazen_notebook database. The demo schema (schema.tql) must be
loaded first.

Usage:
    # Load schema first (one-time)
    python ingest.py load-schema

    # Ingest data
    python ingest.py ingest

    # Verify
    python ingest.py verify
"""

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alhazen_notebook")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")

DATA_DIR = Path(__file__).parent / "data"
SCHEMA_FILE = Path(__file__).parent / "schema.tql"


def get_driver():
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


def skolem_id(prefix: str, *keys) -> str:
    """Generate a deterministic ID from keys."""
    key_str = "|".join(str(k) for k in keys)
    h = hashlib.sha256(key_str.encode()).hexdigest()[:12]
    return f"{prefix}-{h}"


def escape(s) -> str:
    """Escape string for TypeQL."""
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def cmd_load_schema(args):
    """Load the demo-chembl schema into TypeDB."""
    schema = SCHEMA_FILE.read_text()
    driver = get_driver()
    try:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.SCHEMA) as tx:
            tx.query(f"define\n{schema}").resolve()
            tx.commit()
        print(json.dumps({"success": True, "message": "Schema loaded"}))
    finally:
        driver.close()


def cmd_ingest(args):
    """Ingest staged ChEMBL data into TypeDB."""
    # Load data files
    target = json.loads((DATA_DIR / "target.json").read_text())
    molecules = json.loads((DATA_DIR / "molecules.json").read_text())
    assays = json.loads((DATA_DIR / "assays.json").read_text())
    activities = json.loads((DATA_DIR / "activities.json").read_text())

    driver = get_driver()
    stats = {"target": 0, "compounds": 0, "assays": 0, "activities": 0, "relations": 0}

    try:
        # 1. Insert target
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tid = skolem_id("demo-target", target["target_chembl_id"])
            gene = ""
            uniprot = ""
            for comp in target.get("target_components", []):
                uniprot = comp.get("accession", "")
                # Try to get gene symbol from component synonyms
                for syn in comp.get("target_component_synonyms", []):
                    if syn.get("syn_type") == "GENE_SYMBOL":
                        gene = syn.get("component_synonym", "")
                        break

            tx.query(f'''
                insert $t isa demo-target,
                    has id "{tid}",
                    has name "{escape(target["pref_name"])}",
                    has demo-chembl-id "{target["target_chembl_id"]}",
                    has demo-uniprot-id "{escape(uniprot)}",
                    has demo-gene-symbol "{escape(gene)}",
                    has demo-organism "{escape(target.get("organism", ""))}",
                    has demo-target-type "{escape(target.get("target_type", ""))}";
            ''').resolve()
            tx.commit()
            stats["target"] = 1
            print(f"Target: {target['pref_name']} ({tid})")

        # 2. Insert compounds (batch)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            for mol in molecules:
                cid = skolem_id("demo-compound", mol["molecule_chembl_id"])
                smiles = ""
                if mol.get("molecule_structures"):
                    smiles = mol["molecule_structures"].get("canonical_smiles", "") or ""

                props = mol.get("molecule_properties") or {}
                mw = props.get("full_mwt")
                alogp = props.get("alogp")
                max_phase = mol.get("max_phase")

                q = f'''insert $c isa demo-compound,
                    has id "{cid}",
                    has name "{escape(mol.get("pref_name") or mol["molecule_chembl_id"])}",
                    has demo-chembl-id "{mol["molecule_chembl_id"]}"'''

                if smiles:
                    q += f',\n                    has demo-smiles "{escape(smiles[:500])}"'
                if mw is not None:
                    try:
                        q += f",\n                    has demo-molecular-weight {float(mw)}"
                    except (ValueError, TypeError):
                        pass
                if alogp is not None:
                    try:
                        q += f",\n                    has demo-alogp {float(alogp)}"
                    except (ValueError, TypeError):
                        pass
                if max_phase is not None:
                    try:
                        q += f",\n                    has demo-max-phase {int(max_phase)}"
                    except (ValueError, TypeError):
                        pass

                q += ";"
                try:
                    tx.query(q).resolve()
                    stats["compounds"] += 1
                except Exception as e:
                    print(f"  Skip compound {mol['molecule_chembl_id']}: {e}", file=sys.stderr)

            tx.commit()
            print(f"Compounds: {stats['compounds']}")

        # 3. Insert assays (batch)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            for assay in assays:
                aid = skolem_id("demo-assay", assay["assay_chembl_id"])
                q = f'''insert $a isa demo-assay,
                    has id "{aid}",
                    has name "{escape((assay.get("description") or assay["assay_chembl_id"])[:200])}",
                    has demo-chembl-id "{assay["assay_chembl_id"]}",
                    has demo-assay-type "{escape(assay.get("assay_type", ""))}";'''
                try:
                    tx.query(q).resolve()
                    stats["assays"] += 1
                except Exception as e:
                    print(f"  Skip assay {assay['assay_chembl_id']}: {e}", file=sys.stderr)

            tx.commit()
            print(f"Assays: {stats['assays']}")

        # 4. Insert bioactivities with relations (batch)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            for act in activities:
                act_id = skolem_id("demo-activity",
                                    act["molecule_chembl_id"],
                                    act["assay_chembl_id"],
                                    act.get("activity_id", ""))
                comp_id = skolem_id("demo-compound", act["molecule_chembl_id"])
                target_id = skolem_id("demo-target", act["target_chembl_id"])
                assay_id = skolem_id("demo-assay", act["assay_chembl_id"])

                # Insert bioactivity entity
                pchembl = act.get("pchembl_value")
                std_val = act.get("standard_value")

                q = f'''insert $b isa demo-bioactivity,
                    has id "{act_id}",
                    has name "IC50 {act["molecule_chembl_id"]} vs {act["target_chembl_id"]}",
                    has demo-chembl-id "{act.get("activity_id", act_id)}",
                    has demo-activity-type "{escape(act.get("standard_type", ""))}"'''

                if std_val is not None:
                    try:
                        q += f",\n                    has demo-activity-value {float(std_val)}"
                    except (ValueError, TypeError):
                        pass
                q += f',\n                    has demo-activity-units "{escape(act.get("standard_units", ""))}"'
                q += f',\n                    has demo-activity-relation "{escape(act.get("standard_relation", "="))}"'
                if pchembl is not None:
                    try:
                        q += f",\n                    has demo-pchembl-value {float(pchembl)}"
                    except (ValueError, TypeError):
                        pass
                q += ";"

                try:
                    tx.query(q).resolve()
                    stats["activities"] += 1
                except Exception as e:
                    print(f"  Skip activity {act_id}: {e}", file=sys.stderr)
                    continue

                # Insert relation linking compound, target, assay
                rel_q = f'''
                    match
                        $c isa demo-compound, has id "{comp_id}";
                        $t isa demo-target, has id "{target_id}";
                        $a isa demo-assay, has id "{assay_id}";
                    insert
                        (demo-bm-compound: $c, demo-bm-target: $t, demo-bm-assay: $a)
                            isa demo-bioactivity-measurement;
                '''
                try:
                    tx.query(rel_q).resolve()
                    stats["relations"] += 1
                except Exception:
                    pass  # Skip if entities missing

            tx.commit()
            print(f"Activities: {stats['activities']}, Relations: {stats['relations']}")

    finally:
        driver.close()

    print(json.dumps({"success": True, "stats": stats}))


def cmd_clean(args):
    """Delete all demo-* entities and relations from the target DB.

    Used to reset before re-running the GLAV pipeline so the data is built
    by the declarative rules rather than direct Python ingestion.
    """
    driver = get_driver()
    try:
        # Delete relations first (they reference entities)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query('''
                match $r isa demo-bioactivity-measurement;
                delete $r;
            ''').resolve()
            tx.commit()
        # Delete entities
        for etype in ["demo-bioactivity", "demo-assay", "demo-compound", "demo-target"]:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                tx.query(f'''
                    match $e isa {etype};
                    delete $e;
                ''').resolve()
                tx.commit()
        print(json.dumps({"success": True, "message": "Demo data cleaned"}))
    finally:
        driver.close()


def cmd_verify(args):
    """Run verification queries against the loaded data."""
    driver = get_driver()
    try:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            # Count entities
            for etype in ["demo-target", "demo-compound", "demo-assay", "demo-bioactivity"]:
                results = list(tx.query(f'''
                    match $e isa {etype};
                    fetch {{ "id": $e.id }};
                ''').resolve())
                print(f"{etype}: {len(results)}")

            # Count relations via the result role (distinct per bioactivity).
            # Binding only compound/target/assay collapses measurements that
            # share a triple; demo-bm-result gives the true per-measurement count.
            rels = list(tx.query('''
                match
                    $m isa demo-bioactivity-measurement,
                        links (demo-bm-result: $b);
                fetch { "b": $b.id };
            ''').resolve())
            print(f"demo-bioactivity-measurement relations: {len(rels)}")

            # Sample cross-domain query: most potent compounds
            potent = list(tx.query('''
                match
                    $b isa demo-bioactivity, has demo-pchembl-value $pv;
                    $b has demo-activity-value $val;
                    $b has name $bname;
                    $pv > 8.0;
                fetch {
                    "name": $bname,
                    "pchembl": $pv,
                    "ic50_nM": $val
                };
            ''').resolve())
            print(f"\nPotent compounds (pChEMBL > 8.0): {len(potent)}")
            for p in potent[:5]:
                print(f"  {p.get('name')}: pChEMBL={p.get('pchembl')}, IC50={p.get('ic50_nM')}nM")

    finally:
        driver.close()


def main():
    parser = argparse.ArgumentParser(description="ChEMBL demo ingestion")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("load-schema", help="Load demo-chembl schema into TypeDB")
    sub.add_parser("ingest", help="Ingest staged ChEMBL data")
    sub.add_parser("clean", help="Delete all demo-* entities and relations")
    sub.add_parser("verify", help="Run verification queries")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    {"load-schema": cmd_load_schema, "ingest": cmd_ingest, "clean": cmd_clean, "verify": cmd_verify}[args.command](args)


if __name__ == "__main__":
    main()
