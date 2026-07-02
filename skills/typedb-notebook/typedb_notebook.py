#!/usr/bin/env python3
"""
TypeDB Notebook CLI - Command-line interface for Alhazen's Notebook knowledge graph.

Usage:
    python scripts/typedb_notebook.py <command> [options]

Commands:
    insert-collection   Create a new collection
    insert-note         Create a note about an entity
    query-collection    Get collection info and members
    query-notes         Find notes about an entity
    tag                 Tag an entity
    search-tag          Search entities by tag

Examples:
    # Create a collection
    python scripts/typedb_notebook.py insert-collection --name "CRISPR Papers" --description "Papers about CRISPR"

    # Add a note about a paper
    python scripts/typedb_notebook.py insert-note --subject paper-abc123 --content "Key finding: 95% efficiency"

    # Query notes about an entity
    python scripts/typedb_notebook.py query-notes --subject paper-abc123

Environment:
    TYPEDB_HOST     TypeDB server host (default: localhost)
    TYPEDB_PORT     TypeDB server port (default: 1729)
    TYPEDB_DATABASE Database name (default: alhazen_notebook)
"""

import argparse
import json
import os
import re
import shutil
import sys
import zipfile
from datetime import datetime
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

try:
    from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB

    TYPEDB_AVAILABLE = True
except ImportError:
    TYPEDB_AVAILABLE = False
    print(
        "Warning: typedb-driver not installed. Install with: pip install 'typedb-driver>=3.8.0'",
        file=sys.stderr,
    )

try:
    from skillful_alhazen.utils.skill_helpers import escape_string, generate_id, get_timestamp
except ImportError:
    # Fallback if package not installed (e.g., running outside uv)
    import uuid
    from datetime import timezone

    def escape_string(s: str) -> str:
        if s is None:
            return ""
        return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")

    def generate_id(prefix: str) -> str:
        return f"{prefix}-{uuid.uuid4().hex[:12]}"

    def get_timestamp() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# Configuration
TYPEDB_HOST = os.getenv("TYPEDB_HOST", "localhost")
TYPEDB_PORT = int(os.getenv("TYPEDB_PORT", "1729"))
TYPEDB_DATABASE = os.getenv("TYPEDB_DATABASE", "alh_core")
TYPEDB_USERNAME = os.getenv("TYPEDB_USERNAME", "admin")
TYPEDB_PASSWORD = os.getenv("TYPEDB_PASSWORD", "password")


def get_driver():
    """Get TypeDB driver connection."""
    return TypeDB.driver(
        f"{TYPEDB_HOST}:{TYPEDB_PORT}",
        Credentials(TYPEDB_USERNAME, TYPEDB_PASSWORD),
        DriverOptions(is_tls_enabled=False),
    )


# ============================================================================
# SCHEMA MODEL - static parse of .tql files (NEVER query the DB for schema)
# ----------------------------------------------------------------------------
# A variable-free schema match (e.g. `match X sub Y;`) panics TypeDB 3.8 and
# restarts the container, so the engine learns the schema by parsing the .tql
# source files listed in skills-registry.yaml `schema_map` (+ the alh-core base).
# The model drives validation (type exists, attr owned, role valid) and value
# formatting (string -> quoted+escaped; integer/double -> bare; boolean ->
# true|false; datetime -> YYYY-MM-DDTHH:MM:SS).
# ============================================================================

SKILL_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.getenv("PROJECT_ROOT") or os.path.abspath(
    os.path.join(SKILL_DIR, "..", "..")
)

_VALUE_TYPES = {"string", "integer", "boolean", "datetime", "double"}


class SchemaModel:
    """Merged, statically-parsed view of every namespace schema + alh-core."""

    def __init__(self):
        # name -> value_type
        self.attributes: dict = {}
        # name -> {"sub": parent|None, "abstract": bool,
        #          "owns": [(attr, is_key, is_multi)], "plays": [(relation, role)]}
        self.entities: dict = {}
        # name -> {"owns": [(attr, is_key, is_multi)], "relates": [role, ...]}
        self.relations: dict = {}

    # -- loading / parsing -----------------------------------------------------

    def load(self, paths):
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8") as f:
                    self._parse(f.read())
            except FileNotFoundError:
                continue
        return self

    def _parse(self, text):
        # strip line comments
        lines = []
        for line in text.splitlines():
            i = line.find("#")
            if i != -1:
                line = line[:i]
            lines.append(line)
        joined = "\n".join(lines)
        joined = re.sub(r"\bdefine\b", " ", joined, count=1)
        for raw in joined.split(";"):
            stmt = " ".join(raw.split())
            if stmt:
                self._parse_statement(stmt)

    @staticmethod
    def _owns_clause(clause):
        toks = clause.split()
        attr = toks[1]
        is_key = "@key" in clause
        is_multi = "@card(0.." in clause.replace(" ", "")
        return attr, is_key, is_multi

    def _parse_statement(self, stmt):
        clauses = [c.strip() for c in stmt.split(",")]
        head = clauses[0].split()
        if len(head) < 2:
            return
        kind = head[0]

        if kind == "attribute":
            name = head[1]
            for c in clauses[1:]:
                toks = c.split()
                if toks and toks[0] == "value" and len(toks) > 1:
                    self.attributes[name] = toks[1]

        elif kind == "entity":
            name = head[1]
            abstract = "@abstract" in head
            sub = None
            if "sub" in head:
                sub = head[head.index("sub") + 1]
            owns, plays = [], []
            for c in clauses[1:]:
                toks = c.split()
                if not toks:
                    continue
                if toks[0] == "sub" and len(toks) > 1:
                    sub = toks[1]
                elif toks[0] == "owns" and len(toks) > 1:
                    owns.append(self._owns_clause(c))
                elif toks[0] == "plays" and len(toks) > 1 and ":" in toks[1]:
                    rel, role = toks[1].split(":", 1)
                    plays.append((rel, role))
            ent = self.entities.setdefault(
                name, {"sub": None, "abstract": False, "owns": [], "plays": []}
            )
            if sub is not None:
                ent["sub"] = sub
            ent["abstract"] = ent["abstract"] or abstract
            ent["owns"].extend(owns)
            ent["plays"].extend(plays)

        elif kind == "relation":
            name = head[1]
            owns, relates = [], []
            for c in clauses[1:]:
                toks = c.split()
                if not toks:
                    continue
                if toks[0] == "owns" and len(toks) > 1:
                    owns.append(self._owns_clause(c))
                elif toks[0] == "relates" and len(toks) > 1:
                    relates.append(toks[1])
            rel = self.relations.setdefault(name, {"owns": [], "relates": []})
            rel["owns"].extend(owns)
            rel["relates"].extend(relates)

    # -- type queries ----------------------------------------------------------

    def type_exists(self, name):
        return name in self.entities or name in self.relations or name in self.attributes

    def is_entity(self, name):
        return name in self.entities

    def is_relation(self, name):
        return name in self.relations

    def is_abstract(self, name):
        return self.entities.get(name, {}).get("abstract", False)

    def supertype_chain(self, name):
        """[name, parent, ..., root] for an entity; [] for non-entities."""
        chain, seen, cur = [], set(), name
        while cur and cur in self.entities and cur not in seen:
            chain.append(cur)
            seen.add(cur)
            cur = self.entities[cur]["sub"]
        return chain

    def owned_attrs(self, name):
        """attr -> {key, multi}, transitive across the supertype chain."""
        result = {}
        if name in self.entities:
            for t in reversed(self.supertype_chain(name)):
                for attr, key, multi in self.entities[t]["owns"]:
                    result[attr] = {"key": key, "multi": multi}
        elif name in self.relations:
            for attr, key, multi in self.relations[name]["owns"]:
                result[attr] = {"key": key, "multi": multi}
        return result

    def owns_attr(self, name, attr):
        return attr in self.owned_attrs(name)

    def is_multi(self, name, attr):
        info = self.owned_attrs(name).get(attr)
        return bool(info and info["multi"])

    def plays_of(self, name):
        """[(relation, role), ...] transitive across the supertype chain."""
        result, seen = [], set()
        for t in self.supertype_chain(name):
            for rel, role in self.entities[t]["plays"]:
                if (rel, role) not in seen:
                    seen.add((rel, role))
                    result.append((rel, role))
        return result

    def relation_roles(self, name):
        return list(self.relations.get(name, {}).get("relates", []))

    def role_valid(self, relation, role):
        return role in self.relation_roles(relation)

    # -- value formatting ------------------------------------------------------

    def attr_value_type(self, attr):
        return self.attributes.get(attr)

    def format_value(self, attr, raw):
        """Render `raw` as a TypeQL literal according to the attribute's value type."""
        vtype = self.attributes.get(attr)
        if vtype is None:
            raise ValueError(
                f"Unknown attribute '{attr}' (not defined in any loaded schema)"
            )
        if vtype == "string":
            return '"' + escape_string(str(raw)) + '"'
        if vtype == "integer":
            return str(int(raw))
        if vtype == "double":
            return repr(float(raw))
        if vtype == "boolean":
            if isinstance(raw, bool):
                return "true" if raw else "false"
            s = str(raw).strip().lower()
            if s in ("true", "1", "yes"):
                return "true"
            if s in ("false", "0", "no"):
                return "false"
            raise ValueError(f"Invalid boolean value '{raw}' for attribute '{attr}'")
        if vtype == "datetime":
            return self._format_datetime(str(raw))
        raise ValueError(f"Unsupported value type '{vtype}' for attribute '{attr}'")

    @staticmethod
    def _format_datetime(s):
        s = s.strip().replace(" ", "T")
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", s):
            s = s + "T00:00:00"
        return s


def _schema_source_paths():
    """alh-core schema + every namespace schema listed in skills-registry.yaml."""
    paths = [os.path.join(PROJECT_ROOT, "skills/alhazen-core/alhazen_notebook.tql")]
    reg = os.path.join(PROJECT_ROOT, "skills-registry.yaml")
    try:
        import yaml

        with open(reg, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        namespaces = ((data.get("schema_map") or {}).get("namespaces")) or {}
        for _ns, info in namespaces.items():
            sp = (info or {}).get("schema")
            if sp:
                paths.append(os.path.join(PROJECT_ROOT, sp))
    except Exception:
        pass
    seen, out = set(), []
    for p in paths:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            out.append(ap)
    return out


_SCHEMA_MODEL = None


def get_schema_model():
    global _SCHEMA_MODEL
    if _SCHEMA_MODEL is None:
        _SCHEMA_MODEL = SchemaModel().load(_schema_source_paths())
    return _SCHEMA_MODEL


# Per-skill probe entity type: a representative type whose presence in a database means
# that skill's dashboard is relevant there. Used by scan-databases for the hub DB switcher.
# (Data query only — never a variable-free schema match, which panics TypeDB 3.8.)
DASHBOARD_PROBES = {
    "agentic-memory": "nbmem-memory-claim-note",
    "scientific-literature": "scilit-paper",
    "tech-recon": "trec-system",
    "dismech-notebook": "dm-disease",
    "coach": "coach-metric-series",
    "jobhunt": "jhunt-position",
}


def scan_databases(args):
    """List every TypeDB database and, per skill, whether its dashboard is available there.
    For each (database, skill) it probes a representative entity type: status is
    'data' (rows exist), 'schema' (type defined, no rows), or 'absent' (type not defined).
    Powers the hub database switcher — selecting a DB reveals the dashboards valid for it."""
    out = []
    with get_driver() as driver:
        names = sorted(db.name for db in driver.databases.all())
        for name in names:
            skills = {}
            for slug, probe in DASHBOARD_PROBES.items():
                status = "absent"
                try:
                    with driver.transaction(name, TransactionType.READ) as tx:
                        rows = list(tx.query(
                            f'match $x isa {probe}; limit 1; select $x;').resolve())
                        status = "data" if rows else "schema"
                except Exception:
                    status = "absent"
                skills[slug] = status
            out.append({"name": name, "skills": skills})
    print(json.dumps({"success": True, "databases": out}, indent=2))


def describe_schema(args):
    """Inspect the parsed schema: a single type's detail, or a global summary."""
    sm = get_schema_model()

    def _attr_rows(name):
        return [
            {
                "name": a,
                "value_type": sm.attr_value_type(a),
                "key": info["key"],
                "multi": info["multi"],
            }
            for a, info in sorted(sm.owned_attrs(name).items())
        ]

    if args.type:
        t = args.type
        if not sm.type_exists(t):
            print(json.dumps({"success": False, "error": f"Unknown type '{t}'"}))
            return
        out = {"success": True, "type": t}
        if sm.is_entity(t):
            out["kind"] = "entity"
            out["abstract"] = sm.is_abstract(t)
            out["supertype_chain"] = sm.supertype_chain(t)
            out["attributes"] = _attr_rows(t)
            out["plays"] = [
                {"relation": r, "role": ro} for (r, ro) in sm.plays_of(t)
            ]
        elif sm.is_relation(t):
            out["kind"] = "relation"
            out["roles"] = sm.relation_roles(t)
            out["attributes"] = _attr_rows(t)
        else:
            out["kind"] = "attribute"
            out["value_type"] = sm.attr_value_type(t)
        print(json.dumps(out, indent=2))
    else:
        print(
            json.dumps(
                {
                    "success": True,
                    "counts": {
                        "entities": len(sm.entities),
                        "relations": len(sm.relations),
                        "attributes": len(sm.attributes),
                    },
                    "entities": sorted(sm.entities.keys()),
                    "relations": sorted(sm.relations.keys()),
                    "attributes": sorted(sm.attributes.keys()),
                },
                indent=2,
            )
        )


# ============================================================================
# GRAPH ENGINE - generic, schema-validated graph CRUD
# ----------------------------------------------------------------------------
# The engine builds every TypeQL write string itself (agents never author raw
# writes). All ops in one `apply` run inside ONE write transaction, committed
# once (atomic). Cross-op `$bindings` let a `create` mint an id that later ops
# reference (reads within a write txn see prior uncommitted writes).
#
# Role-player typing: `link` and `unlink` ops resolve each role player's
# *concrete type* at compile time via a lightweight concept-API read
# (`_concrete_type`). Using the abstract root `alh-identifiable-entity` for
# all role players triggers TypeDB 3.x [INF4] type-inference failures whenever
# a relation role is restricted to a narrower branch of the hierarchy (e.g.
# `alh-representation:alh-artifact` can only be played by `alh-artifact`
# subtypes, not by `alh-domain-thing`). Concrete types satisfy all role
# constraints without requiring the caller to know types upfront.
# In dry-run mode (no live tx) the abstract root is used as a fallback — the
# output shows intent but is not guaranteed to execute as-is.
# ============================================================================


class GraphError(Exception):
    """A validation or execution error for a single op (carries op index)."""


class GraphEngine:
    ROOT = "alh-identifiable-entity"
    _WRITE_KEYWORDS = ("insert", "delete", "define", "undefine", "update", "put")

    def __init__(self):
        self.sm = get_schema_model()
        self.bindings: dict = {}  # name -> concrete id

    # -- helpers ---------------------------------------------------------------

    def _sub(self, val):
        """Resolve a `$binding` reference to its minted id; pass through otherwise."""
        if isinstance(val, str) and val.startswith("$"):
            key = val[1:]
            if key not in self.bindings:
                raise GraphError(f"unresolved binding '{val}'")
            return self.bindings[key]
        return val

    def _idq(self, raw_id):
        return self.sm.format_value("id", raw_id)

    def _validate_owns(self, type_name, attrs):
        owned = self.sm.owned_attrs(type_name)
        for k in attrs:
            if k not in self.sm.attributes:
                raise GraphError(f"unknown attribute '{k}'")
            if k not in owned:
                sample = ", ".join(sorted(owned)[:25])
                raise GraphError(
                    f"type '{type_name}' does not own attribute '{k}'. Owned: {sample}"
                )

    def _concrete_type(self, tx, eid):
        """Resolve the concrete entity type of `eid` via the concept API (safe)."""
        res = tx.query(f'match $e isa {self.ROOT}, has id {self._idq(eid)};').resolve()
        for row in res:
            label = row.get("e").get_type().get_label()
            return label.name if hasattr(label, "name") else str(label)
        raise GraphError(f"no entity found with id '{eid}'")

    # -- pass 1: normalize (resolve $refs, mint ids, static validation) --------

    def _normalize(self, ops):
        norm = []
        for i, op in enumerate(ops):
            try:
                kind = op.get("op")
                if kind in ("create", "upsert"):
                    t = op.get("type")
                    if not t or not self.sm.is_entity(t):
                        raise GraphError(f"'{t}' is not a known entity type")
                    if kind == "create" and self.sm.is_abstract(t):
                        raise GraphError(f"cannot create instance of abstract type '{t}'")
                    attrs = {k: self._sub(v) for k, v in (op.get("attrs") or {}).items()}
                    self._validate_owns(t, attrs)
                    if op.get("id"):
                        eid = self._sub(op["id"])
                    elif kind == "upsert":
                        raise GraphError("upsert requires an explicit id")
                    else:
                        eid = generate_id(t)
                    if op.get("as"):
                        self.bindings[op["as"]] = eid
                    norm.append({**op, "_id": eid, "_attrs": attrs})
                elif kind in ("set-attr", "delete-attr"):
                    eid = self._sub(op.get("id"))
                    if not eid:
                        raise GraphError(f"{kind} requires an id")
                    attrs = {k: self._sub(v) for k, v in (op.get("attrs") or {}).items()}
                    for k in attrs:
                        if k not in self.sm.attributes:
                            raise GraphError(f"unknown attribute '{k}'")
                    if kind == "set-attr" and not attrs:
                        raise GraphError("set-attr requires at least one attr")
                    norm.append({**op, "_id": eid, "_attrs": attrs})
                elif kind in ("link", "unlink"):
                    rel = op.get("relation")
                    if not rel or not self.sm.is_relation(rel):
                        raise GraphError(f"'{rel}' is not a known relation type")
                    roles = {r: self._sub(v) for r, v in (op.get("roles") or {}).items()}
                    if not roles:
                        raise GraphError(f"{kind} requires at least one role")
                    for r in roles:
                        if not self.sm.role_valid(rel, r):
                            valid = ", ".join(self.sm.relation_roles(rel))
                            raise GraphError(
                                f"relation '{rel}' has no role '{r}'. Roles: {valid}"
                            )
                    attrs = {k: self._sub(v) for k, v in (op.get("attrs") or {}).items()}
                    norm.append({**op, "_roles": roles, "_attrs": attrs})
                elif kind == "delete":
                    eid = self._sub(op.get("id"))
                    if not eid:
                        raise GraphError("delete requires an id")
                    norm.append({**op, "_id": eid})
                else:
                    raise GraphError(f"unknown op '{kind}'")
            except GraphError as e:
                raise GraphError(f"op[{i}] ({op.get('op')}): {e}") from None
        return norm

    # -- pass 2: compile a normalized op to TypeQL statement(s) ----------------

    def _compile(self, tx, op):
        kind = op["op"]
        if kind == "create":
            return [self._q_create(op["type"], op["_id"], op["_attrs"])]
        if kind == "upsert":
            exists = tx is not None and self._entity_exists(tx, op["_id"])
            if exists:
                return self._q_set_attr(tx, op["_id"], op["_attrs"],
                                        replace=op.get("replace", False),
                                        ctype_hint=op.get("type"))
            return [self._q_create(op["type"], op["_id"], op["_attrs"])]
        if kind == "set-attr":
            return self._q_set_attr(tx, op["_id"], op["_attrs"],
                                    replace=op.get("replace", False),
                                    ctype_hint=op.get("type"))
        if kind == "delete-attr":
            return self._q_delete_attr(op["_id"], op["_attrs"])
        if kind == "link":
            return self._q_link(tx, op["relation"], op["_roles"], op["_attrs"],
                                idempotent=op.get("idempotent", False))
        if kind == "unlink":
            return self._q_unlink(tx, op["relation"], op["_roles"])
        if kind == "delete":
            return self._q_delete(tx, op["_id"], detach=op.get("detach", False),
                                  ctype_hint=op.get("type"))
        raise GraphError(f"unknown op '{kind}'")

    def _entity_exists(self, tx, eid):
        res = tx.query(f'match $e isa {self.ROOT}, has id {self._idq(eid)};').resolve()
        for _ in res:
            return True
        return False

    def _q_create(self, type_name, eid, attrs):
        attrs = dict(attrs)
        if "created-at" in self.sm.owned_attrs(type_name) and "created-at" not in attrs:
            attrs["created-at"] = get_timestamp()
        parts = [f"has id {self._idq(eid)}"]
        for k, v in attrs.items():
            parts.append(f"has {k} {self.sm.format_value(k, v)}")
        return f"insert $e isa {type_name}, " + ", ".join(parts) + ";"

    def _q_set_attr(self, tx, eid, attrs, replace=False, ctype_hint=None):
        ctype = self._concrete_type(tx, eid) if tx is not None else ctype_hint
        idq = self._idq(eid)
        queries = []
        for k, raw in attrs.items():
            values = raw if isinstance(raw, list) else [raw]
            multi = self.sm.is_multi(ctype, k) if ctype else False
            if not multi and len(values) > 1:
                raise GraphError(
                    f"attribute '{k}' is single-valued on '{ctype}'; got {len(values)} values"
                )
            do_replace = replace or not multi
            if do_replace:
                queries.append(
                    f'match $e isa {self.ROOT}, has id {idq}, has {k} $old; '
                    f'delete has $old of $e;'
                )
            for v in values:
                queries.append(
                    f'match $e isa {self.ROOT}, has id {idq}; '
                    f'insert $e has {k} {self.sm.format_value(k, v)};'
                )
        return queries

    def _q_delete_attr(self, eid, attrs):
        idq = self._idq(eid)
        queries = []
        if not attrs:
            raise GraphError("delete-attr requires at least one attr")
        for k, raw in attrs.items():
            if raw is None or raw == "" or (isinstance(raw, list) and not raw):
                # remove all values of k
                queries.append(
                    f'match $e isa {self.ROOT}, has id {idq}, has {k} $old; '
                    f'delete has $old of $e;'
                )
            else:
                values = raw if isinstance(raw, list) else [raw]
                for v in values:
                    val = self.sm.format_value(k, v)
                    # bind the specific value, then delete that ownership link
                    queries.append(
                        f'match $e isa {self.ROOT}, has id {idq}, has {k} $old; '
                        f'$old == {val}; delete has $old of $e;'
                    )
        return queries

    def _role_match(self, roles, tx=None, relation=None):  # noqa: ARG002
        """Build the match clause and `links` tuple for a link/unlink op.

        Fix for TypeDB 3.x [INF4] type-inference failure: when a live `tx` is
        available, resolve each role player's concrete type via the concept API.
        Using the abstract ROOT causes [INF4] when a role is restricted to a
        narrower branch (e.g. only alh-artifact subtypes may play
        alh-representation:alh-artifact). Dry-run (tx=None) falls back to ROOT.

        The callers use TypeDB 3.x relation-match syntax (`$r isa T, links (…)`)
        instead of the old 2.x `$r (…) isa T` form.  The `links` keyword provides
        unambiguous role context, so role names that coincide with type names
        (e.g. `alh-artifact`) do NOT cause [REP1] in this form.
        """
        match_parts, role_tuple = [], []
        for idx, (role, rid) in enumerate(roles.items()):
            var = f"$p{idx}"
            if tx is not None:
                try:
                    ctype = self._concrete_type(tx, rid)
                except GraphError:
                    # Entity was just created in this transaction and is not yet
                    # visible to _concrete_type (e.g. $binding from a prior create
                    # op in the same apply). Fall back to ROOT.
                    ctype = self.ROOT
            else:
                ctype = self.ROOT
            match_parts.append(f"{var} isa {ctype}, has id {self._idq(rid)}")
            role_tuple.append(f"{role}: {var}")
        return "; ".join(match_parts), "(" + ", ".join(role_tuple) + ")"

    def _q_link(self, tx, relation, roles, attrs, idempotent=False):
        match_clause, tuple_clause = self._role_match(roles, tx, relation=relation)
        attrs = dict(attrs)
        if "created-at" in self.sm.owned_attrs(relation) and "created-at" not in attrs:
            attrs["created-at"] = get_timestamp()
        attr_clause = ""
        if attrs:
            attr_clause = ", " + ", ".join(
                f"has {k} {self.sm.format_value(k, v)}" for k, v in attrs.items()
            )
        insert_q = (
            f"match {match_clause}; "
            f"insert {tuple_clause} isa {relation}{attr_clause};"
        )
        if idempotent and tx is not None:
            # TypeDB 3.x relation-match syntax: $r isa T, links (roles)
            check = f"match {match_clause}; $r isa {relation}, links {tuple_clause};"
            for _ in tx.query(check).resolve():
                return []  # already linked -> no-op
        return [insert_q]

    def _q_unlink(self, tx, relation, roles):
        match_clause, tuple_clause = self._role_match(roles, tx, relation=relation)
        # TypeDB 3.x: `$r isa T, links (roles)` in MATCH; old `$r (roles) isa T` is 2.x
        return [f"match {match_clause}; $r isa {relation}, links {tuple_clause}; delete $r;"]

    def _q_delete(self, tx, eid, detach=False, ctype_hint=None):
        idq = self._idq(eid)
        queries = []
        if detach:
            ctype = self._concrete_type(tx, eid) if tx is not None else ctype_hint
            if ctype:
                for rel, role in self.sm.plays_of(ctype):
                    # TypeDB 3.x: `$r isa T, links (role: $e)` for relation MATCH
                    queries.append(
                        f"match $e isa {self.ROOT}, has id {idq}; "
                        f"$r isa {rel}, links ({role}: $e); delete $r;"
                    )
        queries.append(f"match $e isa {self.ROOT}, has id {idq}; delete $e;")
        return queries

    # -- public entrypoint -----------------------------------------------------

    def run(self, ops, dry_run=False):
        norm = self._normalize(ops)
        if dry_run:
            rendered = []
            for op in norm:
                for q in self._compile(None, op):
                    rendered.append(q)
            return {"success": True, "dry_run": True, "ops": len(norm),
                    "queries": rendered, "bindings": dict(self.bindings)}
        executed = 0
        with get_driver() as driver:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                for op in norm:
                    for q in self._compile(tx, op):
                        tx.query(q).resolve()
                        executed += 1
                tx.commit()
        return {"success": True, "ops": len(norm), "statements": executed,
                "bindings": dict(self.bindings)}


# -- generic verb CLI wrappers (each builds a 1-op apply) ----------------------


def _parse_kv(pairs):
    """['k=v', ...] -> {k: v}. Splits on the first '='."""
    out = {}
    for p in pairs or []:
        if "=" not in p:
            raise ValueError(f"expected key=value, got '{p}'")
        k, v = p.split("=", 1)
        out[k.strip()] = v
    return out


def create_entity(args):
    op = {"op": "upsert" if args.upsert else "create", "type": args.type,
          "attrs": _parse_kv(args.attr), "as": "_new"}
    if args.id:
        op["id"] = args.id
    result = GraphEngine().run([op], dry_run=args.dry_run)
    if result.get("success"):
        result["id"] = result.get("bindings", {}).get("_new")
    print(json.dumps(result))


def set_attr(args):
    op = {"op": "set-attr", "id": args.id, "attrs": _parse_kv(args.attr),
          "replace": args.replace}
    if args.type:
        op["type"] = args.type
    print(json.dumps(GraphEngine().run([op], dry_run=args.dry_run)))


def delete_attr(args):
    attrs = {}
    for p in args.attr or []:
        if "=" in p:
            k, v = p.split("=", 1)
            attrs[k.strip()] = v
        else:
            attrs[p.strip()] = None
    print(json.dumps(GraphEngine().run(
        [{"op": "delete-attr", "id": args.id, "attrs": attrs}], dry_run=args.dry_run)))


def link_entities(args):
    op = {"op": "link", "relation": args.relation, "roles": _parse_kv(args.role),
          "attrs": _parse_kv(args.attr), "idempotent": args.idempotent}
    print(json.dumps(GraphEngine().run([op], dry_run=args.dry_run)))


def unlink_entities(args):
    op = {"op": "unlink", "relation": args.relation, "roles": _parse_kv(args.role)}
    print(json.dumps(GraphEngine().run([op], dry_run=args.dry_run)))


def delete_entity(args):
    op = {"op": "delete", "id": args.id, "detach": args.detach}
    print(json.dumps(GraphEngine().run([op], dry_run=args.dry_run)))


def query_graph(args):
    """Guarded read-only query. Must bind a variable; rejects write keywords."""
    q = args.read
    if "$" not in q:
        print(json.dumps({"success": False,
                          "error": "read query must bind a variable (a bare schema match crashes TypeDB)"}))
        return
    low = q.lower()
    for kw in GraphEngine._WRITE_KEYWORDS:
        if re.search(rf"\b{kw}\b", low):
            print(json.dumps({"success": False,
                              "error": f"write keyword '{kw}' not allowed in read query"}))
            return
    if "fetch" not in low:
        print(json.dumps({"success": False,
                          "error": "read query must contain a `fetch { ... }` clause"}))
        return
    limit = args.limit if args.limit is not None else 1000
    rows = []
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            for i, doc in enumerate(tx.query(q).resolve()):
                if i >= limit:
                    break
                rows.append(doc)
    print(json.dumps({"success": True, "count": len(rows), "rows": rows},
                     indent=2, default=str))


def _load_arg_or_file(value):
    """If `value` starts with '@', read the file; otherwise return as-is."""
    if isinstance(value, str) and value.startswith("@"):
        with open(value[1:], "r", encoding="utf-8") as f:
            return f.read()
    return value


def apply_ops(args):
    """Run an ordered op-list in one atomic write transaction."""
    raw = _load_arg_or_file(args.ops)
    try:
        ops = json.loads(raw)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"invalid JSON ops: {e}"}))
        return
    if not isinstance(ops, list):
        print(json.dumps({"success": False, "error": "ops must be a JSON array"}))
        return
    try:
        result = GraphEngine().run(ops, dry_run=args.dry_run)
    except GraphError as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return
    print(json.dumps(result, indent=2 if args.dry_run else None))


def _find_recipe(name):
    """Resolve a recipe by name from skills/*/recipes/, local_skills/*/recipes/,
    and external skill dirs referenced under local_skills."""
    candidates = []
    for base in ("skills", "local_skills"):
        root = os.path.join(PROJECT_ROOT, base)
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            if os.path.basename(dirpath) == "recipes":
                for fn in filenames:
                    if fn == f"{name}.json":
                        candidates.append(os.path.join(dirpath, fn))
    return candidates


def _substitute_params(template, params):
    """Recursively replace {{key}} placeholders in a JSON structure.

    A string that is exactly '{{key}}' is replaced by the param's raw value
    (preserving type); placeholders embedded in a larger string are replaced
    textually.
    """
    if isinstance(template, dict):
        return {k: _substitute_params(v, params) for k, v in template.items()}
    if isinstance(template, list):
        return [_substitute_params(v, params) for v in template]
    if isinstance(template, str):
        m = re.fullmatch(r"\{\{\s*(\w[\w-]*)\s*\}\}", template)
        if m:
            key = m.group(1)
            if key not in params:
                raise ValueError(f"missing recipe param '{key}'")
            return params[key]

        def repl(match):
            key = match.group(1)
            if key not in params:
                raise ValueError(f"missing recipe param '{key}'")
            return str(params[key])

        return re.sub(r"\{\{\s*(\w[\w-]*)\s*\}\}", repl, template)
    return template


def apply_recipe(args):
    """Load a named recipe, substitute params, run through the apply engine."""
    matches = _find_recipe(args.recipe)
    if not matches:
        print(json.dumps({"success": False,
                          "error": f"recipe '{args.recipe}' not found under skills/*/recipes/"}))
        return
    if len(set(os.path.abspath(m) for m in matches)) > 1:
        print(json.dumps({"success": False,
                          "error": f"recipe '{args.recipe}' is ambiguous: {matches}"}))
        return
    recipe_path = matches[0]
    with open(recipe_path, "r", encoding="utf-8") as f:
        recipe = json.load(f)

    params = _parse_kv(args.param)
    declared = recipe.get("params")
    if declared:
        missing = [p for p in declared if p not in params]
        if missing:
            print(json.dumps({"success": False,
                              "error": f"missing required params: {missing}",
                              "declared_params": declared}))
            return

    ops_template = recipe.get("ops")
    if not isinstance(ops_template, list):
        print(json.dumps({"success": False,
                          "error": "recipe must have an 'ops' array"}))
        return
    try:
        ops = _substitute_params(ops_template, params)
        result = GraphEngine().run(ops, dry_run=args.dry_run)
    except (GraphError, ValueError) as e:
        print(json.dumps({"success": False, "error": str(e)}))
        return
    result["recipe"] = args.recipe
    print(json.dumps(result, indent=2 if args.dry_run else None))


def insert_collection(args):
    """Create a new collection."""
    cid = args.id or generate_id("collection")

    query = f'insert $c isa alh-collection, has id "{cid}", has name "{escape_string(args.name)}"'
    if args.description:
        query += f', has description "{escape_string(args.description)}"'
    if args.query:
        query += f', has alh-logical-query "{escape_string(args.query)}"'
    query += ";"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(query).resolve()
            tx.commit()

    print(json.dumps({"success": True, "collection_id": cid, "name": args.name}))



def insert_note(args):
    """Create a note about an entity."""
    nid = args.id or generate_id("note")

    # Insert the note
    query = f'insert $n isa alh-note, has id "{nid}", has content "{escape_string(args.content)}"'
    if args.name:
        query += f', has name "{escape_string(args.name)}"'
    if args.confidence:
        query += f", has confidence {args.confidence}"
    query += ";"

    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(query).resolve()
            tx.commit()

        # Create alh-aboutness relation
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            rel_query = f'match $s isa alh-identifiable-entity, has id "{args.subject}"; $n isa alh-note, has id "{nid}"; insert (note: $n, subject: $s) isa alh-aboutness;'
            tx.query(rel_query).resolve()
            tx.commit()

        # Add tags if specified
        if args.tags:
            for tag in args.tags:
                tag_id = generate_id("tag")
                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    try:
                        tx.query(f'insert $t isa alh-tag, has id "{tag_id}", has name "{tag}";').resolve()
                        tx.commit()
                    except Exception:
                        tx.rollback()  # Tag might already exist

                with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                    tx.query(
                        f'match $n isa alh-note, has id "{nid}"; $t isa alh-tag, has name "{tag}"; insert (tagged-entity: $n, tag: $t) isa alh-tagging;'
                    ).resolve()
                    tx.commit()

    print(json.dumps({"success": True, "note_id": nid, "subject": args.subject}))


def query_collection(args):
    """Get collection info and members."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            # Get collection
            result = list(tx.query(
                f'match $c isa alh-collection, has id "{args.id}"; '
                f'fetch {{ "id": $c.id, "name": $c.name, "description": $c.description }};'
            ).resolve())
            if not result:
                print(json.dumps({"success": False, "error": "Collection not found"}))
                return

            # Get members
            members = list(tx.query(
                f'match $c isa alh-collection, has id "{args.id}"; '
                f'(collection: $c, member: $m) isa alh-collection-membership; '
                f'fetch {{ "id": $m.id, "name": $m.name }};'
            ).resolve())

        print(
            json.dumps(
                {
                    "success": True,
                    "collection": {k: v for k, v in result[0].items() if v is not None},
                    "members": [{k: v for k, v in m.items() if v is not None} for m in members],
                    "member_count": len(members),
                },
                indent=2,
            )
        )


def query_notes(args):
    """Find notes about an entity."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            query = (
                f'match $s isa alh-identifiable-entity, has id "{args.subject}"; '
                f'(note: $n, subject: $s) isa alh-aboutness; '
                f'fetch {{ "id": $n.id, "name": $n.name, "content": $n.content, "confidence": $n.confidence }};'
            )
            results = [{k: v for k, v in r.items() if v is not None}
                       for r in tx.query(query).resolve()]

        print(
            json.dumps(
                {
                    "success": True,
                    "subject": args.subject,
                    "notes": results,
                    "count": len(results),
                },
                indent=2,
            )
        )


def tag_entity(args):
    """Tag an entity."""
    with get_driver() as driver:
        # Create tag if not exists
        tag_id = generate_id("tag")
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            try:
                tx.query(f'insert $t isa alh-tag, has id "{tag_id}", has name "{args.tag}";').resolve()
                tx.commit()
            except Exception:
                tx.rollback()  # Tag might already exist

        # Create tagging relation
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(
                f'match $e isa alh-identifiable-entity, has id "{args.entity}"; $t isa alh-tag, has name "{args.tag}"; insert (tagged-entity: $e, tag: $t) isa alh-tagging;'
            ).resolve()
            tx.commit()

    print(json.dumps({"success": True, "entity": args.entity, "tag": args.tag}))


def search_tag(args):
    """Search entities by tag."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            query = (
                f'match $t isa alh-tag, has name "{args.tag}"; '
                f'(tagged-entity: $e, tag: $t) isa alh-tagging; '
                f'fetch {{ "id": $e.id, "name": $e.name }};'
            )
            results = [{k: v for k, v in r.items() if v is not None}
                       for r in tx.query(query).resolve()]

        print(
            json.dumps(
                {
                    "success": True,
                    "tag": args.tag,
                    "entities": results,
                    "count": len(results),
                },
                indent=2,
            )
        )


def export_db(args):
    """Export the full TypeDB database using the TypeDB Python driver API."""
    if not TYPEDB_AVAILABLE:
        print(json.dumps({"success": False, "error": "typedb-driver not installed"}))
        return

    database = args.database or TYPEDB_DATABASE

    # Build timestamped folder name
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    folder_name = f"{database}_export_{timestamp}"

    # Determine cache directory
    cache_dir_env = os.getenv("ALHAZEN_CACHE_DIR")
    if cache_dir_env:
        cache_dir = Path(cache_dir_env).expanduser()
    else:
        cache_dir = Path.home() / ".alhazen" / "cache"
    export_dir = cache_dir / "typedb" / folder_name
    export_dir.mkdir(parents=True, exist_ok=True)

    schema_file = f"{database}_schema.typeql"
    data_file = f"{database}_data.typedb"
    local_schema = export_dir / schema_file
    local_data = export_dir / data_file

    print(f"Exporting database '{database}' via Python driver...", file=sys.stderr)

    with get_driver() as driver:
        db = driver.databases.get(database)
        db.export_to_file(str(local_schema), str(local_data))

    # Create zip archive
    zip_path = export_dir.parent / f"{folder_name}.zip"
    print(f"Creating zip archive...", file=sys.stderr)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for filepath in export_dir.iterdir():
            zf.write(filepath, f"{folder_name}/{filepath.name}")

    # Get file sizes
    schema_size = local_schema.stat().st_size
    data_size = local_data.stat().st_size
    zip_size = zip_path.stat().st_size

    # Remove unzipped folder (keep only the zip)
    shutil.rmtree(export_dir)

    print(json.dumps({
        "success": True,
        "database": database,
        "timestamp": timestamp,
        "zip_path": str(zip_path),
        "zip_size": zip_size,
        "contents": {
            "schema": {"file": schema_file, "size": schema_size},
            "data": {"file": data_file, "size": data_size},
        },
    }, indent=2))


def import_db(args):
    """Import a TypeDB database from a previously exported zip using the Python driver API."""
    if not TYPEDB_AVAILABLE:
        print(json.dumps({"success": False, "error": "typedb-driver not installed"}))
        return

    zip_path = Path(args.zip).expanduser()
    if not zip_path.exists():
        print(json.dumps({"success": False, "error": f"File not found: {zip_path}"}))
        return

    database = args.database

    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        tmpdir = Path(tmpdir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmpdir)

        # Find the schema and data files
        schema_file = None
        data_file = None
        for f in tmpdir.rglob("*"):
            if f.suffix == ".typeql":
                schema_file = f
            elif f.suffix == ".typedb":
                data_file = f

        if not schema_file or not data_file:
            print(json.dumps({
                "success": False,
                "error": "Zip must contain one .typeql (schema) and one .typedb (data) file"
            }))
            return

        print(f"Importing database '{database}' via Python driver...", file=sys.stderr)

        schema_text = schema_file.read_text()

        with get_driver() as driver:
            driver.databases.import_from_file(database, schema_text, str(data_file))

    print(json.dumps({
        "success": True,
        "database": database,
        "source": str(zip_path),
    }, indent=2))


# -----------------------------------------------------------------------------
# Analysis pipeline notes (stored, re-runnable Hamilton workflows)
# -----------------------------------------------------------------------------
# A note that subtypes alh-analysis-pipeline-note stores a Hamilton module's
# source (alh-pipeline-script) + a JSON config (alh-pipeline-config). The generic
# runner reloads the module, builds the DAG, executes the requested terminal
# outputs, and writes each result back to the attribute named by the config's
# output_attr_map (default: content). Pipeline notes link to their source
# collections (the input data) via alh-aboutness.

_PIPELINE_ID_PREFIXES = {
    "scilit-faceting-note": "scfn",
    "alh-analysis-pipeline-note": "apn",
}


def _read_arg_or_file(value: str) -> str:
    """Return the literal value, or the file contents if value starts with '@'."""
    if value.startswith("@"):
        with open(value[1:]) as f:
            return f.read()
    return value


def load_pipeline_module(source_code: str, module_name: str = "alh_pipeline"):
    """Dynamically load a Hamilton pipeline module from a source-code string.

    Uses a real temp file + importlib because Hamilton's introspection calls
    inspect.getsource(), which requires a path on disk.
    """
    import importlib.util
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", prefix=f"{module_name}_", delete=False
    ) as f:
        f.write(source_code)
        tmp_path = f.name
    spec = importlib.util.spec_from_file_location(module_name, tmp_path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    os.unlink(tmp_path)
    return mod


def create_pipeline_note(args):
    """Create an analysis-pipeline note (or subtype) and link it to source collections."""
    note_type = args.type
    prefix = _PIPELINE_ID_PREFIXES.get(note_type, "pnote")
    nid = args.id or generate_id(prefix)

    script = _read_arg_or_file(args.script)
    config = _read_arg_or_file(args.config)
    try:
        json.loads(config)
    except json.JSONDecodeError as e:
        print(json.dumps({"success": False, "error": f"--config is not valid JSON: {e}"}))
        sys.exit(1)

    now = datetime.now().isoformat(timespec="seconds")
    collection_ids = [c.strip() for c in args.collections.split(",") if c.strip()] if args.collections else []

    query = (
        f'insert $n isa {note_type}, has id "{nid}", '
        f'has alh-pipeline-script "{escape_string(script)}", '
        f'has alh-pipeline-config "{escape_string(config)}", '
        f'has created-at {now}'
    )
    if args.name:
        query += f', has name "{escape_string(args.name)}"'
    query += ";"

    linked = []
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            tx.query(query).resolve()
            tx.commit()

        for cid in collection_ids:
            with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
                rel = (
                    f'match $n isa {note_type}, has id "{nid}"; '
                    f'$c isa alh-identifiable-entity, has id "{escape_string(cid)}"; '
                    f'insert (note: $n, subject: $c) isa alh-aboutness;'
                )
                tx.query(rel).resolve()
                tx.commit()
            linked.append(cid)

    print(json.dumps({
        "success": True,
        "note_id": nid,
        "type": note_type,
        "linked_collections": linked,
        "script_chars": len(script),
    }))


def run_pipeline_note(args):
    """Execute a stored Hamilton pipeline note and write terminal outputs back."""
    nid = escape_string(args.id)
    with get_driver() as driver:
        # Fetch script + config (polymorphic: isa includes subtypes)
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(
                f'match $n isa alh-analysis-pipeline-note, has id "{nid}"; '
                f'fetch {{ "script": $n.alh-pipeline-script, "config": $n.alh-pipeline-config }};'
            ).resolve())

        if not results:
            print(json.dumps({"success": False, "error": f"Pipeline note {args.id} not found"}))
            sys.exit(1)

        script = results[0].get("script")
        config_str = results[0].get("config")
        if not script:
            print(json.dumps({"success": False, "error": "Note has no alh-pipeline-script"}))
            sys.exit(1)
        if not config_str:
            print(json.dumps({"success": False, "error": "Note has no alh-pipeline-config"}))
            sys.exit(1)

        config = json.loads(config_str)
        outputs = config.get("outputs", [])
        if not outputs:
            print(json.dumps({"success": False, "error": "config has no 'outputs' list"}))
            sys.exit(1)

        # Resolve inputs (explicit + env-sourced)
        inputs = dict(config.get("inputs", {}))
        for param_name, env_var in config.get("env_inputs", {}).items():
            val = os.environ.get(env_var)
            if val is None:
                print(json.dumps({"success": False, "error": f"Required env var {env_var} (for '{param_name}') is not set"}))
                sys.exit(1)
            inputs[param_name] = val

        try:
            from hamilton import driver as h_driver  # noqa: PLC0415
        except ImportError:
            print(json.dumps({"success": False, "error": "sf-hamilton not installed. Run: uv add sf-hamilton"}))
            sys.exit(1)

        print("Loading pipeline module...", file=sys.stderr)
        mod = load_pipeline_module(script, module_name=f"pipeline_{nid}")

        hamilton_cfg = config.get("hamilton", {})
        builder = h_driver.Builder().with_modules(mod)
        if hamilton_cfg.get("with_cache"):
            builder = builder.with_cache()
        dr = builder.build()

        print(f"Executing Hamilton outputs: {outputs}", file=sys.stderr)
        results_map = dr.execute(outputs, inputs=inputs)

        # Write terminal outputs back per output_attr_map (default -> content)
        output_attr_map = config.get("output_attr_map", {})
        written = {}
        non_persisted = {}
        with driver.transaction(TYPEDB_DATABASE, TransactionType.WRITE) as tx:
            for output_name, value in results_map.items():
                attr_name = output_attr_map.get(output_name)
                if attr_name is None:
                    # Not mapped to an attribute: report but don't persist
                    non_persisted[output_name] = value if isinstance(value, (int, float, str, dict, list, bool)) else str(value)
                    continue
                if not isinstance(value, str):
                    value = json.dumps(value)
                escaped_val = escape_string(value)
                tx.query(
                    f'match $n isa alh-analysis-pipeline-note, has id "{nid}", has {attr_name} $old; '
                    f'delete has $old of $n;'
                ).resolve()
                tx.query(
                    f'match $n isa alh-analysis-pipeline-note, has id "{nid}"; '
                    f'insert $n has {attr_name} "{escaped_val}";'
                ).resolve()
                written[output_name] = {"attr": attr_name, "chars": len(value)}
            tx.commit()

        # Observable-Plot support: a note may carry a `plot_code` (JS expression string) and a
        # `plot_data_output` naming which output holds the row data; the dashboard evals plot_code
        # against `data`. Fall back to the first list-of-dicts output when unnamed.
        plot_code = config.get("plot_code")
        plot_data = None
        data_output = config.get("plot_data_output")
        if data_output and data_output in results_map:
            plot_data = results_map[data_output]
        else:
            for v in results_map.values():
                if isinstance(v, list) and v and isinstance(v[0], dict):
                    plot_data = v
                    break
        try:
            json.dumps(plot_data)
        except (TypeError, ValueError):
            plot_data = None

        print(json.dumps({
            "success": True,
            "note_id": args.id,
            "outputs_written": written,
            "outputs_not_persisted": non_persisted,
            "plot_code": plot_code,
            "data": plot_data,
        }))


def show_pipeline_note(args):
    """Round-trip a pipeline note: script, parsed config, and content."""
    nid = escape_string(args.id)
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            results = list(tx.query(
                f'match $n isa alh-analysis-pipeline-note, has id "{nid}"; '
                f'fetch {{ "name": $n.name, "script": $n.alh-pipeline-script, '
                f'"config": $n.alh-pipeline-config, "content": $n.content }};'
            ).resolve())

    if not results:
        print(json.dumps({"success": False, "error": f"Pipeline note {args.id} not found"}))
        sys.exit(1)

    r = results[0]
    config_str = r.get("config")
    config = json.loads(config_str) if config_str else None
    out = {
        "success": True,
        "note_id": args.id,
        "name": r.get("name"),
        "script": r.get("script"),
        "config": config,
        "content": r.get("content"),
        # convenience for the dashboard Plot renderer (also inside config)
        "plot_code": (config or {}).get("plot_code"),
    }
    print(json.dumps(out, indent=2))


def list_pipeline_notes(args):
    """List all analysis pipeline notes (polymorphic), with their linked source collections."""
    with get_driver() as driver:
        with driver.transaction(TYPEDB_DATABASE, TransactionType.READ) as tx:
            rows = list(tx.query(
                'match $n isa alh-analysis-pipeline-note; '
                'fetch { "id": $n.id, "name": $n.name, "content": $n.content };'
            ).resolve())

            notes = []
            for r in rows:
                nid = r["id"]
                colls = list(tx.query(
                    f'match $n isa alh-analysis-pipeline-note, has id "{escape_string(nid)}"; '
                    f'(note: $n, subject: $c) isa alh-aboutness; $c isa alh-collection; '
                    f'fetch {{ "id": $c.id, "name": $c.name }};'
                ).resolve())
                content = r.get("content")
                notes.append({
                    "id": nid,
                    "name": r.get("name"),
                    "has_content": bool(content),
                    "content_preview": content[:280] if content else None,
                    "collections": [{k: v for k, v in c.items() if v is not None} for c in colls],
                })

    print(json.dumps({"success": True, "notes": notes, "count": len(notes)}, indent=2))


def main():
    parser = argparse.ArgumentParser(
        description="TypeDB Notebook CLI for Alhazen's knowledge graph"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # insert-collection
    p = subparsers.add_parser("insert-collection", help="Create a new collection")
    p.add_argument("--name", required=True, help="Collection name")
    p.add_argument("--description", help="Collection description")
    p.add_argument("--query", help="Logical query defining membership")
    p.add_argument("--id", help="Specific ID (auto-generated if not provided)")

    # insert-note
    p = subparsers.add_parser("insert-note", help="Create a note about an entity")
    p.add_argument("--subject", required=True, help="ID of entity this note is about")
    p.add_argument("--content", required=True, help="Note content")
    p.add_argument("--name", help="Note name/title")
    p.add_argument("--confidence", type=float, help="Confidence score (0.0-1.0)")
    p.add_argument("--tags", nargs="+", help="Tags to apply")
    p.add_argument("--id", help="Specific ID")

    # query-collection
    p = subparsers.add_parser("query-collection", help="Get collection info")
    p.add_argument("--id", required=True, help="Collection ID")

    # query-notes
    p = subparsers.add_parser("query-notes", help="Find notes about an entity")
    p.add_argument("--subject", required=True, help="Entity ID")

    # tag
    p = subparsers.add_parser("tag", help="Tag an entity")
    p.add_argument("--entity", required=True, help="Entity ID")
    p.add_argument("--tag", required=True, help="Tag name")

    # search-tag
    p = subparsers.add_parser("search-tag", help="Search by tag")
    p.add_argument("--tag", required=True, help="Tag to search for")

    # export-db
    p = subparsers.add_parser("export-db", help="Export database to timestamped zip")
    p.add_argument("--database", help=f"Database name (default: {TYPEDB_DATABASE})")

    # import-db
    p = subparsers.add_parser("import-db", help="Import database from exported zip")
    p.add_argument("--zip", required=True, help="Path to the export zip file")
    p.add_argument("--database", required=True, help="Target database name (must not exist)")

    # create-pipeline-note
    p = subparsers.add_parser(
        "create-pipeline-note",
        help="Store a Hamilton pipeline as a note and link it to source collections",
    )
    p.add_argument("--type", default="alh-analysis-pipeline-note",
                   help="Note type (subtype of alh-analysis-pipeline-note; default: alh-analysis-pipeline-note)")
    p.add_argument("--script", required=True, help="Hamilton module source (or @path/to/module.py)")
    p.add_argument("--config", required=True, help="JSON config (or @path/to/config.json)")
    p.add_argument("--collections", help="Comma-separated source collection IDs (linked via alh-aboutness)")
    p.add_argument("--name", help="Note name/title")
    p.add_argument("--id", help="Specific ID (auto-generated if not provided)")

    # run-pipeline-note
    p = subparsers.add_parser("run-pipeline-note", help="Execute a stored pipeline note and write outputs back")
    p.add_argument("--id", required=True, help="Pipeline note ID")

    # show-pipeline-note
    p = subparsers.add_parser("show-pipeline-note", help="Show a pipeline note's script, config, and content")
    p.add_argument("--id", required=True, help="Pipeline note ID")

    # list-pipeline-notes
    p = subparsers.add_parser("list-pipeline-notes",
                              help="List analysis pipeline notes with their linked collections")

    # ---- Generic graph-CRUD engine --------------------------------------------

    # describe-schema
    p = subparsers.add_parser("describe-schema",
                              help="Inspect the parsed schema (a single type, or a global summary)")
    p.add_argument("--type", help="Type to describe (entity, relation, or attribute)")

    # scan-databases (hub DB switcher: per-DB availability of each skill dashboard)
    subparsers.add_parser("scan-databases",
                          help="List databases and, per skill, whether its dashboard is available")

    # create-entity
    p = subparsers.add_parser("create-entity", help="Create (or upsert) a typed entity")
    p.add_argument("--type", required=True, help="Concrete entity type (e.g. scilit-evidence)")
    p.add_argument("--id", help="Specific id (auto-generated from type if omitted)")
    p.add_argument("--attr", action="append", help="Attribute as key=value (repeat for multiple)")
    p.add_argument("--upsert", action="store_true", help="Create if absent, else set-attr (requires --id)")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL without writing")

    # set-attr
    p = subparsers.add_parser("set-attr", help="Set/append attributes on an entity (atomic)")
    p.add_argument("--id", required=True, help="Entity id")
    p.add_argument("--type", help="Concrete type hint (only needed for --dry-run cardinality)")
    p.add_argument("--attr", action="append", required=True, help="key=value (repeat for multiple)")
    p.add_argument("--replace", action="store_true", help="Replace multi-valued sets (clear first)")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL without writing")

    # delete-attr
    p = subparsers.add_parser("delete-attr", help="Remove an attribute value (or all values of a key)")
    p.add_argument("--id", required=True, help="Entity id")
    p.add_argument("--attr", action="append", required=True, help="key (all values) or key=value (repeat for multiple)")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL without writing")

    # link
    p = subparsers.add_parser("link", help="Create a relation between entities")
    p.add_argument("--relation", required=True, help="Relation type (e.g. alh-aboutness)")
    p.add_argument("--role", action="append", required=True, help="role=entity-id (repeat for each role)")
    p.add_argument("--attr", action="append", help="Relation attribute as key=value (repeat for multiple)")
    p.add_argument("--idempotent", action="store_true", help="No-op if the relation already exists")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL without writing")

    # unlink
    p = subparsers.add_parser("unlink", help="Delete a relation between entities")
    p.add_argument("--relation", required=True, help="Relation type")
    p.add_argument("--role", action="append", required=True, help="role=entity-id (repeat for each role)")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL without writing")

    # delete-entity
    p = subparsers.add_parser("delete-entity", help="Delete an entity")
    p.add_argument("--id", required=True, help="Entity id")
    p.add_argument("--detach", action="store_true", help="Unlink the entity's relations first")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL without writing")

    # query (guarded read-only)
    p = subparsers.add_parser("query", help="Run a guarded read-only match-fetch query")
    p.add_argument("--read", required=True, help="A read-only TypeQL match...fetch query (must bind a variable)")
    p.add_argument("--limit", type=int, help="Max rows (default 1000)")

    # apply
    p = subparsers.add_parser("apply", help="Run an ordered op-list in ONE atomic transaction")
    p.add_argument("--ops", required=True, help="JSON op-list (or @path/to/ops.json)")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL per op without writing")

    # apply-recipe
    p = subparsers.add_parser("apply-recipe", help="Run a named recipe (op-list template) atomically")
    p.add_argument("--recipe", required=True, help="Recipe name (resolved from skills/*/recipes/*.json)")
    p.add_argument("--param", action="append", help="Recipe param as key=value (repeat for multiple)")
    p.add_argument("--dry-run", action="store_true", help="Print TypeQL per op without writing")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if not TYPEDB_AVAILABLE:
        print(json.dumps({"success": False, "error": "typedb-driver not installed"}))
        sys.exit(1)

    commands = {
        "insert-collection": insert_collection,
        "insert-note": insert_note,
        "query-collection": query_collection,
        "query-notes": query_notes,
        "tag": tag_entity,
        "search-tag": search_tag,
        "export-db": export_db,
        "import-db": import_db,
        "create-pipeline-note": create_pipeline_note,
        "run-pipeline-note": run_pipeline_note,
        "show-pipeline-note": show_pipeline_note,
        "list-pipeline-notes": list_pipeline_notes,
        "describe-schema": describe_schema,
        "scan-databases": scan_databases,
        "create-entity": create_entity,
        "set-attr": set_attr,
        "delete-attr": delete_attr,
        "link": link_entities,
        "unlink": unlink_entities,
        "delete-entity": delete_entity,
        "query": query_graph,
        "apply": apply_ops,
        "apply-recipe": apply_recipe,
    }

    try:
        commands[args.command](args)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
