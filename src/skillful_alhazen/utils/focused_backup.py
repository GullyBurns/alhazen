"""
Focused, portable backup of a namespaced subgraph (TypeDB) + its Qdrant vectors.

Produces ONE restorable zip per target by composing two mechanisms that already
exist in the repo:

  * TypeDB slice  -- a temp DB is created with the SOURCE schema, then
    ``subgraph_migrator.copy`` copies the scoped subgraph into it (id-preserving,
    scoped by type-label prefix + shared-ref allowlist), and the temp DB is
    exported (native ``db.export_to_file`` -> schema.typeql + data.typedb) and
    dropped. The export is fully self-contained, so it re-imports standalone.

  * Qdrant vectors -- native per-collection snapshots (POST .../snapshots), each
    downloaded over REST. Snapshots restore via PUT .../snapshots/upload.

Bundle layout inside the zip::

    <slug>/
      MANIFEST.json                 # sources, scope, counts, restore steps
      typedb/<db>_schema.typeql
      typedb/<db>_data.typedb
      qdrant/<collection>.snapshot  # one per collection

Presets (see TARGETS):
  career-kg      alh_personal  career-/jhunt-  + career/jobhunt Qdrant collections
  deep-research  alh_deep_research  scilit-/kefed-/ooevv-/trec-  + alhazen_papers

Usage::

    uv run python -m skillful_alhazen.utils.focused_backup list
    uv run python -m skillful_alhazen.utils.focused_backup backup --target career-kg [--dry-run]
    uv run python -m skillful_alhazen.utils.focused_backup backup --target deep-research
    uv run python -m skillful_alhazen.utils.focused_backup backup --all
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Any

from skillful_alhazen.utils import subgraph_migrator as sm

TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Shared reference data replicated into every per-repo DB. Carried in every slice
# so classification/tagging/vocabulary relations resolve on restore into a fresh
# instance. id-preserving copy is idempotent: skipped if the id already exists.
SHARED_REFS = ["alh-vocabulary", "alh-vocabulary-type", "alh-tag"]

# Cache capture rules. Each rule pulls content out of ~/.alhazen/cache/<dir>
# whose name is derived from an in-slice entity id, for every slice id starting
# with `id_prefix`. This keeps the extracted document content (paper full text,
# text artifacts) travelling WITH the graph that references it, scoped to exactly
# the ids in the bundle -- no unrelated files. Two shapes:
#   kind="dir":  ~/.alhazen/cache/<dir>/<id>/...    whole per-id subtree (fulltext PDFs)
#   kind="file": ~/.alhazen/cache/<dir>/<id><ext>   one file per id (text artifacts)

TARGETS: dict[str, dict[str, Any]] = {
    "career-kg": {
        "description": "Career knowledge graph (career-* live graph + legacy jhunt-*) "
                       "and its Qdrant collections.",
        "typedb": {
            "source": "alh_personal",
            "prefixes": ["career-", "jhunt-"],
            "also_types": ["alh-person"] + SHARED_REFS,
        },
        "qdrant": ["career-opportunities", "jobhunt-candidates", "jobhunt-opportunities"],
        "cache": [],
    },
    "deep-research": {
        "description": "Scientific-literature + tech-recon subgraph (scilit-/kefed-/ooevv-/trec-) "
                       "and the alhazen_papers vector collection. NOTE: trec-* is empty until "
                       "tech-recon is curated; it is scoped here so future data is captured.",
        "typedb": {
            "source": "alh_deep_research",
            "prefixes": ["scilit-", "kefed-", "ooevv-", "trec-"],
            # Artifact nodes (scilit-pdf-fulltext, scilit-citation-record, kefed-model,
            # ooevv-element-set, ...) are concrete subtypes of alh-artifact and are
            # already captured by the prefixes above, so their alh-representation /
            # alh-fragmentation relations resolve without extra also_types.
            "also_types": list(SHARED_REFS),
        },
        "qdrant": ["alhazen_papers"],
        # Cache content that is REFERENCED by the graph and not already inline:
        #   fulltext/<scilit-paper-id>/  the downloaded PDF + extracted fulltext text,
        #                               one subdir per paper (papers are in scope).
        # NOTE: section/observation/sentence text lives inline in TypeDB attributes
        # (travels in data.typedb), and ~/.alhazen/cache/text/artifact-*.txt is a
        # stale older-pipeline cache disjoint from the current graph -- so it is NOT
        # captured (id-scoping it yields 0 for this DB).
        "cache": [
            {"dir": "fulltext", "id_prefix": "scilit-paper-", "kind": "dir"},
        ],
    },
}


def _cache_dir() -> Path:
    env = os.getenv("ALHAZEN_CACHE_DIR")
    base = Path(env).expanduser() if env else Path.home() / ".alhazen" / "cache"
    return base


def _qdrant(path: str, method: str = "GET", raw: bool = False):
    url = f"http://{QDRANT_HOST}:{QDRANT_PORT}{path}"
    req = urllib.request.Request(url, method=method)
    resp = urllib.request.urlopen(req)
    if raw:
        return resp
    return json.load(resp)


def _snapshot_collection(collection: str, out_dir: Path) -> dict[str, Any]:
    """Create a snapshot of a whole collection, download it, delete server copy."""
    info = _qdrant(f"/collections/{collection}")["result"]
    points = info.get("points_count")
    created = _qdrant(f"/collections/{collection}/snapshots", method="POST")
    snap_name = created["result"]["name"]
    dest = out_dir / f"{collection}.snapshot"
    with _qdrant(f"/collections/{collection}/snapshots/{snap_name}", raw=True) as r, \
            open(dest, "wb") as f:
        shutil.copyfileobj(r, f)
    # free the server-side copy (lives in the qdrant volume otherwise)
    try:
        _qdrant(f"/collections/{collection}/snapshots/{snap_name}", method="DELETE")
    except Exception:
        pass
    return {"collection": collection, "points": points,
            "file": dest.name, "size": dest.stat().st_size,
            "server_snapshot_name": snap_name}


def _all_ids(driver, db: str) -> set[str]:
    """Every entity id present in `db` (relations carry no id @key)."""
    from typedb.driver import TransactionType

    ids: set[str] = set()
    with driver.transaction(db, TransactionType.READ) as tx:
        for r in tx.query("match $e has id $id;").resolve():
            ids.add(r.get("id").try_get_string())
    return ids


def _typedb_slice(source: str, prefixes: list[str], also_types: list[str],
                  out_dir: Path, dry_run: bool) -> tuple[dict[str, Any], set[str]]:
    """Copy the scoped subgraph into a temp DB, export it, drop the temp DB.

    Returns (result_dict, slice_ids) -- slice_ids is the exact set of entity ids
    in the slice (empty on dry-run, since nothing is materialised), used to scope
    cache-file capture.
    """
    from typedb.driver import TransactionType

    temp_db = f"bkp_slice_{source}"
    driver = sm.get_driver()
    try:
        schema_text = driver.databases.get(source).schema()
        if driver.databases.contains(temp_db):
            driver.databases.get(temp_db).delete()
        if dry_run:
            # still run the migrator dry-run to report counts, against a throwaway
            # schema-only temp DB (relations need the target schema to be checked)
            driver.databases.create(temp_db)
            with driver.transaction(temp_db, TransactionType.SCHEMA) as tx:
                tx.query(schema_text).resolve()
                tx.commit()
            report = sm.copy(source, temp_db, prefixes, set(),
                             dry_run=True, also_types=also_types)
            driver.databases.get(temp_db).delete()
            return {"dry_run": True, "report": report}, set()

        driver.databases.create(temp_db)
        with driver.transaction(temp_db, TransactionType.SCHEMA) as tx:
            tx.query(schema_text).resolve()
            tx.commit()

        report = sm.copy(source, temp_db, prefixes, set(),
                         dry_run=False, also_types=also_types)

        slice_ids = _all_ids(driver, temp_db)

        schema_path = out_dir / f"{source}_schema.typeql"
        data_path = out_dir / f"{source}_data.typedb"
        driver.databases.get(temp_db).export_to_file(str(schema_path), str(data_path))
        result = {
            "dry_run": False,
            "report": report,
            "schema_file": schema_path.name,
            "data_file": data_path.name,
            "schema_size": schema_path.stat().st_size,
            "data_size": data_path.stat().st_size,
        }
        driver.databases.get(temp_db).delete()
        return result, slice_ids
    finally:
        driver.close()


def _collect_cache_files(slice_ids: set[str], cache_rules: list[dict[str, Any]],
                         out_dir: Path, dry_run: bool) -> list[dict[str, Any]]:
    """Copy cache files whose name derives from an in-slice id into out_dir/<dir>/.

    For each rule, a file is captured when `f"{id}{ext}"` exists under
    ~/.alhazen/cache/<dir> for some slice id starting with `id_prefix`. On dry-run
    nothing is copied and slice_ids is empty, so we instead report how many files
    in the source dir match the prefix (an upper bound on what a real run captures).
    """
    def _tree_bytes(p: Path) -> int:
        return sum(f.stat().st_size for f in p.rglob("*") if f.is_file())

    cache_root = _cache_dir()
    results: list[dict[str, Any]] = []
    for rule in cache_rules:
        d, id_prefix = rule["dir"], rule["id_prefix"]
        kind, ext = rule.get("kind", "file"), rule.get("ext", "")
        src_dir = cache_root / d

        if dry_run:
            available = 0
            if src_dir.is_dir():
                available = sum(
                    1 for f in src_dir.iterdir()
                    if f.name.startswith(id_prefix)
                    and (f.is_dir() if kind == "dir" else (f.is_file() and f.name.endswith(ext)))
                )
            results.append({"dir": d, "kind": kind, "dry_run": True,
                            "available_in_source": available, "id_prefix": id_prefix})
            continue

        dest_dir = out_dir / d
        ids = [i for i in slice_ids if i.startswith(id_prefix)]
        copied, total_bytes, missing = 0, 0, 0
        for i in ids:
            if kind == "dir":
                src = src_dir / i
                if not src.is_dir():
                    missing += 1
                    continue
                shutil.copytree(src, dest_dir / i, dirs_exist_ok=True)
                total_bytes += _tree_bytes(src)
            else:
                src = src_dir / f"{i}{ext}"
                if not src.is_file():
                    missing += 1
                    continue
                dest_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest_dir / f"{i}{ext}")
                total_bytes += src.stat().st_size
            copied += 1
        results.append({"dir": d, "kind": kind, "id_prefix": id_prefix,
                        "candidates": len(ids), "copied": copied,
                        "missing": missing, "bytes": total_bytes})
    return results


def _restore_instructions(slug: str, source_db: str, collections: list[str],
                          cache_dirs: list[str]) -> dict[str, Any]:
    out = {
        "typedb": (
            "Import the slice into a NEW database (creates it from the bundled "
            "schema+data; id-preserving so it can also be merged into an existing "
            "instance that already holds the shared reference data):\n"
            f"  unzip {slug}_<ts>.zip\n"
            f"  uv run python skills/typedb-notebook/typedb_notebook.py import-db "
            f"--zip <the zip> --database {source_db}_restored"
        ),
        "qdrant": [
            f"curl -X POST 'http://localhost:6333/collections/{c}/snapshots/upload?priority=snapshot' "
            f"-H 'Content-Type:multipart/form-data' -F 'snapshot=@{slug}/qdrant/{c}.snapshot'"
            for c in collections
        ],
    }
    if cache_dirs:
        out["cache"] = (
            "Copy the bundled document content back into the file cache "
            "(restore does this automatically; manual equivalent):\n"
            f"  cp -rn {slug}/cache/* ~/.alhazen/cache/    # dirs: {', '.join(cache_dirs)}"
        )
    return out


def backup_target(slug: str, dry_run: bool, include_cache: bool = False) -> dict[str, Any]:
    if slug not in TARGETS:
        raise SystemExit(f"Unknown target '{slug}'. Known: {', '.join(TARGETS)}")
    spec = TARGETS[slug]
    td = spec["typedb"]
    cache_rules = spec.get("cache", []) if include_cache else []
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    staging = _cache_dir() / "backups" / f"{slug}_{ts}"
    (staging / "typedb").mkdir(parents=True, exist_ok=True)
    (staging / "qdrant").mkdir(parents=True, exist_ok=True)

    print(f"[{slug}] TypeDB slice from '{td['source']}' "
          f"(prefixes={td['prefixes']}, shared={td['also_types']})...", file=sys.stderr)
    typedb_res, slice_ids = _typedb_slice(td["source"], td["prefixes"], td["also_types"],
                                          staging / "typedb", dry_run)

    qdrant_res: list[dict[str, Any]] = []
    if dry_run:
        for c in spec["qdrant"]:
            try:
                info = _qdrant(f"/collections/{c}")["result"]
                qdrant_res.append({"collection": c, "points": info.get("points_count"),
                                   "dry_run": True})
            except Exception as e:
                qdrant_res.append({"collection": c, "error": str(e)})
    else:
        for c in spec["qdrant"]:
            print(f"[{slug}] Qdrant snapshot '{c}'...", file=sys.stderr)
            qdrant_res.append(_snapshot_collection(c, staging / "qdrant"))

    cache_res: list[dict[str, Any]] = []
    if cache_rules:
        print(f"[{slug}] cache files (dirs={[r['dir'] for r in cache_rules]})...", file=sys.stderr)
        cache_res = _collect_cache_files(slice_ids, cache_rules, staging / "cache", dry_run)

    manifest = {
        "slug": slug,
        "description": spec["description"],
        "created_at": ts,
        "typedb": {
            "source_db": td["source"],
            "prefixes": td["prefixes"],
            "shared_refs": td["also_types"],
            **typedb_res,
        },
        "qdrant": qdrant_res,
        "cache": cache_res,
        "restore": _restore_instructions(slug, td["source"], spec["qdrant"],
                                         [r["dir"] for r in cache_rules]),
    }
    (staging / "MANIFEST.json").write_text(json.dumps(manifest, indent=2))

    if dry_run:
        shutil.rmtree(staging)
        return {"dry_run": True, "target": slug, "manifest": manifest}

    zip_path = staging.parent / f"{slug}_{ts}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fp in staging.rglob("*"):
            if fp.is_file():
                zf.write(fp, f"{slug}/{fp.relative_to(staging)}")
    shutil.rmtree(staging)

    return {
        "dry_run": False,
        "target": slug,
        "zip_path": str(zip_path),
        "zip_size": zip_path.stat().st_size,
        "manifest": manifest,
    }


# ---------------------------------------------------------------------------
# Restore -- load a bundle into THIS instance (point TYPEDB_HOST / QDRANT_HOST
# at the destination to load elsewhere). Modes:
#   fresh    (default) create the DB / collection; refuse if it already exists
#   merge    additive, id-preserving: import into a temp then copy into target
#   replace  DESTRUCTIVE: drop the DB / collection first, then load (needs --yes)
# ---------------------------------------------------------------------------

def _qdrant_multipart_upload(collection: str, snapshot_path: Path) -> dict[str, Any]:
    """Stream a snapshot file to the destination Qdrant, recovering the collection."""
    import uuid as _uuid
    boundary = "----alhazen" + _uuid.uuid4().hex
    payload = snapshot_path.read_bytes()
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="snapshot"; filename="{snapshot_path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + payload + f"\r\n--{boundary}--\r\n".encode()
    url = (f"http://{QDRANT_HOST}:{QDRANT_PORT}/collections/{collection}"
           f"/snapshots/upload?priority=snapshot")
    req = urllib.request.Request(url, data=body, method="POST",
                                 headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    return json.load(urllib.request.urlopen(req))


def _collection_exists(collection: str) -> bool:
    try:
        _qdrant(f"/collections/{collection}")
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def _typedb_restore(schema_path: Path, data_path: Path, source_db: str,
                    target_db: str, prefixes: list[str], also_types: list[str],
                    mode: str, yes: bool) -> dict[str, Any]:
    from typedb.driver import TransactionType

    driver = sm.get_driver()
    try:
        exists = driver.databases.contains(target_db)
        schema_text = schema_path.read_text()
        if mode == "fresh":
            if exists:
                raise SystemExit(
                    f"TypeDB database '{target_db}' already exists. Use --mode merge "
                    f"(additive) or --mode replace --yes (destructive).")
            driver.databases.import_from_file(target_db, schema_text, str(data_path))
            return {"mode": "fresh", "target_db": target_db, "created": True}
        if mode == "replace":
            if exists and not yes:
                raise SystemExit(f"--mode replace drops '{target_db}'. Re-run with --yes to confirm.")
            if exists:
                driver.databases.get(target_db).delete()
            driver.databases.import_from_file(target_db, schema_text, str(data_path))
            return {"mode": "replace", "target_db": target_db, "recreated": True}
        if mode == "merge":
            if not exists:
                # nothing to merge into: same as fresh
                driver.databases.import_from_file(target_db, schema_text, str(data_path))
                return {"mode": "merge", "target_db": target_db, "created": True}
            temp_db = f"bkp_restore_{source_db}"
            if driver.databases.contains(temp_db):
                driver.databases.get(temp_db).delete()
            driver.databases.import_from_file(temp_db, schema_text, str(data_path))
            report = sm.copy(temp_db, target_db, prefixes, set(),
                             dry_run=False, also_types=also_types)
            driver.databases.get(temp_db).delete()
            return {"mode": "merge", "target_db": target_db, "copy_report": report}
        raise SystemExit(f"Unknown mode '{mode}'")
    finally:
        driver.close()


def restore_bundle(zip_path: str, target_db: str | None, mode: str,
                   typedb_only: bool, qdrant_only: bool, yes: bool,
                   dry_run: bool) -> dict[str, Any]:
    zp = Path(zip_path).expanduser()
    if not zp.exists():
        raise SystemExit(f"Bundle not found: {zp}")
    staging = Path(_cache_dir()) / "restore" / zp.stem
    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zp) as zf:
        zf.extractall(staging)
    manifest = json.loads(next(staging.rglob("MANIFEST.json")).read_text())
    td = manifest["typedb"]
    source_db = td["source_db"]
    dest_db = target_db or source_db

    result: dict[str, Any] = {"bundle": str(zp), "slug": manifest.get("slug"),
                              "mode": mode, "dry_run": dry_run}

    if dry_run:
        result["typedb"] = {"would_load_into": dest_db,
                            "source_db": source_db,
                            "qdrant_host": f"{QDRANT_HOST}:{QDRANT_PORT}",
                            "typedb_host": f"{TYPEDB_HOST}:{TYPEDB_PORT}"}
        result["qdrant"] = [{"collection": q["collection"], "points": q.get("points")}
                            for q in manifest["qdrant"]]
        shutil.rmtree(staging)
        return result

    if not qdrant_only:
        schema_path = next(staging.rglob("*_schema.typeql"))
        data_path = next(staging.rglob("*_data.typedb"))
        print(f"[restore] TypeDB '{dest_db}' (mode={mode})...", file=sys.stderr)
        result["typedb"] = _typedb_restore(
            schema_path, data_path, source_db, dest_db,
            td.get("prefixes", []), td.get("shared_refs", []), mode, yes)

    if not typedb_only and not qdrant_only:
        # Restore bundled document content into the local file cache (additive,
        # never overwrites an existing file). Cache is a third dimension alongside
        # TypeDB/Qdrant, so it rides along on a full restore only.
        cache_src = next((p for p in staging.rglob("cache") if p.is_dir()), None)
        if cache_src:
            cache_root = _cache_dir()
            restored, skipped = 0, 0
            for f in cache_src.rglob("*"):
                if not f.is_file():
                    continue
                rel = f.relative_to(cache_src)
                dest = cache_root / rel
                if dest.exists():
                    skipped += 1
                    continue
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(f, dest)
                restored += 1
            print(f"[restore] cache -> {cache_root} ({restored} new, {skipped} kept)...",
                  file=sys.stderr)
            result["cache"] = {"root": str(cache_root), "restored": restored, "skipped": skipped}

    if not typedb_only:
        qres = []
        for snap in sorted((staging).rglob("qdrant/*.snapshot")):
            coll = snap.stem
            exists = _collection_exists(coll)
            if exists and mode == "fresh":
                raise SystemExit(
                    f"Qdrant collection '{coll}' already exists. Use --mode replace --yes "
                    f"to overwrite (Qdrant snapshot recovery replaces the whole collection).")
            if exists and mode == "merge":
                raise SystemExit(
                    f"Qdrant collection '{coll}' already exists; snapshot recovery cannot "
                    f"merge point-wise. Use --mode replace --yes, or restore into a fresh "
                    f"Qdrant instance.")
            if exists and mode == "replace":
                if not yes:
                    raise SystemExit(f"--mode replace overwrites Qdrant '{coll}'. Re-run with --yes.")
                _qdrant(f"/collections/{coll}", method="DELETE")
            print(f"[restore] Qdrant snapshot -> '{coll}'...", file=sys.stderr)
            up = _qdrant_multipart_upload(coll, snap)
            qres.append({"collection": coll, "result": up.get("status")})
        result["qdrant"] = qres

    shutil.rmtree(staging)
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list backup presets")
    bp = sub.add_parser("backup", help="create a focused backup bundle")
    bp.add_argument("--target", help=f"one of: {', '.join(TARGETS)}")
    bp.add_argument("--all", action="store_true", help="back up every preset")
    bp.add_argument("--dry-run", action="store_true",
                    help="report scope + counts without writing a zip")
    bp.add_argument("--include-cache", action="store_true",
                    help="also bundle cached document content (fulltext/, text/) scoped "
                         "to the slice's ids -- makes bundles much larger")

    rp = sub.add_parser("restore", help="load a bundle into TYPEDB_HOST/QDRANT_HOST")
    rp.add_argument("--zip", required=True, help="path to a bundle zip")
    rp.add_argument("--target-db", help="destination TypeDB DB (default: bundle's source DB)")
    rp.add_argument("--mode", choices=["fresh", "merge", "replace"], default="fresh",
                    help="fresh=create (refuse if exists); merge=id-preserving additive; "
                         "replace=drop first (destructive)")
    rp.add_argument("--typedb-only", action="store_true")
    rp.add_argument("--qdrant-only", action="store_true")
    rp.add_argument("--yes", action="store_true", help="confirm destructive --mode replace")
    rp.add_argument("--dry-run", action="store_true", help="show what would load, change nothing")
    args = ap.parse_args()

    if args.cmd == "list":
        for slug, spec in TARGETS.items():
            print(f"{slug}\n  {spec['description']}\n  typedb: {spec['typedb']['source']} "
                  f"{spec['typedb']['prefixes']}\n  qdrant: {spec['qdrant']}\n")
        return

    if args.cmd == "restore":
        out = restore_bundle(args.zip, args.target_db, args.mode,
                             args.typedb_only, args.qdrant_only, args.yes, args.dry_run)
        print(json.dumps(out, indent=2))
        return

    targets = list(TARGETS) if args.all else ([args.target] if args.target else [])
    if not targets:
        raise SystemExit("Specify --target <slug> or --all")

    out = [backup_target(t, args.dry_run, args.include_cache) for t in targets]
    print(json.dumps(out if len(out) > 1 else out[0], indent=2))


if __name__ == "__main__":
    main()
