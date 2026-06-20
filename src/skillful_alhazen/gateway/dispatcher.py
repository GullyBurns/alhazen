"""In-process skill command dispatch.

Every Alhazen skill CLI follows the same shape: argparse subparsers dispatch to
``commands[args.command](args)`` and the command ``print(json.dumps(...))`` to
stdout. So we can run any command without touching skill code: import the
module once, set ``sys.argv``, capture stdout, call ``main()``, and parse the
JSON it printed.

Scripts are resolved from the *full* skill directory (``local_skills/<skill>``
or ``skills/<skill>``) rather than the stripped ``.claude/skills`` copy, so any
sibling resources a command reads (recipes, schema files) are present.

Because ``sys.argv``/``sys.stdout`` are process-global, ``run`` serializes all
invocations behind a single lock. The FastAPI layer runs it in a thread so the
event loop stays responsive; a generous timeout guards long commands.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import sys
import threading
from pathlib import Path

import yaml

# dispatcher.py -> gateway -> skillful_alhazen -> src -> <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[3]
_LOCAL_SKILLS = _REPO_ROOT / "local_skills"
_SKILLS = _REPO_ROOT / "skills"

_lock = threading.Lock()
_module_cache: dict[tuple[str, str], object] = {}


class DispatchError(Exception):
    """Raised when a skill or entrypoint cannot be resolved."""


def _skill_root(skill: str) -> Path:
    """Resolve a skill name to its full source directory."""
    for base in (_LOCAL_SKILLS, _SKILLS):
        candidate = base / skill
        if candidate.exists():
            # resolve() follows the local_skills/<core-skill> -> ../skills symlink
            return candidate.resolve()
    raise DispatchError(f"unknown skill: {skill!r}")


def _primary_entrypoint(skill: str, root: Path) -> str:
    """Determine a skill's default script stem from its skill.yaml.

    Handles both ``cli: agentic_memory.py`` and ``scripts: [jobhunt.py, ...]``.
    Falls back to the skill name with dashes converted to underscores.
    """
    manifest = root / "skill.yaml"
    if manifest.exists():
        data = yaml.safe_load(manifest.read_text(encoding="utf-8")) or {}
        if data.get("cli"):
            return Path(data["cli"]).stem
        scripts = data.get("scripts")
        if isinstance(scripts, list) and scripts:
            return Path(scripts[0]).stem
    return skill.replace("-", "_")


def list_skills() -> list[str]:
    """List installed skills that expose a Python entrypoint."""
    names: set[str] = set()
    for base in (_LOCAL_SKILLS, _SKILLS):
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and not d.name.startswith((".", "_")):
                names.add(d.name)
    return sorted(names)


def _resolve_script(skill: str, entrypoint: str | None) -> tuple[str, Path]:
    root = _skill_root(skill)
    stem = entrypoint or _primary_entrypoint(skill, root)
    script = root / f"{stem}.py"
    if not script.exists():
        raise DispatchError(f"entrypoint not found: {skill}/{stem}.py")
    return stem, script


def _load_module(skill: str, stem: str, script: Path):
    key = (skill, stem)
    module = _module_cache.get(key)
    if module is None:
        name = f"_gw_{skill.replace('-', '_')}_{stem}"
        spec = importlib.util.spec_from_file_location(name, script)
        if spec is None or spec.loader is None:
            raise DispatchError(f"could not load module for {skill}/{stem}.py")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _module_cache[key] = module
    return module


def _exit_code(exc: SystemExit) -> int:
    if exc.code is None:
        return 0
    if isinstance(exc.code, int):
        return exc.code
    return 1  # sys.exit("message") — the message went to stderr


def run(skill: str, argv: list[str], entrypoint: str | None = None) -> dict:
    """Run a skill command and return its JSON result.

    Returns a dict with: ok, skill, entrypoint, exit_code, result (parsed JSON
    from stdout), error (JSON parse error, if any), raw (stdout when unparsable),
    and stderr.
    """
    stem, script = _resolve_script(skill, entrypoint)

    with _lock:
        module = _load_module(skill, stem, script)
        if not hasattr(module, "main"):
            raise DispatchError(f"{skill}/{stem}.py defines no main()")

        out, err = io.StringIO(), io.StringIO()
        saved_argv = sys.argv
        sys.argv = [str(script), *argv]
        code = 0
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                try:
                    module.main()
                except SystemExit as exc:
                    code = _exit_code(exc)
        finally:
            sys.argv = saved_argv

        raw = out.getvalue()
        stderr = err.getvalue()

    result = None
    parse_error = None
    if raw.strip():
        try:
            result = json.loads(raw)
        except json.JSONDecodeError as exc:
            parse_error = f"non-JSON stdout: {exc}"

    ok = parse_error is None
    return {
        "ok": ok,
        "skill": skill,
        "entrypoint": stem,
        "exit_code": code,
        "result": result,
        "error": parse_error,
        "raw": None if ok else raw,
        "stderr": stderr,
    }
