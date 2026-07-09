#!/usr/bin/env python3
"""
Load raw ChEMBL JSON into a throwaway TypeDB staging database.

This is the SOURCE side of the GLAV demo. It creates the `chembl_staging`
database, loads the raw staging schema (staging-schema.tql), and inserts the
fetched ChEMBL JSON "as-is" into flat raw-* entities. The declarative GLAV
rules (mapping/rules/) then read from here and project into the Alhazen
demo schema in `alhazen_notebook`.

Every attribute is written with a sentinel default ("" / 0.0 / 0) when the
source value is missing, so each raw entity is fully populated and matchable
by a single GLAV rule (no silent row drops).

Usage:
    python load_staging.py            # create db, load schema, ingest
    python load_staging.py --reset    # drop and recreate first
"""

import argparse
import json
import os
import sys
from pathlib import Path

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
STAGING_DB = os.getenv("CHEMBL_STAGING_DB", "chembl_staging")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")

DATA_DIR = Path(__file__).parent.parent / "data"
SCHEMA_FILE = Path(__file__).parent / "staging-schema.tql"


def get_driver():
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


def escape(s) -> str:
    if s is None:
        return ""
    return str(s).replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def as_double(v) -> float:
    try:
        return float(v)
    except (ValueError, TypeError):
        return 0.0


def as_int(v) -> int:
    try:
        return int(v)
    except (ValueError, TypeError):
        return 0


def ensure_db(driver, reset: bool):
    exists = driver.databases.contains(STAGING_DB)
    if exists and reset:
        driver.databases.get(STAGING_DB).delete()
        exists = False
    if not exists:
        driver.databases.create(STAGING_DB)
        print(f"Created staging database: {STAGING_DB}")
    schema = SCHEMA_FILE.read_text()
    with driver.transaction(STAGING_DB, TransactionType.SCHEMA) as tx:
        tx.query(schema).resolve()
        tx.commit()
    print("Staging schema loaded")


def load_targets(driver, target):
    """The target.json is a single target object."""
    gene = ""
    uniprot = ""
    for comp in target.get("target_components", []):
        uniprot = comp.get("accession", "") or uniprot
        for syn in comp.get("target_component_synonyms", []):
            if syn.get("syn_type") == "GENE_SYMBOL":
                gene = syn.get("component_synonym", "")
                break
    with driver.transaction(STAGING_DB, TransactionType.WRITE) as tx:
        tx.query(f'''insert $t isa raw-target,
            has chembl-id "{escape(target["target_chembl_id"])}",
            has pref-name "{escape(target.get("pref_name", ""))}",
            has organism "{escape(target.get("organism", ""))}",
            has target-type "{escape(target.get("target_type", ""))}",
            has uniprot-id "{escape(uniprot)}",
            has gene-symbol "{escape(gene)}";''').resolve()
        tx.commit()
    print("Targets: 1")


def load_molecules(driver, molecules):
    count = 0
    with driver.transaction(STAGING_DB, TransactionType.WRITE) as tx:
        for mol in molecules:
            smiles = ""
            if mol.get("molecule_structures"):
                smiles = mol["molecule_structures"].get("canonical_smiles", "") or ""
            props = mol.get("molecule_properties") or {}
            tx.query(f'''insert $m isa raw-molecule,
                has chembl-id "{escape(mol["molecule_chembl_id"])}",
                has pref-name "{escape(mol.get("pref_name") or mol["molecule_chembl_id"])}",
                has smiles "{escape(smiles[:500])}",
                has mol-weight {as_double(props.get("full_mwt"))},
                has alogp {as_double(props.get("alogp"))},
                has max-phase {as_int(mol.get("max_phase"))};''').resolve()
            count += 1
        tx.commit()
    print(f"Molecules: {count}")


def load_assays(driver, assays):
    count = 0
    with driver.transaction(STAGING_DB, TransactionType.WRITE) as tx:
        for assay in assays:
            tx.query(f'''insert $a isa raw-assay,
                has chembl-id "{escape(assay["assay_chembl_id"])}",
                has description "{escape((assay.get("description") or assay["assay_chembl_id"])[:200])}",
                has assay-type "{escape(assay.get("assay_type", ""))}";''').resolve()
            count += 1
        tx.commit()
    print(f"Assays: {count}")


def load_activities(driver, activities):
    count = 0
    with driver.transaction(STAGING_DB, TransactionType.WRITE) as tx:
        for act in activities:
            tx.query(f'''insert $x isa raw-activity,
                has activity-id "{escape(act.get("activity_id", ""))}",
                has molecule-ref "{escape(act.get("molecule_chembl_id", ""))}",
                has target-ref "{escape(act.get("target_chembl_id", ""))}",
                has assay-ref "{escape(act.get("assay_chembl_id", ""))}",
                has standard-type "{escape(act.get("standard_type", ""))}",
                has standard-value {as_double(act.get("standard_value"))},
                has standard-units "{escape(act.get("standard_units", ""))}",
                has standard-relation "{escape(act.get("standard_relation", "="))}",
                has pchembl-value {as_double(act.get("pchembl_value"))};''').resolve()
            count += 1
        tx.commit()
    print(f"Activities: {count}")


def main():
    parser = argparse.ArgumentParser(description="Load ChEMBL JSON into staging TypeDB")
    parser.add_argument("--reset", action="store_true", help="Drop and recreate staging DB")
    args = parser.parse_args()

    target = json.loads((DATA_DIR / "target.json").read_text())
    molecules = json.loads((DATA_DIR / "molecules.json").read_text())
    assays = json.loads((DATA_DIR / "assays.json").read_text())
    activities = json.loads((DATA_DIR / "activities.json").read_text())

    driver = get_driver()
    try:
        ensure_db(driver, args.reset)
        load_targets(driver, target)
        load_molecules(driver, molecules)
        load_assays(driver, assays)
        load_activities(driver, activities)
    finally:
        driver.close()

    print(json.dumps({"success": True, "staging_db": STAGING_DB}))


if __name__ == "__main__":
    main()
