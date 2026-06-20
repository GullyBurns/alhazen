"""Alhazen skill query gateway.

A warm, long-lived service that imports each skill's CLI module once and drives
its existing ``main()`` in-process via a synthetic ``sys.argv`` — replacing the
dashboard's per-request ``uv run python <skill>.py`` subprocess spawning.

The command contract is unchanged: every skill parses ``argv`` with argparse and
prints a JSON object to stdout. The gateway captures that stdout and returns it.
"""

from .dispatcher import DispatchError, list_skills, run

__all__ = ["DispatchError", "list_skills", "run"]
