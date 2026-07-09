#!/usr/bin/env python3
"""
Fetch Reactome pathways for a gene (by UniProt accession) and save as JSON.

Real open data from the Reactome ContentService (CC-BY 4.0, no auth). This is
the SECOND domain (systems biology) that the bridge schema connects to the
chemistry domain (ChEMBL bioactivities).

Usage:
    python fetch_pathways.py --uniprot P00533 --gene EGFR --ncbi 1956
"""

import argparse
import json
from pathlib import Path

import requests

REACTOME_API = "https://reactome.org/ContentService"
DATA_DIR = Path(__file__).parent / "data"


def fetch_pathways(uniprot: str, species_taxon: str = "9606") -> list:
    """Return Reactome pathways that the given UniProt accession maps to."""
    resp = requests.get(
        f"{REACTOME_API}/data/mapping/UniProt/{uniprot}/pathways",
        params={"species": species_taxon},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def main():
    parser = argparse.ArgumentParser(description="Fetch Reactome pathways for a gene")
    parser.add_argument("--uniprot", default="P00533", help="UniProt accession (default: EGFR)")
    parser.add_argument("--gene", default="EGFR", help="HGNC gene symbol")
    parser.add_argument("--ncbi", default="1956", help="NCBI Gene ID")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching Reactome pathways for {args.gene} ({args.uniprot})...")
    pathways = fetch_pathways(args.uniprot)
    print(f"  Got {len(pathways)} pathways")

    # Normalize pathway records and tag each with the gene it came from
    norm = []
    for p in pathways:
        species = ""
        sp = p.get("species")
        if isinstance(sp, list) and sp:
            species = sp[0].get("displayName", "")
        elif isinstance(sp, dict):
            species = sp.get("displayName", "")
        norm.append({
            "pathway_id": p.get("stId", ""),
            "name": p.get("displayName", ""),
            "source": "Reactome",
            "species": species,
            "gene_ref": args.gene,
        })
    (DATA_DIR / "pathways.json").write_text(json.dumps(norm, indent=2))

    gene = {
        "hgnc_symbol": args.gene,
        "ncbi_gene_id": args.ncbi,
        "uniprot_id": args.uniprot,
    }
    (DATA_DIR / "gene.json").write_text(json.dumps(gene, indent=2))

    summary = {
        "gene": args.gene,
        "uniprot": args.uniprot,
        "ncbi_gene_id": args.ncbi,
        "pathways_count": len(norm),
        "data_source": "Reactome ContentService",
        "license": "CC-BY 4.0",
        "api_url": REACTOME_API,
    }
    (DATA_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"Saved to {DATA_DIR}/")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
