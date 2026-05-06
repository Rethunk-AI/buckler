"""Buckler CLI entry point.

Usage modes:
  buckler [--driver cursor]        Read harness JSON from stdin, write response to stdout.
  buckler evaluate [--input F] [--output F]  Read PolicyInput, write PolicyOutput (harness-neutral).
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
from buckler.core import evaluate

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


def _run_cursor_driver(args: argparse.Namespace) -> None:
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


def _run_evaluate(args: argparse.Namespace) -> None:
    policy_input = _load_json_from(getattr(args, "input", None))
    policy_output = evaluate(policy_input)
    _write_json_to(getattr(args, "output", None), policy_output)


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
        "--input", "-i", default=None, metavar="FILE", help="PolicyInput JSON file (default: stdin)"
    )
    eval_p.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="PolicyOutput JSON file (default: stdout)",
    )

    args = parser.parse_args()

    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    if args.subcommand == "evaluate":
        _run_evaluate(args)
    elif args.driver == "cursor":
        _run_cursor_driver(args)
    else:
        log.error("Unknown driver: %s", args.driver)
        sys.exit(1)


if __name__ == "__main__":
    main()
