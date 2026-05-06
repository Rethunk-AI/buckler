"""hooks.json merge utility.

Provides idempotent merging of Buckler hook entries into Cursor's hooks.json.
Run via: python -m buckler.hooks merge
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, cast

from buckler import paths

log = logging.getLogger(__name__)

BUCKLER_HOOK_PREFIX = "buckler:"

_HOOK_DEFINITIONS = [
    {
        "name": "buckler:pre-shell-exec",
        "description": "Buckler agent-git pack: deny git commit, force push, remote destruction",
        "event": "beforeShellExecution",
        "timeout": 5000,
        "failClosed": True,
    },
    {
        "name": "buckler:pre-shell-tool",
        "description": "Buckler defense-in-depth: intercept Shell tool proposals",
        "event": "preToolUse",
        "matchers": [{"type": "Tool", "name": "Shell"}],
        "timeout": 5000,
        "failClosed": True,
    },
    {
        "name": "buckler:post-tool",
        "description": "Buckler MCP nudge: steer agent toward MCP tools",
        "event": "postToolUse",
        "timeout": 3000,
        "failClosed": False,
    },
]


def _buckler_command(venv_python: Path | None = None) -> str:
    """Compute the absolute command for hooks.json."""
    if venv_python is not None:
        return f"{venv_python} -m buckler --driver cursor"
    cur = paths.current_dir()
    if cur is not None:
        py = cur / ".venv" / "bin" / "python"
        if py.exists():
            return f"{py} -m buckler --driver cursor"
    # Development fallback: use the active Python
    return f"{sys.executable} -m buckler --driver cursor"


def _read_hooks_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        with path.open() as f:
            return cast("dict[str, Any]", json.load(f))
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Could not read %s: %s", path, e)
        return {}


def _write_hooks_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def merge(hooks_path: Path | None = None, venv_python: Path | None = None, dry_run: bool = False) -> None:
    """Idempotently merge Buckler hook entries into hooks.json."""
    target = hooks_path or paths.cursor_hooks_json()
    command = _buckler_command(venv_python)

    data = _read_hooks_json(target)
    existing_hooks: list[dict[str, Any]] = data.get("hooks", [])

    # Remove any existing buckler entries (we'll re-add fresh)
    filtered = [h for h in existing_hooks if not h.get("name", "").startswith(BUCKLER_HOOK_PREFIX)]

    # Build new entries with the current command path
    new_entries: list[dict[str, Any]] = []
    for defn in _HOOK_DEFINITIONS:
        entry: dict[str, Any] = {**defn, "command": command}
        new_entries.append(entry)

    data["hooks"] = filtered + new_entries

    if dry_run:
        print(json.dumps(data, indent=2))
        return

    _write_hooks_json(target, data)
    log.info("Merged %d Buckler hook entries into %s", len(new_entries), target)


def strip(hooks_path: Path | None = None, dry_run: bool = False) -> None:
    """Remove all Buckler hook entries from hooks.json (for uninstall)."""
    target = hooks_path or paths.cursor_hooks_json()
    data = _read_hooks_json(target)
    existing: list[dict[str, Any]] = data.get("hooks", [])
    filtered = [h for h in existing if not h.get("name", "").startswith(BUCKLER_HOOK_PREFIX)]
    removed = len(existing) - len(filtered)
    data["hooks"] = filtered

    if dry_run:
        print(f"Would remove {removed} Buckler entries from {target}")
        print(json.dumps(data, indent=2))
        return

    _write_hooks_json(target, data)
    log.info("Removed %d Buckler entries from %s", removed, target)


def status(hooks_path: Path | None = None) -> None:
    """Print current Buckler entries in hooks.json."""
    target = hooks_path or paths.cursor_hooks_json()
    data = _read_hooks_json(target)
    hooks: list[dict[str, Any]] = data.get("hooks", [])
    buckler_hooks = [h for h in hooks if h.get("name", "").startswith(BUCKLER_HOOK_PREFIX)]
    if buckler_hooks:
        print(f"Buckler hooks in {target}:")
        for h in buckler_hooks:
            print(f"  {h['name']} ({h['event']}): {h.get('command', '?')}")
    else:
        print(f"No Buckler hooks found in {target}")


def main() -> None:
    """CLI entry for python -m buckler.hooks <subcommand>."""
    parser = argparse.ArgumentParser(prog="python -m buckler.hooks")
    sub = parser.add_subparsers(dest="cmd")

    merge_p = sub.add_parser("merge", help="Merge Buckler entries into hooks.json")
    merge_p.add_argument("--hooks-json", type=Path, default=None)
    merge_p.add_argument("--venv-python", type=Path, default=None)
    merge_p.add_argument("--dry-run", action="store_true")

    strip_p = sub.add_parser("strip", help="Remove Buckler entries from hooks.json")
    strip_p.add_argument("--hooks-json", type=Path, default=None)
    strip_p.add_argument("--dry-run", action="store_true")

    status_p = sub.add_parser("status", help="Show current Buckler entries in hooks.json")
    status_p.add_argument("--hooks-json", type=Path, default=None)

    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    if args.cmd == "merge":
        merge(hooks_path=args.hooks_json, venv_python=args.venv_python, dry_run=args.dry_run)
    elif args.cmd == "strip":
        strip(hooks_path=args.hooks_json, dry_run=args.dry_run)
    elif args.cmd == "status":
        status(hooks_path=args.hooks_json)
    else:
        parser.print_help()


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
