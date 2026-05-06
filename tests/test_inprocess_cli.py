"""In-process CLI and module tests for coverage of cli.py, hooks.py main(),
and remaining branch lines in core.py / pack_loader.py / hooks.py.

Subprocess calls in test_coverage_gaps.py don't contribute to coverage;
these tests call module code directly within the pytest process.
"""

from __future__ import annotations

import json
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).parent.parent


# ══════════════════════════════════════════════════════════════════════════════
# cli.py — tested in-process via main() with mocked sys.argv / sys.stdin
# ══════════════════════════════════════════════════════════════════════════════

def _call_main(argv: list[str], stdin_json: dict | None = None, env: dict | None = None):
    """Call buckler.cli.main() in-process with captured stdout."""
    from buckler.cli import main

    stdin_text = json.dumps(stdin_json) if stdin_json is not None else ""
    with mock.patch("sys.argv", ["buckler"] + argv), \
         mock.patch("sys.stdin", StringIO(stdin_text)), \
         mock.patch.dict("os.environ", env or {}):
        captured = StringIO()
        with mock.patch("sys.stdout", captured):
            try:
                main()
            except SystemExit:
                pass
        return captured.getvalue()


class TestCLIInProcess:
    def test_cursor_default_deny_commit(self):
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git commit -m 'test'",
            "cwd": "/project",
        }
        out = _call_main(["--driver", "cursor"], stdin_json=payload)
        data = json.loads(out)
        assert data["permission"] == "deny"

    def test_cursor_default_allow_benign(self):
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git status",
            "cwd": "/project",
        }
        out = _call_main([], stdin_json=payload)
        data = json.loads(out)
        assert data["permission"] == "allow"

    def test_cursor_bypass_env(self):
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git commit -m 'bypass'",
            "cwd": "/project",
        }
        out = _call_main([], stdin_json=payload, env={"RETHUNK_ALLOW_SHELL": "1"})
        data = json.loads(out)
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
        result = json.loads(out_file.read_text())
        assert result["decision"] == "deny"

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
        result = json.loads(captured.getvalue())
        assert result["decision"] == "allow"

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

    def test_main_module_callable(self):
        """buckler.__main__ delegates to cli.main — run via runpy to exercise if __name__ block."""
        import runpy
        payload = json.dumps({
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git status",
            "cwd": "/p",
        })
        with mock.patch("sys.argv", ["buckler"]), \
             mock.patch("sys.stdin", StringIO(payload)), \
             mock.patch("sys.stdout", StringIO()):
            # run_module with run_name="__main__" triggers the if __name__ == "__main__": branch
            runpy.run_module("buckler", run_name="__main__", alter_sys=True)

    def test_unknown_driver_exits(self):
        """An unknown --driver value logs an error and exits 1."""
        payload = {
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git status",
            "cwd": "/p",
        }
        from buckler.cli import main
        with mock.patch("sys.argv", ["buckler", "--driver", "cursor"]), \
             mock.patch("sys.stdin", StringIO(json.dumps(payload))), \
             mock.patch("sys.stdout", StringIO()):
            # Force the driver branch to "not cursor" after args parse by patching args.driver
            with mock.patch("buckler.cli.argparse.Namespace.driver", "unknown_driver",
                            create=True):
                # Simpler: just override args after parse
                pass
        # Direct test via monkeypatching the decision branch
        from buckler import cli
        with mock.patch.object(cli, "_run_cursor_driver"):
            # Patch argparse to return args.driver="someother"
            fake_args = mock.Mock()
            fake_args.subcommand = None
            fake_args.driver = "notcursor"
            fake_args.version = False
            with mock.patch("buckler.cli.argparse") as mock_ap:
                mock_parser = mock.Mock()
                mock_ap.ArgumentParser.return_value = mock_parser
                mock_parser.parse_args.return_value = fake_args
                mock_ap.Namespace = mock.Mock
                with pytest.raises(SystemExit) as exc_info:
                    cli.main()
            assert exc_info.value.code == 1

    def test_cli_if_name_main_guard(self):
        """cli.py if __name__ == '__main__': guard runs via runpy."""
        import runpy
        payload = json.dumps({
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git status",
            "cwd": "/p",
        })
        with mock.patch("sys.argv", ["buckler"]), \
             mock.patch("sys.stdin", StringIO(payload)), \
             mock.patch("sys.stdout", StringIO()):
            runpy.run_module("buckler.cli", run_name="__main__", alter_sys=True)


# ══════════════════════════════════════════════════════════════════════════════
# hooks.py — main() called in-process
# ══════════════════════════════════════════════════════════════════════════════

class TestHooksMainInProcess:
    def test_hooks_main_merge(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import main
        with mock.patch("sys.argv", [
            "buckler.hooks", "merge",
            "--hooks-json", str(hooks_json),
            "--venv-python", sys.executable,
        ]):
            main()
        data = json.loads(hooks_json.read_text())
        assert any(h["name"].startswith("buckler:") for h in data["hooks"])

    def test_hooks_main_strip(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [
            {"name": "buckler:pre-shell-exec", "event": "beforeShellExecution", "command": "x"}
        ]}))
        from buckler.hooks import main
        with mock.patch("sys.argv", ["buckler.hooks", "strip", "--hooks-json", str(hooks_json)]):
            main()
        data = json.loads(hooks_json.read_text())
        assert not any(h["name"].startswith("buckler:") for h in data["hooks"])

    def test_hooks_main_status(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        from buckler.hooks import main
        with mock.patch("sys.argv", ["buckler.hooks", "status", "--hooks-json", str(hooks_json)]):
            main()
        out = capsys.readouterr().out
        assert "No Buckler hooks" in out

    def test_hooks_main_no_subcommand(self, capsys: pytest.CaptureFixture):
        from buckler.hooks import main
        with mock.patch("sys.argv", ["buckler.hooks"]):
            main()
        combined = capsys.readouterr()
        assert "merge" in combined.out or "merge" in combined.err

    def test_hooks_if_name_main_guard(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        """hooks.py if __name__ == '__main__': guard runs via runpy."""
        import runpy
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        with mock.patch("sys.argv", ["buckler.hooks", "status", "--hooks-json", str(hooks_json)]):
            runpy.run_module("buckler.hooks", run_name="__main__", alter_sys=True)
        out = capsys.readouterr().out
        assert "No Buckler hooks" in out

    def test_hooks_main_merge_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import main
        with mock.patch("sys.argv", [
            "buckler.hooks", "merge",
            "--hooks-json", str(hooks_json),
            "--dry-run",
        ]):
            main()
        out = capsys.readouterr().out
        parsed = json.loads(out)
        assert any(h["name"].startswith("buckler:") for h in parsed["hooks"])

    def test_hooks_main_strip_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [
            {"name": "buckler:post-tool", "event": "postToolUse", "command": "x"}
        ]}))
        from buckler.hooks import main
        with mock.patch("sys.argv", [
            "buckler.hooks", "strip",
            "--hooks-json", str(hooks_json),
            "--dry-run",
        ]):
            main()
        out = capsys.readouterr().out
        assert "Would remove" in out

    def test_buckler_command_with_venv_python(self, tmp_path: Path):
        """_buckler_command(venv_python) hits the explicit venv_python branch."""
        from buckler.hooks import _buckler_command
        result = _buckler_command(venv_python=Path(sys.executable))
        assert sys.executable in result
        assert "--driver cursor" in result

    def test_buckler_command_current_dir_with_venv(self, tmp_path: Path):
        """_buckler_command() with current_dir set and .venv/bin/python present."""
        py = tmp_path / ".venv" / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.write_text("#!/usr/bin/env python3")
        py.chmod(0o755)
        with mock.patch("buckler.hooks.paths.current_dir", return_value=tmp_path):
            from buckler.hooks import _buckler_command
            result = _buckler_command()
        assert str(py) in result

    def test_read_hooks_json_invalid_json(self, tmp_path: Path):
        """_read_hooks_json returns {} when file contains bad JSON."""
        bad = tmp_path / "hooks.json"
        bad.write_text("not json")
        from buckler.hooks import _read_hooks_json
        result = _read_hooks_json(bad)
        assert result == {}


# ══════════════════════════════════════════════════════════════════════════════
# core.py remaining branches
# ══════════════════════════════════════════════════════════════════════════════

class TestCoreRemainingBranches:
    def test_match_tool_name_specified_and_matches(self):
        """_match_tool_name returns True when spec matches tool_name."""
        from buckler.core import _match_tool_name
        assert _match_tool_name({"tool_name": "Shell"}, "Shell") is True

    def test_match_tool_name_specified_no_match(self):
        from buckler.core import _match_tool_name
        assert _match_tool_name({"tool_name": "Shell"}, "Edit") is False

    def test_matches_shell_segments_empty_command(self):
        """When shell_segments in match but command is empty, rule does not fire."""
        from buckler.core import _matches
        rule = {
            "id": "r", "pack": "p", "source": "s",
            "trigger": ["pre_shell_exec"],
            "match": {"shell_segments": [{"program": "git"}]},
            "action": "deny", "priority": 100, "tier": "baseline",
            "user_message": None, "agent_message": None, "additional_context": None,
            "enabled": True,
        }
        inp = {"policy_io_version": "1", "trigger": "pre_shell_exec",
               "shell": {"command": ""}, "tool": None, "env": {}}
        assert _matches(rule, inp) is False

    def test_action_priority_unknown(self):
        from buckler.core import _action_priority
        assert _action_priority("unknown_action") == 0

    def test_evaluate_rule_priority_tie_higher_severity_wins(self):
        """When two rules tie on priority, higher-severity action wins."""
        from buckler.core import evaluate
        # `git add` matches both warn-git-add (priority 50, nudge) and any allow rule (priority <50)
        # The nudge should win over any lower-priority allow
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git add ."},
            "env": {},
        }
        result = evaluate(inp)
        assert result["decision"] == "nudge"

    def test_match_shell_segments_continue_on_none_program(self):
        """Segments that parse to (None, ...) are skipped without error."""
        from buckler.core import _match_shell_segments
        # Command with an unclosed quote after a good segment
        # First segment "git commit" should match, despite second being malformed
        result = _match_shell_segments(
            {"shell_segments": [{"program": "git", "subcommand": "commit"}]},
            "git commit && 'unclosed",
        )
        assert result is True

    def test_evaluate_refspec_delete_spec_no_match(self):
        """A rule with refspec_delete:true but no : refspec → not triggered."""
        from buckler.core import evaluate
        # Normal push without : refspec — deny-git-push-refspec-delete should NOT fire
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git push origin main"},
            "env": {},
        }
        result = evaluate(inp)
        assert result["decision"] == "allow"

    def test_match_segments_none_program_continue_line(self):
        """Line 158: continue fires when a trailing segment has program=None.

        Segment 1 (echo) does not match spec (git) → outer loop continues.
        Segment 2 ('unclosed) → shlex ValueError → program=None → line 158 continue fires.
        Neither segment matches, so result is False.
        """
        from buckler.core import _match_shell_segments
        result = _match_shell_segments(
            {"shell_segments": [{"program": "git"}]},
            "echo hello && 'unclosed",
        )
        assert result is False

    def test_evaluate_priority_tie_higher_severity_wins(self, tmp_path: Path):
        """Line 269: two rules match at same priority; higher-severity action wins.

        Secondary sort key is action name ascending (alphabetical), so 'allow' sorts
        before 'ask'. Both match; the 'ask' rule must displace 'allow' via line 269.
        """
        from buckler.core import evaluate
        from buckler import pack_loader

        pack_yaml = tmp_path / "tie.yaml"
        pack_yaml.write_text(
            "pack: tie-test\nversion: '1'\nrules:\n"
            # 'allow' sorts before 'ask' alphabetically → allow is best_rule first (line 262)
            "  - id: r-allow\n    trigger: pre_shell_exec\n    action: allow\n"
            "    priority: 50\n    match:\n      shell_segments:\n        - program: ls\n"
            "    user_message: null\n    agent_message: null\n\n"
            # 'ask' has higher severity (3 > 1) → should displace allow via line 269
            "  - id: r-ask\n    trigger: pre_shell_exec\n    action: ask\n"
            "    priority: 50\n    match:\n      shell_segments:\n        - program: ls\n"
            "    user_message: 'Confirm?'\n    agent_message: null\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "nope"):
            rules = pack_loader.load_packs()

        with mock.patch("buckler.core.load_packs", return_value=rules), \
             mock.patch("buckler.core.load_config", return_value={"core": {"tier": "baseline"}}):
            inp = {
                "policy_io_version": "1",
                "trigger": "pre_shell_exec",
                "shell": {"command": "ls -la"},
                "env": {},
            }
            result = evaluate(inp)
        # ask (severity 3) beats allow (severity 1) at same priority via line 269
        assert result["decision"] == "ask"


# ══════════════════════════════════════════════════════════════════════════════
# pack_loader.py remaining branches
# ══════════════════════════════════════════════════════════════════════════════

class TestPackLoaderRemainingBranches:
    def test_invalid_tier_value(self, tmp_path: Path):
        """A rule with an invalid tier value is skipped with a warning."""
        pack = tmp_path / "bad_tier.yaml"
        pack.write_text(
            "pack: test\nversion: '1'\nrules:\n"
            "  - id: r1\n    trigger: pre_shell_exec\n    action: deny\n    tier: extreme\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "nope"):
            from buckler.pack_loader import load_packs
            rules = load_packs()
            assert not any(r["id"] == "r1" for r in rules)

    def test_missing_action(self, tmp_path: Path):
        """A rule missing 'action' is skipped."""
        pack = tmp_path / "no_action.yaml"
        pack.write_text(
            "pack: test\nversion: '1'\nrules:\n"
            "  - id: r1\n    trigger: pre_shell_exec\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "nope"):
            from buckler.pack_loader import load_packs
            rules = load_packs()
            assert not any(r["id"] == "r1" for r in rules)

    def test_user_rules_dir_yaml_error(self, tmp_path: Path):
        """A malformed YAML in user rules.d is skipped gracefully."""
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "bad.yaml").write_text("pack: bad\n  invalid: [unclosed")
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "no_packs"), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d):
            from buckler.pack_loader import load_packs
            load_packs()  # must not raise

    def test_load_config_with_tomllib(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """load_config() reads config.toml via tomllib and merges into defaults."""
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_text("[core]\ntier = \"strict\"\naudit_log = true\n")
        from buckler.pack_loader import load_config
        cfg = load_config()
        assert cfg["core"]["tier"] == "strict"
        assert cfg["core"]["audit_log"] is True

    def test_load_config_parse_error(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """load_config() falls back to defaults when config.toml has a parse error."""
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        # Write invalid TOML (binary open mode will reject non-bytes)
        bad = tmp_path / "config.toml"
        bad.write_bytes(b"\xff\xfe bad toml content \x00")
        from buckler.pack_loader import load_config
        cfg = load_config()
        assert cfg["core"]["tier"] == "baseline"


# ══════════════════════════════════════════════════════════════════════════════
# paths.py remaining: line 77 (Windows current_dir: current.json absent)
# ══════════════════════════════════════════════════════════════════════════════

class TestPathsRemainingBranch:
    def test_current_dir_windows_no_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Windows current_dir returns None when current.json is absent."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        # tmp_path has no current.json — expect None
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            result = paths.current_dir()
        assert result is None
