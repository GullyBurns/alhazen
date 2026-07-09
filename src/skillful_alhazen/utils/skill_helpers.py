"""
Shared utility functions for Alhazen skill CLI scripts.

Canonical implementations of escape_string, generate_id, get_timestamp.
Import these in skill scripts rather than copy-pasting.
"""

import os
import uuid
from datetime import datetime, timezone


def escape_string(s: str) -> str:
    """Escape special characters for TypeQL string literals."""
    if s is None:
        return ""
    return s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "")


def generate_id(prefix: str) -> str:
    """Generate a unique ID with a domain prefix."""
    return f"{prefix}-{uuid.uuid4().hex[:12]}"


def get_timestamp() -> str:
    """Return current UTC timestamp in TypeQL datetime format (no timezone suffix)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


def check_infrastructure(
    skill_name: str,
    schema_check_type: str | None = None,
    has_dashboard: bool = False,
    zip_name: str | None = None,
) -> None:
    """
    Verify TypeDB is reachable, the skill schema is loaded, and (optionally) the
    dashboard container is running. Prints a helpful error and exits 1 if not.

    Call this at the top of each skill script's main() before argument dispatch.
    """
    import subprocess
    import sys

    errors: list[str] = []
    make_cmd = f"make install-skill ZIP={zip_name}" if zip_name else "make build"

    # 1. TypeDB connectivity
    typedb_ok = False
    try:
        from typedb.driver import Credentials, DriverOptions, TypeDB
        host = os.environ.get("TYPEDB_HOST", "localhost")
        port = os.environ.get("TYPEDB_PORT", "1729")
        user = os.environ.get("TYPEDB_USERNAME", "admin")
        pwd  = os.environ.get("TYPEDB_PASSWORD", "password")
        driver = TypeDB.driver(
            f"{host}:{port}",
            Credentials(user, pwd),
            DriverOptions(is_tls_enabled=False),
        )
        driver.close()
        typedb_ok = True
    except Exception:
        errors.append("TypeDB is not running (start with: make db-start)")

    # 2. Schema check — only if TypeDB is reachable and a check type is given
    if typedb_ok and schema_check_type:
        try:
            from typedb.driver import Credentials, DriverOptions, TransactionType, TypeDB
            host = os.environ.get("TYPEDB_HOST", "localhost")
            port = os.environ.get("TYPEDB_PORT", "1729")
            db   = os.environ.get("TYPEDB_DATABASE", "alh_core")
            user = os.environ.get("TYPEDB_USERNAME", "admin")
            pwd  = os.environ.get("TYPEDB_PASSWORD", "password")
            driver = TypeDB.driver(
                f"{host}:{port}",
                Credentials(user, pwd),
                DriverOptions(is_tls_enabled=False),
            )
            with driver.transaction(db, TransactionType.READ) as tx:
                list(tx.query(f"match $x isa {schema_check_type}; limit 0;").resolve())
            driver.close()
        except Exception:
            errors.append(
                f"TypeDB schema for '{skill_name}' not loaded "
                f"(run: {make_cmd})"
            )

    # 3. Dashboard container check (optional)
    if has_dashboard:
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=alhazen-dashboard",
                 "--format", "{{.Names}}"],
                capture_output=True, text=True, timeout=5,
            )
            if "alhazen-dashboard" not in result.stdout:
                errors.append(
                    "Dashboard container not running "
                    f"(run: {make_cmd})"
                )
        except Exception:
            errors.append("Could not check dashboard status (is Docker running?)")

    if errors:
        print(f"✗ {skill_name}: infrastructure not ready:", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        print(f"\n  Fix: {make_cmd}", file=sys.stderr)
        sys.exit(1)
