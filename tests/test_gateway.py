"""Tests for the skill query gateway dispatcher.

Parity test (gateway output == direct CLI output) is skipped when TypeDB is not
reachable, so the suite still runs in DB-less CI.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "src"))

from skillful_alhazen.gateway import dispatcher  # noqa: E402


def _typedb_up() -> bool:
    try:
        from typedb.driver import Credentials, DriverOptions, TypeDB

        host = os.getenv("TYPEDB_HOST", "localhost")
        port = os.getenv("TYPEDB_PORT", "1729")
        driver = TypeDB.driver(
            f"{host}:{port}",
            Credentials(
                os.getenv("TYPEDB_USERNAME", "admin"),
                os.getenv("TYPEDB_PASSWORD", "password"),
            ),
            DriverOptions(is_tls_enabled=False),
        )
        driver.close()
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(not _typedb_up(), reason="TypeDB not reachable")


def test_list_skills_includes_core():
    skills = dispatcher.list_skills()
    assert "agentic-memory" in skills
    assert "typedb-notebook" in skills


def test_unknown_skill_raises():
    with pytest.raises(dispatcher.DispatchError):
        dispatcher.run("does-not-exist", ["whatever"])


def test_unknown_entrypoint_raises():
    with pytest.raises(dispatcher.DispatchError):
        dispatcher.run("agentic-memory", ["x"], entrypoint="not_a_script")


@requires_db
def test_parity_with_direct_cli():
    os.environ.setdefault("TYPEDB_DATABASE", "alhazen_notebook")

    gw = dispatcher.run("agentic-memory", ["list-persons"])
    assert gw["ok"] is True
    assert gw["exit_code"] == 0

    proc = subprocess.run(
        ["uv", "run", "python",
         str(REPO / "skills/agentic-memory/agentic_memory.py"), "list-persons"],
        cwd=REPO,
        capture_output=True,
        text=True,
    )
    cli = json.loads(proc.stdout)
    assert gw["result"] == cli


@requires_db
def test_warm_module_is_cached():
    os.environ.setdefault("TYPEDB_DATABASE", "alhazen_notebook")
    dispatcher.run("typedb-notebook", ["describe-schema"])
    # Second call must reuse the cached module rather than re-importing.
    assert ("typedb-notebook", "typedb_notebook") in dispatcher._module_cache
