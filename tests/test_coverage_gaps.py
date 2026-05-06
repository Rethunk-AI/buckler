"""Targeted tests to bring per-module coverage to ≥80%.

Focuses on paths that were untouched: cli.py (0%), hooks.py (0%),
plus Windows branches, error paths, and edge cases in core/paths/adapters/pack_loader.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from io import StringIO
from pathlib import Path
from unittest import mock

import pytest

REPO_ROOT = Path(__file__).parent.parent
PYTHON = sys.executable


# ══════════════════════════════════════════════════════════════════════════════
# paths.py
# ══════════════════════════════════════════════════════════════════════════════

class TestPaths:
    def test_env_or_returns_from_env(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path / "custom"))
        from buckler import paths
        assert paths.data_dir() == tmp_path / "custom"

    def test_xdg_data_home_used(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.delenv("BUCKLER_DATA_HOME", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "xdg"))
        from buckler import paths
        assert paths.data_dir() == tmp_path / "xdg" / "buckler"

    def test_config_dir_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.delenv("BUCKLER_CONFIG_HOME", raising=False)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        from buckler import paths
        assert paths.config_dir() == tmp_path / "cfg" / "buckler"

    def test_state_dir_xdg(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.delenv("BUCKLER_STATE_HOME", raising=False)
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        from buckler import paths
        assert paths.state_dir() == tmp_path / "state" / "buckler"

    def test_data_dir_windows(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.delenv("BUCKLER_DATA_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            result = paths.data_dir()
        assert result == tmp_path / "local" / "Buckler"

    def test_config_dir_windows(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.delenv("BUCKLER_CONFIG_HOME", raising=False)
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            result = paths.config_dir()
        assert result == tmp_path / "roaming" / "Buckler"

    def test_state_dir_windows(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.delenv("BUCKLER_STATE_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            result = paths.state_dir()
        assert result == tmp_path / "local" / "Buckler" / "state"

    def test_current_dir_unix_symlink(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        ver_dir = tmp_path / "versions" / "0.1.0"
        ver_dir.mkdir(parents=True)
        current = tmp_path / "current"
        current.symlink_to(ver_dir)
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths
            result = paths.current_dir()
        assert result == ver_dir.resolve()

    def test_current_dir_unix_missing(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths
            assert paths.current_dir() is None

    def test_current_dir_windows_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        ver_dir = tmp_path / "versions" / "0.1.0"
        ver_dir.mkdir(parents=True)
        current_json = tmp_path / "current.json"
        current_json.write_text(json.dumps({"version": "0.1.0", "path": str(ver_dir)}))
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            result = paths.current_dir()
        assert result == ver_dir

    def test_current_dir_windows_bad_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        (tmp_path / "current.json").write_text("not json")
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            assert paths.current_dir() is None

    def test_current_dir_windows_missing_key(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        (tmp_path / "current.json").write_text(json.dumps({"version": "0.1.0"}))
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths
            assert paths.current_dir() is None

    def test_packs_dir_with_current(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        ver_dir = tmp_path / "versions" / "0.1.0"
        (ver_dir / "packs").mkdir(parents=True)
        with mock.patch("buckler.paths.current_dir", return_value=ver_dir):
            from buckler import paths
            assert paths.packs_dir() == ver_dir / "packs"

    def test_packs_dir_dev_fallback(self):
        with mock.patch("buckler.paths.current_dir", return_value=None):
            from buckler import paths
            result = paths.packs_dir()
            assert result.name == "packs"

    def test_user_rules_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        from buckler import paths
        assert paths.user_rules_dir() == tmp_path / "rules.d"

    def test_audit_log(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_STATE_HOME", str(tmp_path))
        from buckler import paths
        assert paths.audit_log() == tmp_path / "audit.log"

    def test_cursor_hooks_json(self):
        from buckler import paths
        result = paths.cursor_hooks_json()
        assert result.name == "hooks.json"
        assert ".cursor" in str(result)


# ══════════════════════════════════════════════════════════════════════════════
# core.py edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestCoreEdgeCases:
    def test_segment_double_quoted_boundary(self):
        from buckler.core import _segment_command
        # Boundary chars inside double quotes must not split
        segs = _segment_command('echo "hello && world"')
        assert len(segs) == 1

    def test_parse_segment_shlex_error(self):
        from buckler.core import _parse_segment
        # Unclosed quote → shlex ValueError → (None, None, [])
        result = _parse_segment("git commit -m 'unclosed")
        assert result == (None, None, [])

    def test_parse_segment_empty_after_shlex(self):
        from buckler.core import _parse_segment
        result = _parse_segment("")
        assert result == (None, None, [])

    def test_parse_segment_git_global_flag(self):
        from buckler.core import _parse_segment
        # --bare is a global flag that should be skipped
        program, sub, flags = _parse_segment("git --bare commit -m 'x'")
        assert program == "git"
        assert sub == "commit"

    def test_parse_segment_git_global_opt_with_arg(self):
        from buckler.core import _parse_segment
        # -C takes an argument, both should be skipped before subcommand
        program, sub, flags = _parse_segment("git -C /path commit -m 'x'")
        assert program == "git"
        assert sub == "commit"

    def test_parse_segment_git_double_dash(self):
        from buckler.core import _parse_segment
        # -- stops global option parsing; next token is NOT a subcommand here
        program, sub, flags = _parse_segment("git -- commit")
        assert program == "git"
        # After --, commit is treated as a file path, not subcommand
        assert sub is None

    def test_push_has_delete_refspec_bad_quote(self):
        from buckler.core import _push_has_delete_refspec
        # Unclosed quote → shlex ValueError → returns False
        assert _push_has_delete_refspec("git push 'unclosed") is False

    def test_push_has_delete_refspec_detected(self):
        from buckler.core import _push_has_delete_refspec
        assert _push_has_delete_refspec("git push origin :my-branch") is True

    def test_push_has_delete_refspec_double_colon(self):
        from buckler.core import _push_has_delete_refspec
        # ::something should NOT be treated as a delete refspec
        assert _push_has_delete_refspec("git push origin ::refs") is False

    def test_match_no_shell_segments_constraint(self):
        """Rule with no shell_segments match is unconstrained on that field."""
        from buckler.core import _match_shell_segments
        # Empty segment_specs → always True
        assert _match_shell_segments({}, "git commit -m x") is True
        assert _match_shell_segments({}, "") is True

    def test_match_program_none_skipped(self):
        """Segments that fail to parse (program=None) are skipped."""
        from buckler.core import _match_shell_segments
        # Unclosed quote produces a None-program segment; no match
        result = _match_shell_segments(
            {"shell_segments": [{"program": "git"}]},
            "git commit && 'unclosed",
        )
        # The first segment matches (git commit), so True
        assert result is True

    def test_evaluate_post_tool_failure_trigger(self):
        """post_tool_failure trigger fires post-tool nudge rules."""
        from buckler.core import evaluate
        inp = {
            "policy_io_version": "1",
            "trigger": "post_tool_failure",
            "shell": {"command": "git push", "cwd": "/p"},
            "tool": {"name": "Shell", "input": {"command": "git push"}, "output": {}},
            "session": None,
            "env": {},
        }
        result = evaluate(inp)
        # No post_tool_failure rule in agent-git, so allow
        assert result["decision"] in ("allow", "nudge")

    def test_evaluate_allow_no_matching_rule(self):
        """Commands with no matching rule return allow."""
        from buckler.core import evaluate
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "make test", "cwd": "/p"},
            "env": {},
        }
        result = evaluate(inp)
        assert result["decision"] == "allow"
        assert result["user_message"] is None

    def test_evaluate_env_only_match(self):
        """A rule matching only on env (bypass) fires with RETHUNK_ALLOW_SHELL=1."""
        from buckler.core import evaluate
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git commit -m 'x'", "cwd": "/p"},
            "env": {"RETHUNK_ALLOW_SHELL": "1"},
        }
        result = evaluate(inp)
        assert result["decision"] == "allow"

    def test_evaluate_refspec_delete_detected(self):
        """git push with :branch refspec is denied."""
        from buckler.core import evaluate
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git push origin :my-branch", "cwd": "/p"},
            "env": {},
        }
        result = evaluate(inp)
        assert result["decision"] == "deny"


# ══════════════════════════════════════════════════════════════════════════════
# adapters/cursor.py edge cases
# ══════════════════════════════════════════════════════════════════════════════

class TestCursorAdapterEdgeCases:
    def test_adapt_input_unknown_event(self):
        from buckler.adapters.cursor import adapt_input
        raw = {"hook_event_name": "unknownEvent", "cwd": "/p"}
        pi = adapt_input(raw)
        assert pi["trigger"] == "post_tool_success"

    def test_adapt_output_ask(self):
        from buckler.adapters.cursor import adapt_output
        output = {
            "policy_io_version": "1",
            "decision": "ask",
            "user_message": "Confirm?",
            "agent_message": "Please confirm.",
            "additional_context": None,
            "updated_tool_input": None,
        }
        result = adapt_output(output, {"hook_event_name": "beforeShellExecution"})
        assert result["permission"] == "ask"
        assert result["message"] == "Confirm?"
        assert result["agent_message"] == "Please confirm."

    def test_adapt_output_nudge_on_pre_hook_with_messages(self):
        from buckler.adapters.cursor import adapt_output
        output = {
            "policy_io_version": "1",
            "decision": "nudge",
            "user_message": "Consider MCP.",
            "agent_message": "Use batch_commit.",
            "additional_context": None,
            "updated_tool_input": None,
        }
        result = adapt_output(output, {"hook_event_name": "preToolUse"})
        # Nudge on pre-hook → allow + messages
        assert result["permission"] == "allow"
        assert result["message"] == "Consider MCP."
        assert result["agent_message"] == "Use batch_commit."

    def test_adapt_output_post_tool_no_context(self):
        from buckler.adapters.cursor import adapt_output
        output = {
            "policy_io_version": "1",
            "decision": "allow",
            "user_message": None,
            "agent_message": None,
            "additional_context": None,
            "updated_tool_input": None,
        }
        result = adapt_output(output, {"hook_event_name": "postToolUse"})
        assert result == {}

    def test_adapt_input_pre_tool_non_shell(self):
        from buckler.adapters.cursor import adapt_input
        raw = {
            "hook_event_name": "preToolUse",
            "tool_name": "Edit",
            "tool_input": {"path": "/file.py"},
            "cwd": "/p",
            "workspace_root": "/p",
        }
        pi = adapt_input(raw)
        assert pi["trigger"] == "pre_shell_tool"
        assert pi["tool"]["name"] == "Edit"
        assert pi["shell"] is None  # non-Shell tool → no shell field

    def test_adapt_input_workspace_from_cwd(self):
        from buckler.adapters.cursor import adapt_input
        raw = {"hook_event_name": "beforeShellExecution", "shell_command": "ls", "cwd": "/myproject"}
        pi = adapt_input(raw)
        assert pi["session"]["workspace_roots"] == ["/myproject"]


# ══════════════════════════════════════════════════════════════════════════════
# pack_loader.py error paths
# ══════════════════════════════════════════════════════════════════════════════

class TestPackLoaderErrorPaths:
    def test_missing_rule_id(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        pack = tmp_path / "bad.yaml"
        pack.write_text("pack: test\nversion: '1'\nrules:\n  - trigger: pre_shell_exec\n    action: deny\n")
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path / "data"))
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rules.d"):
            from buckler.pack_loader import load_packs
            # Bad rule is skipped; load completes without exception
            rules = load_packs()
            assert all(r["id"] != "" for r in rules)

    def test_missing_trigger(self, tmp_path: Path):
        pack = tmp_path / "bad.yaml"
        pack.write_text("pack: test\nversion: '1'\nrules:\n  - id: r1\n    action: deny\n")
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rules.d"):
            from buckler.pack_loader import load_packs
            rules = load_packs()
            assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_trigger_value(self, tmp_path: Path):
        pack = tmp_path / "bad.yaml"
        pack.write_text(
            "pack: test\nversion: '1'\nrules:\n  - id: r1\n    trigger: bad_trigger\n    action: deny\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rules.d"):
            from buckler.pack_loader import load_packs
            rules = load_packs()
            assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_action_value(self, tmp_path: Path):
        pack = tmp_path / "bad.yaml"
        pack.write_text(
            "pack: test\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n    action: explode\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rules.d"):
            from buckler.pack_loader import load_packs
            rules = load_packs()
            assert not any(r["id"] == "r1" for r in rules)

    def test_yaml_parse_error(self, tmp_path: Path):
        pack = tmp_path / "bad.yaml"
        pack.write_text("pack: test\n  bad: [unclosed")
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rules.d"):
            from buckler.pack_loader import load_packs
            # Should not raise; bad file is skipped
            load_packs()

    def test_user_rules_loaded(self, tmp_path: Path):
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "my.yaml").write_text(
            "pack: my\nversion: '1'\nrules:\n"
            "  - id: allow-all\n    trigger: pre_shell_exec\n    action: allow\n    priority: 5\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "empty_packs"), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d):
            from buckler.pack_loader import load_packs
            rules = load_packs()
            assert any(r["id"] == "allow-all" for r in rules)

    def test_load_config_missing_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path / "nonexistent"))
        from buckler.pack_loader import load_config
        cfg = load_config()
        assert cfg["core"]["tier"] == "baseline"

    def test_load_config_reads_tier(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_text("[core]\ntier = \"strict\"\n")
        from buckler.pack_loader import load_config
        cfg = load_config()
        assert cfg["core"]["tier"] == "strict"


# ══════════════════════════════════════════════════════════════════════════════
# hooks.py (0% → covered)
# ══════════════════════════════════════════════════════════════════════════════

class TestHooks:
    def test_merge_creates_hooks_json(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        data = json.loads(hooks_json.read_text())
        names = [h["name"] for h in data["hooks"]]
        assert "buckler:pre-shell-exec" in names
        assert "buckler:pre-shell-tool" in names
        assert "buckler:post-tool" in names

    def test_merge_is_idempotent(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        data = json.loads(hooks_json.read_text())
        buckler_hooks = [h for h in data["hooks"] if h["name"].startswith("buckler:")]
        assert len(buckler_hooks) == 3  # exactly one copy of each

    def test_merge_preserves_existing_hooks(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [{"name": "other-tool", "event": "postToolUse"}]}))
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        data = json.loads(hooks_json.read_text())
        names = [h["name"] for h in data["hooks"]]
        assert "other-tool" in names
        assert "buckler:pre-shell-exec" in names

    def test_strip_removes_buckler_entries(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge, strip
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        strip(hooks_path=hooks_json)
        data = json.loads(hooks_json.read_text())
        buckler_hooks = [h for h in data["hooks"] if h["name"].startswith("buckler:")]
        assert len(buckler_hooks) == 0

    def test_strip_preserves_other_entries(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({
            "hooks": [
                {"name": "buckler:pre-shell-exec", "event": "beforeShellExecution", "command": "x"},
                {"name": "other-tool", "event": "postToolUse"},
            ]
        }))
        from buckler.hooks import strip
        strip(hooks_path=hooks_json)
        data = json.loads(hooks_json.read_text())
        names = [h["name"] for h in data["hooks"]]
        assert "other-tool" in names
        assert "buckler:pre-shell-exec" not in names

    def test_merge_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON), dry_run=True)
        captured = capsys.readouterr()
        parsed = json.loads(captured.out)
        assert any(h["name"].startswith("buckler:") for h in parsed["hooks"])
        assert not hooks_json.exists()  # dry_run should not write

    def test_strip_dry_run(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({
            "hooks": [{"name": "buckler:pre-shell-exec", "event": "beforeShellExecution", "command": "x"}]
        }))
        from buckler.hooks import strip
        strip(hooks_path=hooks_json, dry_run=True)
        captured = capsys.readouterr()
        assert "Would remove" in captured.out
        # File unchanged
        data = json.loads(hooks_json.read_text())
        assert len(data["hooks"]) == 1

    def test_status_with_hooks(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge, status
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        status(hooks_path=hooks_json)
        out = capsys.readouterr().out
        assert "buckler:pre-shell-exec" in out

    def test_status_no_hooks(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        from buckler.hooks import status
        status(hooks_path=hooks_json)
        out = capsys.readouterr().out
        assert "No Buckler hooks" in out

    def test_merge_missing_venv_python_falls_back(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        # No venv_python; should still work using current_dir or sys.executable fallback
        merge(hooks_path=hooks_json)
        data = json.loads(hooks_json.read_text())
        assert any(h["name"].startswith("buckler:") for h in data["hooks"])


# ══════════════════════════════════════════════════════════════════════════════
# cli.py (0% → covered via subprocess)
# ══════════════════════════════════════════════════════════════════════════════

def _run_cli(stdin_data: str, args: list[str] | None = None, env: dict | None = None) -> subprocess.CompletedProcess:
    cmd = [PYTHON, "-m", "buckler"] + (args or [])
    merged_env = {**os.environ, **(env or {})}
    return subprocess.run(
        cmd,
        input=stdin_data,
        capture_output=True,
        text=True,
        env=merged_env,
        cwd=REPO_ROOT,
    )


class TestCLI:
    def test_version(self):
        result = subprocess.run(
            [PYTHON, "-m", "buckler", "--version"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0
        assert "buckler" in result.stdout

    def test_cursor_driver_deny_commit(self):
        payload = json.dumps({
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git commit -m 'test'",
            "cwd": "/project",
            "workspace_root": "/project",
        })
        result = _run_cli(payload, ["--driver", "cursor"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["permission"] == "deny"

    def test_cursor_driver_allow_benign(self):
        payload = json.dumps({
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git status",
            "cwd": "/project",
        })
        result = _run_cli(payload)
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["permission"] == "allow"

    def test_cursor_driver_bypass(self):
        payload = json.dumps({
            "hook_event_name": "beforeShellExecution",
            "shell_command": "git commit -m 'bypass'",
            "cwd": "/project",
        })
        result = _run_cli(payload, env={"RETHUNK_ALLOW_SHELL": "1"})
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["permission"] == "allow"

    def test_evaluate_subcommand_stdin(self):
        payload = json.dumps({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git commit -m 'x'", "cwd": "/p"},
            "env": {},
        })
        result = _run_cli(payload, ["evaluate"])
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["decision"] == "deny"
        assert data["policy_io_version"] == "1"

    def test_evaluate_to_file(self, tmp_path: Path):
        payload = json.dumps({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "ls -la", "cwd": "/p"},
            "env": {},
        })
        out_file = tmp_path / "out.json"
        inp_file = tmp_path / "in.json"
        inp_file.write_text(payload)
        result = subprocess.run(
            [PYTHON, "-m", "buckler", "evaluate", "--input", str(inp_file), "--output", str(out_file)],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0
        data = json.loads(out_file.read_text())
        assert data["decision"] == "allow"

    def test_hooks_merge_subcommand(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        result = subprocess.run(
            [PYTHON, "-m", "buckler.hooks", "merge",
             "--hooks-json", str(hooks_json),
             "--venv-python", PYTHON],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0
        data = json.loads(hooks_json.read_text())
        assert any(h["name"].startswith("buckler:") for h in data["hooks"])

    def test_hooks_status_subcommand(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        result = subprocess.run(
            [PYTHON, "-m", "buckler.hooks", "status", "--hooks-json", str(hooks_json)],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0
        assert "No Buckler hooks" in result.stdout

    def test_hooks_strip_subcommand(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        # First merge, then strip
        subprocess.run(
            [PYTHON, "-m", "buckler.hooks", "merge",
             "--hooks-json", str(hooks_json),
             "--venv-python", PYTHON],
            cwd=REPO_ROOT
        )
        result = subprocess.run(
            [PYTHON, "-m", "buckler.hooks", "strip", "--hooks-json", str(hooks_json)],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert result.returncode == 0
        data = json.loads(hooks_json.read_text())
        assert not any(h["name"].startswith("buckler:") for h in data["hooks"])

    def test_hooks_no_subcommand_prints_help(self):
        result = subprocess.run(
            [PYTHON, "-m", "buckler.hooks"],
            capture_output=True, text=True, cwd=REPO_ROOT
        )
        assert "merge" in result.stdout or "merge" in result.stderr
