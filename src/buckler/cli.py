"""Buckler CLI entry point.

Usage modes:
  buckler [--driver cursor]        Read harness JSON from stdin, write response to stdout.
  buckler evaluate [--input F] [--output F]  Read PolicyInput, write PolicyOutput (harness-neutral).
  buckler validate                 Validate builtin pack and user rules YAML (non-zero on errors).
  buckler --version                Print version.

Environment:
  BUCKLER_DRIVER   Default driver name (cursor, etc.). Overridden by --driver.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, cast

from buckler import __version__
from buckler.adapters import cursor as cursor_adapter
from buckler.core import PolicyError, evaluate
from buckler.pack_loader import validate_pack_files

log = logging.getLogger(__name__)


def _load_json_from(source: str | None) -> dict[str, Any]:
    raw = sys.stdin.read() if source is None or source == "-" else Path(source).read_text()
    try:
        return cast("dict[str, Any]", json.loads(raw))
    except json.JSONDecodeError as e:
        log.error("Invalid JSON input: %s", e)
        sys.exit(1)


def _write_json_to(dest: str | None, data: dict[str, Any]) -> None:
    out = json.dumps(data, indent=2)
    if dest is None or dest == "-":
        print(out)
    else:
        Path(dest).write_text(out + "\n")


def _policy_error_cursor_response(msg: str) -> dict[str, Any]:
    """Fail-closed JSON for Cursor pre-hooks when policy input is invalid."""
    return {"permission": "deny", "message": msg, "agent_message": msg}


def _run_cursor_driver(args: argparse.Namespace) -> None:
    try:
        raw = _load_json_from(None)
        policy_input = cursor_adapter.adapt_input(raw)

        # Inject bypass env from raw input if Cursor passes env vars
        # (Cursor doesn't currently expose env; we check the subprocess env as fallback)
        bypass = os.environ.get("RETHUNK_ALLOW_SHELL", "0")
        if bypass == "1":
            policy_input.setdefault("env", {})["RETHUNK_ALLOW_SHELL"] = "1"

        policy_output = evaluate(policy_input)
        cursor_response = cursor_adapter.adapt_output(policy_output, raw)
        print(json.dumps(cursor_response))
    except PolicyError as e:
        log.error("%s", e)
        print(json.dumps(_policy_error_cursor_response(str(e))))


def _run_evaluate(args: argparse.Namespace) -> None:
    policy_input = _load_json_from(getattr(args, "input", None))
    try:
        policy_output = evaluate(policy_input)
    except PolicyError as e:
        log.error("%s", e)
        sys.exit(2)
    _write_json_to(getattr(args, "output", None), policy_output)


def _run_validate(args: argparse.Namespace) -> None:
    errs = validate_pack_files(
        packs_dir=args.packs_dir,
        user_rules_dir=args.rules_dir,
    )
    if errs:
        for err in errs:
            print(err, file=sys.stderr)
        sys.exit(1)
    print("OK: all pack YAML validated.", file=sys.stderr)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="buckler",
        description="Buckler Agent Gatehouse — policy evaluation for AI coding harnesses.",
    )
    parser.add_argument("--version", action="version", version=f"buckler {__version__}")
    parser.add_argument(
        "--driver",
        default=os.environ.get("BUCKLER_DRIVER", "cursor"),
        choices=["cursor"],
        help="Harness adapter to use (default: cursor or $BUCKLER_DRIVER)",
    )

    sub = parser.add_subparsers(dest="subcommand")

    eval_p = sub.add_parser(
        "evaluate",
        help="Evaluate a PolicyInput JSON and write PolicyOutput (harness-neutral)",
    )
    eval_p.add_argument(
        "--input",
        "-i",
        default=None,
        metavar="FILE",
        help="PolicyInput JSON file (default: stdin)",
    )
    eval_p.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="PolicyOutput JSON file (default: stdout)",
    )

    val_p = sub.add_parser(
        "validate",
        help="Validate builtin packs and user rules.d YAML (exit 1 on errors)",
    )
    val_p.add_argument(
        "--packs-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Override builtin packs directory (default: installed or dev packs/)",
    )
    val_p.add_argument(
        "--rules-dir",
        type=Path,
        default=None,
        metavar="DIR",
        help="Override user rules.d directory (default: XDG config path)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    if args.subcommand == "evaluate":
        _run_evaluate(args)
    elif args.subcommand == "validate":
        _run_validate(args)
    elif args.driver == "cursor":
        _run_cursor_driver(args)
    else:
        log.error("Unknown driver: %s", args.driver)
        sys.exit(1)


if __name__ == "__main__":  # pragma: no cover
    main()  # pragma: no cover
