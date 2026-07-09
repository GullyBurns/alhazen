#!/usr/bin/env python3
"""
Load raw gene + Reactome pathway JSON into the chembl_staging database.

Additive to the ChEMBL staging load -- adds raw-gene and raw-pathway rows so
the bridge GLAV rules have a source to read from. Run after the ChEMBL
staging load (which creates the database and the shared attributes).

Usage:
    python load_staging.py
"""

import json
import os
from pathlib import Path

from typedb.driver import TypeDB, Credentials, DriverOptions, TransactionType

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
STAGING_DB = os.getenv("CHEMBL_STAGING_DB", "chembl_staging")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")

DATA_DIR = Path(__file__).parent / "data"
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


def main():
    gene = json.loads((DATA_DIR / "gene.json").read_text())
    pathways = json.loads((DATA_DIR / "pathways.json").read_text())

    driver = get_driver()
    try:
        # Load bridge staging schema additively
        with driver.transaction(STAGING_DB, TransactionType.SCHEMA) as tx:
            tx.query(SCHEMA_FILE.read_text()).resolve()
            tx.commit()
        print("Bridge staging schema loaded")

        with driver.transaction(STAGING_DB, TransactionType.WRITE) as tx:
            tx.query(f'''insert $g isa raw-gene,
                has hgnc-symbol "{escape(gene["hgnc_symbol"])}",
                has ncbi-gene-id "{escape(gene["ncbi_gene_id"])}",
                has uniprot-id "{escape(gene["uniprot_id"])}";''').resolve()
            tx.commit()
        print("Genes: 1")

        count = 0
        with driver.transaction(STAGING_DB, TransactionType.WRITE) as tx:
            for p in pathways:
                tx.query(f'''insert $p isa raw-pathway,
                    has pathway-id "{escape(p["pathway_id"])}",
                    has pref-name "{escape(p["name"])}",
                    has pathway-source "{escape(p["source"])}",
                    has pathway-species "{escape(p["species"])}",
                    has gene-ref "{escape(p["gene_ref"])}";''').resolve()
                count += 1
            tx.commit()
        print(f"Pathways: {count}")
    finally:
        driver.close()

    print(json.dumps({"success": True, "staging_db": STAGING_DB}))


if __name__ == "__main__":
    main()
