#!/usr/bin/env python3
"""
Fetch ChEMBL data for a target and save as staged JSON files.

This downloads real open data from the ChEMBL REST API (CC-BY-SA 3.0)
and writes it as JSON files that the GLAV mapper can source from.

Usage:
    python fetch_data.py --target CHEMBL203 --limit 500
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import requests

CHEMBL_API = "https://www.ebi.ac.uk/chembl/api/data"
DATA_DIR = Path(__file__).parent / "data"


def fetch_paginated(url: str, params: dict, limit: int = 500) -> list:
    """Fetch paginated results from ChEMBL API."""
    results = []
    params = {**params, "limit": min(limit, 1000), "offset": 0, "format": "json"}

    while len(results) < limit:
        resp = requests.get(url, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()

        page_key = [k for k in data.keys() if k not in ("page_meta",)][0]
        batch = data[page_key]
        results.extend(batch)

        if not data["page_meta"].get("next") or len(results) >= limit:
            break

        params["offset"] += params["limit"]
        time.sleep(0.3)  # Rate limit courtesy

    return results[:limit]


def fetch_target(target_id: str) -> dict:
    """Fetch target details."""
    resp = requests.get(f"{CHEMBL_API}/target/{target_id}.json", timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_activities(target_id: str, limit: int = 500) -> list:
    """Fetch IC50 bioactivities with pChEMBL values for a target."""
    return fetch_paginated(
        f"{CHEMBL_API}/activity.json",
        {
            "target_chembl_id": target_id,
            "standard_type": "IC50",
            "pchembl_value__isnull": "false",
        },
        limit=limit,
    )


def fetch_molecules(chembl_ids: list[str]) -> list:
    """Fetch molecule details for a list of ChEMBL IDs."""
    molecules = []
    # Batch in groups of 50
    for i in range(0, len(chembl_ids), 50):
        batch = chembl_ids[i:i + 50]
        ids_param = ";".join(batch)
        resp = requests.get(
            f"{CHEMBL_API}/molecule/set/{ids_param}.json",
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            molecules.extend(data.get("molecules", []))
        time.sleep(0.3)
    return molecules


def fetch_assays(chembl_ids: list[str]) -> list:
    """Fetch assay details for a list of ChEMBL IDs."""
    assays = []
    for i in range(0, len(chembl_ids), 50):
        batch = chembl_ids[i:i + 50]
        ids_param = ";".join(batch)
        resp = requests.get(
            f"{CHEMBL_API}/assay/set/{ids_param}.json",
            timeout=60,
        )
        if resp.status_code == 200:
            data = resp.json()
            assays.extend(data.get("assays", []))
        time.sleep(0.3)
    return assays


def main():
    parser = argparse.ArgumentParser(description="Fetch ChEMBL data for demo")
    parser.add_argument("--target", default="CHEMBL203", help="Target ChEMBL ID (default: EGFR)")
    parser.add_argument("--limit", type=int, default=500, help="Max bioactivities to fetch")
    args = parser.parse_args()

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Fetching target {args.target}...")
    target = fetch_target(args.target)
    (DATA_DIR / "target.json").write_text(json.dumps(target, indent=2))
    print(f"  Target: {target['pref_name']} ({target['organism']})")

    print(f"Fetching up to {args.limit} IC50 bioactivities...")
    activities = fetch_activities(args.target, limit=args.limit)
    (DATA_DIR / "activities.json").write_text(json.dumps(activities, indent=2))
    print(f"  Got {len(activities)} activities")

    # Extract unique molecule and assay IDs
    mol_ids = list(set(a["molecule_chembl_id"] for a in activities if a.get("molecule_chembl_id")))
    assay_ids = list(set(a["assay_chembl_id"] for a in activities if a.get("assay_chembl_id")))
    print(f"  Unique compounds: {len(mol_ids)}, unique assays: {len(assay_ids)}")

    print("Fetching molecule details...")
    molecules = fetch_molecules(mol_ids)
    (DATA_DIR / "molecules.json").write_text(json.dumps(molecules, indent=2))
    print(f"  Got {len(molecules)} molecules")

    print("Fetching assay details...")
    assays = fetch_assays(assay_ids)
    (DATA_DIR / "assays.json").write_text(json.dumps(assays, indent=2))
    print(f"  Got {len(assays)} assays")

    # Summary
    summary = {
        "target": args.target,
        "target_name": target["pref_name"],
        "organism": target["organism"],
        "activities_count": len(activities),
        "molecules_count": len(molecules),
        "assays_count": len(assays),
        "data_source": "ChEMBL",
        "license": "CC-BY-SA 3.0",
        "api_url": CHEMBL_API,
    }
    (DATA_DIR / "summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nData saved to {DATA_DIR}/")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
