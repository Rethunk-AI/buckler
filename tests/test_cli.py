"""Tests for buckler.cli — in-process CLI entry point."""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest


def _call_main(argv: list[str], stdin_json: dict | None = None, env: dict | None = None) -> str:
    """Call buckler.cli.main() in-process with captured stdout."""
    import contextlib
    from buckler.cli import main

    stdin_text = json.dumps(stdin_json) if stdin_json is not None else ""
    with mock.patch("sys.argv", ["buckler", *argv]), \
         mock.patch("sys.stdin", StringIO(stdin_text)), \
         mock.patch.dict("os.environ", env or {}):
        captured = StringIO()
        with mock.patch("sys.stdout", captured):
            with contextlib.suppress(SystemExit):
                main()
        return captured.getvalue()


class TestCLIInProcess:
    def test_cursor_default_deny_commit(self):
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git commit -m 'test'",
            "cwd": "/project",
        }
        data = json.loads(_call_main(["--driver", "cursor"], stdin_json=payload))
        assert data["permission"] == "deny"

    def test_cursor_default_allow_benign(self):
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git status",
            "cwd": "/project",
        }
        data = json.loads(_call_main([], stdin_json=payload))
        assert data["permission"] == "allow"

    def test_cursor_bypass_env(self):
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git commit -m 'bypass'",
            "cwd": "/project",
        }
        data = json.loads(_call_main([], stdin_json=payload, env={"RETHUNK_ALLOW_SHELL": "1"}))
        assert data["permission"] == "allow"

    def test_evaluate_subcommand_deny(self, tmp_path: Path):
        inp_file = tmp_path / "in.json"
        out_file = tmp_path / "out.json"
        inp_file.write_text(json.dumps({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git commit -m 'x'"},
            "env": {},
        }))
        from buckler.cli import main
        with mock.patch("sys.argv", ["buckler", "evaluate",
                                      "--input", str(inp_file),
                                      "--output", str(out_file)]):
            main()
        assert json.loads(out_file.read_text())["decision"] == "deny"

    def test_evaluate_subcommand_stdin_allow(self):
        payload = json.dumps({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "make test"},
            "env": {},
        })
        from buckler.cli import main
        with mock.patch("sys.argv", ["buckler", "evaluate"]), \
             mock.patch("sys.stdin", StringIO(payload)):
            captured = StringIO()
            with mock.patch("sys.stdout", captured):
                main()
        assert json.loads(captured.getvalue())["decision"] == "allow"

    def test_invalid_json_stdin_exits(self):
        from buckler.cli import main
        with mock.patch("sys.argv", ["buckler", "evaluate"]), \
             mock.patch("sys.stdin", StringIO("not json")), \
             pytest.raises(SystemExit):
            main()

    def test_version_flag(self):
        from buckler.cli import main
        with mock.patch("sys.argv", ["buckler", "--version"]), \
             pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    def test_unknown_driver_exits(self):
        """An unknown --driver value logs an error and exits 1."""
        from buckler import cli

        fake_args = mock.Mock()
        fake_args.subcommand = None
        fake_args.driver = "notcursor"
        fake_args.version = False
        with mock.patch.object(cli, "_run_cursor_driver"), \
             mock.patch("buckler.cli.argparse") as mock_ap:
            mock_parser = mock.Mock()
            mock_ap.ArgumentParser.return_value = mock_parser
            mock_parser.parse_args.return_value = fake_args
            mock_ap.Namespace = mock.Mock
            with pytest.raises(SystemExit) as exc_info:
                cli.main()
        assert exc_info.value.code == 1
