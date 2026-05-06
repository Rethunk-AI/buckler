"""Behavioral and edge-case tests for paths, core internals, cursor adapter,
pack loader error handling, and hooks API.

Scope: unit tests for self-contained features + golden-path integration
checks not already covered by test_core.py / test_agent_git.py.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

PYTHON = sys.executable


# ══════════════════════════════════════════════════════════════════════════════
# paths.py
# ══════════════════════════════════════════════════════════════════════════════


class TestPaths:
    def test_buckler_data_home_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """BUCKLER_DATA_HOME overrides every other path source."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path / "custom"))
        from buckler import paths

        assert paths.data_dir() == tmp_path / "custom"

    def test_xdg_vars_respected(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """XDG_DATA/CONFIG/STATE_HOME are all honoured as fallbacks."""
        monkeypatch.delenv("BUCKLER_DATA_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_CONFIG_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_STATE_HOME", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        from buckler import paths

        assert paths.data_dir() == tmp_path / "data" / "buckler"
        assert paths.config_dir() == tmp_path / "cfg" / "buckler"
        assert paths.state_dir() == tmp_path / "state" / "buckler"

    def test_windows_paths_use_appdata(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """On Windows, LOCALAPPDATA/APPDATA env vars drive all three dir functions."""
        monkeypatch.delenv("BUCKLER_DATA_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_CONFIG_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_STATE_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.data_dir() == tmp_path / "local" / "Buckler"
            assert paths.config_dir() == tmp_path / "roaming" / "Buckler"
            assert paths.state_dir() == tmp_path / "local" / "Buckler" / "state"

    def test_current_dir_unix_follows_symlink(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Unix: current_dir() resolves the current symlink to the installed version."""
        ver_dir = tmp_path / "versions" / "0.1.0"
        ver_dir.mkdir(parents=True)
        (tmp_path / "current").symlink_to(ver_dir)
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.current_dir() == ver_dir.resolve()

    def test_current_dir_unix_returns_none_when_absent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """Unix: current_dir() returns None when no symlink exists (dev environment)."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.current_dir() is None

    def test_current_dir_windows_reads_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Windows: current_dir() reads current.json and returns the path it contains."""
        ver_dir = tmp_path / "versions" / "0.1.0"
        ver_dir.mkdir(parents=True)
        (tmp_path / "current.json").write_text(json.dumps({"path": str(ver_dir)}))
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.current_dir() == ver_dir

    def test_current_dir_windows_error_recovery(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """Windows: bad/missing JSON in current.json returns None rather than raising."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            # No current.json at all
            assert paths.current_dir() is None

            # Malformed JSON
            (tmp_path / "current.json").write_text("not json")
            assert paths.current_dir() is None

            # Valid JSON but missing 'path' key
            (tmp_path / "current.json").write_text(json.dumps({"version": "0.1.0"}))
            assert paths.current_dir() is None

    def test_packs_dir_prefers_installed_location(self, tmp_path: Path):
        """packs_dir() returns <current>/packs when an installed version is active."""
        ver_dir = tmp_path / "versions" / "0.1.0"
        (ver_dir / "packs").mkdir(parents=True)
        with mock.patch("buckler.paths.current_dir", return_value=ver_dir):
            from buckler import paths

            assert paths.packs_dir() == ver_dir / "packs"

    def test_audit_log_is_inside_state_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """audit_log() must be a child of state_dir() named audit.log."""
        monkeypatch.setenv("BUCKLER_STATE_HOME", str(tmp_path))
        from buckler import paths

        assert paths.audit_log() == tmp_path / "audit.log"

    def test_cursor_hooks_json_path(self):
        """cursor_hooks_json() must point at ~/.cursor/hooks.json."""
        from buckler import paths

        assert paths.cursor_hooks_json() == Path.home() / ".cursor" / "hooks.json"


# ══════════════════════════════════════════════════════════════════════════════
# core.py edge cases
# ══════════════════════════════════════════════════════════════════════════════


class TestCoreEdgeCases:
    def test_segment_double_quoted_boundary(self):
        """&& inside double quotes must NOT split the command into two segments."""
        from buckler.core import _segment_command

        assert len(_segment_command('echo "hello && world"')) == 1

    def test_parse_segment_shlex_error(self):
        """Unclosed quote causes shlex.ValueError → graceful (None, None, [])."""
        from buckler.core import _parse_segment

        assert _parse_segment("git commit -m 'unclosed") == (None, None, [])

    def test_parse_segment_empty(self):
        from buckler.core import _parse_segment

        assert _parse_segment("") == (None, None, [])

    def test_parse_segment_git_global_options_skipped(self):
        """Git global flags (-C, --bare) before the subcommand are transparent."""
        from buckler.core import _parse_segment

        program, sub, _flags = _parse_segment("git --bare commit -m 'x'")
        assert (program, sub) == ("git", "commit")

        program, sub, _flags = _parse_segment("git -C /path commit -m 'x'")
        assert (program, sub) == ("git", "commit")

    def test_parse_segment_double_dash_stops_subcommand_search(self):
        """-- terminates global option parsing; the next token is not a subcommand."""
        from buckler.core import _parse_segment

        program, sub, _flags = _parse_segment("git -- commit")
        assert program == "git"
        assert sub is None

    def test_push_has_delete_refspec_double_colon_not_matched(self):
        """::something must NOT be treated as an implicit delete refspec."""
        from buckler.core import _push_has_delete_refspec

        assert _push_has_delete_refspec("git push origin ::refs") is False

    def test_push_has_delete_refspec_bad_quote_returns_false(self):
        """Unclosed quote in push command → shlex error → safe False, not an exception."""
        from buckler.core import _push_has_delete_refspec

        assert _push_has_delete_refspec("git push 'unclosed") is False

    def test_evaluate_allow_no_matching_rule(self):
        """Commands matching no rule are allowed (default-allow policy)."""
        from buckler.core import evaluate

        result = evaluate({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "make test", "cwd": "/p"},
            "env": {},
        })
        assert result["decision"] == "allow"
        assert result["user_message"] is None

    def test_evaluate_bypass_env_overrides_deny(self):
        """RETHUNK_ALLOW_SHELL=1 overrides even a deny rule."""
        from buckler.core import evaluate

        result = evaluate({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git commit -m 'x'", "cwd": "/p"},
            "env": {"RETHUNK_ALLOW_SHELL": "1"},
        })
        assert result["decision"] == "allow"

    def test_evaluate_refspec_delete_detected(self):
        """git push with :branch implicit-delete refspec is denied end-to-end."""
        from buckler.core import evaluate

        result = evaluate({
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git push origin :my-branch", "cwd": "/p"},
            "env": {},
        })
        assert result["decision"] == "deny"

    def test_malformed_segment_skipped_in_pipeline(self):
        """A malformed segment in a pipeline is silently skipped; evaluation continues."""
        from buckler.core import _match_shell_segments

        # echo → doesn't match git spec; 'unclosed → program=None → continue (not an error)
        result = _match_shell_segments(
            {"shell_segments": [{"program": "git"}]},
            "echo hello && 'unclosed",
        )
        assert result is False

    def test_match_shell_segments_no_constraint_always_true(self):
        """A match_cfg with no shell_segments key immediately returns True."""
        from buckler.core import _match_shell_segments

        assert _match_shell_segments({}, "git commit -m 'x'") is True
        assert _match_shell_segments({"env": {"X": "y"}}, "make test") is True


# ══════════════════════════════════════════════════════════════════════════════
# adapters/cursor.py
# ══════════════════════════════════════════════════════════════════════════════


class TestCursorAdapter:
    def test_unknown_event_falls_back_to_post_tool_success(self):
        """An unrecognised hook_event_name defaults to post_tool_success (allow path)."""
        from buckler.adapters.cursor import adapt_input

        pi = adapt_input({"hook_event_name": "unknownEvent", "cwd": "/p"})
        assert pi["trigger"] == "post_tool_success"

    def test_ask_decision_maps_to_cursor_ask(self):
        from buckler.adapters.cursor import adapt_output

        result = adapt_output(
            {
                "policy_io_version": "1",
                "decision": "ask",
                "user_message": "Confirm?",
                "agent_message": "Please confirm.",
                "additional_context": None,
                "updated_tool_input": None,
            },
            {"hook_event_name": "beforeShellExecution"},
        )
        assert result == {"permission": "ask", "message": "Confirm?",
                          "agent_message": "Please confirm."}

    def test_nudge_on_pre_hook_is_allow_with_messages(self):
        """Nudge on a pre-hook = allow + advisory messages (not a block)."""
        from buckler.adapters.cursor import adapt_output

        result = adapt_output(
            {
                "policy_io_version": "1",
                "decision": "nudge",
                "user_message": "Consider MCP.",
                "agent_message": "Use batch_commit.",
                "additional_context": None,
                "updated_tool_input": None,
            },
            {"hook_event_name": "preToolUse"},
        )
        assert result["permission"] == "allow"
        assert result["message"] == "Consider MCP."
        assert result["agent_message"] == "Use batch_commit."

    def test_allow_on_post_hook_returns_empty(self):
        """A plain allow on a post-hook emits an empty response (no-op)."""
        from buckler.adapters.cursor import adapt_output

        result = adapt_output(
            {
                "policy_io_version": "1",
                "decision": "allow",
                "user_message": None,
                "agent_message": None,
                "additional_context": None,
                "updated_tool_input": None,
            },
            {"hook_event_name": "postToolUse"},
        )
        assert result == {}

    def test_pre_tool_non_shell_has_no_shell_field(self):
        """A preToolUse event for a non-Shell tool produces trigger=pre_shell_tool, shell=None."""
        from buckler.adapters.cursor import adapt_input

        pi = adapt_input({
            "hook_event_name": "preToolUse",
            "tool_name": "Edit",
            "tool_input": {"path": "/file.py"},
            "cwd": "/p",
            "workspace_root": "/p",
        })
        assert pi["trigger"] == "pre_shell_tool"
        assert pi["tool"]["name"] == "Edit"
        assert pi["shell"] is None

    def test_workspace_root_from_cwd(self):
        """cwd is used as workspace_root when workspace_root key is absent."""
        from buckler.adapters.cursor import adapt_input

        pi = adapt_input({"hook_event_name": "beforeShellExecution",
                          "shell_command": "ls", "cwd": "/myproject"})
        assert pi["session"]["workspace_roots"] == ["/myproject"]


# ══════════════════════════════════════════════════════════════════════════════
# pack_loader.py error paths
# ══════════════════════════════════════════════════════════════════════════════


class TestPackLoaderValidation:
    """pack_loader silently skips invalid rules — verify each validation path."""

    def _load_with_pack(self, tmp_path: Path, yaml_text: str):
        (tmp_path / "p.yaml").write_text(yaml_text)
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rd"):
            from buckler.pack_loader import load_packs
            return load_packs()

    def test_missing_id_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path, "pack: t\nversion: '1'\nrules:\n  - trigger: pre_shell_exec\n    action: deny\n"
        )
        assert not any(r.get("id") == "" for r in rules)

    def test_missing_trigger_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path, "pack: t\nversion: '1'\nrules:\n  - id: r1\n    action: deny\n"
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_trigger_value_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: bad_trigger\n    action: deny\n",
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_missing_action_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path, "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n"
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_action_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n    action: explode\n",
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_tier_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n    action: deny\n    tier: extreme\n",
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_malformed_yaml_skipped(self, tmp_path: Path):
        """A pack file with invalid YAML is skipped; the rest of load_packs() succeeds."""
        self._load_with_pack(tmp_path, "pack: test\n  bad: [unclosed")  # must not raise

    def test_user_rules_loaded(self, tmp_path: Path):
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "my.yaml").write_text(
            "pack: my\nversion: '1'\nrules:\n"
            "  - id: allow-all\n    trigger: pre_shell_exec\n    action: allow\n    priority: 5\n"
        )
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "empty"), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d):
            from buckler.pack_loader import load_packs
            assert any(r["id"] == "allow-all" for r in load_packs())

    def test_user_rules_bad_yaml_skipped(self, tmp_path: Path):
        """Malformed YAML in rules.d is skipped without aborting load."""
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "bad.yaml").write_text("pack: bad\n  invalid: [unclosed")
        with mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "empty"), \
             mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d):
            from buckler.pack_loader import load_packs
            load_packs()  # must not raise


class TestLoadConfig:
    def test_defaults_when_file_missing(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path / "nonexistent"))
        from buckler.pack_loader import load_config
        assert load_config()["core"]["tier"] == "baseline"

    def test_reads_tier_from_toml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_text('[core]\ntier = "strict"\n')
        from buckler.pack_loader import load_config
        assert load_config()["core"]["tier"] == "strict"

    def test_falls_back_to_defaults_on_parse_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_bytes(b"\xff\xfe bad toml \x00")
        from buckler.pack_loader import load_config
        assert load_config()["core"]["tier"] == "baseline"


# ══════════════════════════════════════════════════════════════════════════════
# hooks.py
# ══════════════════════════════════════════════════════════════════════════════


class TestHooks:
    def test_merge_creates_all_three_entries(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        names = [h["name"] for h in json.loads(hooks_json.read_text())["hooks"]]
        assert {"buckler:pre-shell-exec", "buckler:pre-shell-tool", "buckler:post-tool"} <= set(names)

    def test_merge_is_idempotent(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        buckler = [h for h in json.loads(hooks_json.read_text())["hooks"]
                   if h["name"].startswith("buckler:")]
        assert len(buckler) == 3

    def test_merge_preserves_existing_hooks(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [{"name": "other-tool", "event": "x"}]}))
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        names = [h["name"] for h in json.loads(hooks_json.read_text())["hooks"]]
        assert "other-tool" in names and "buckler:pre-shell-exec" in names

    def test_strip_removes_buckler_preserves_others(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [
            {"name": "buckler:pre-shell-exec", "event": "beforeShellExecution", "command": "x"},
            {"name": "other-tool", "event": "postToolUse"},
        ]}))
        from buckler.hooks import strip
        strip(hooks_path=hooks_json)
        names = [h["name"] for h in json.loads(hooks_json.read_text())["hooks"]]
        assert "other-tool" in names and "buckler:pre-shell-exec" not in names

    def test_merge_dry_run_prints_without_writing(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON), dry_run=True)
        out = capsys.readouterr().out
        assert any(h["name"].startswith("buckler:") for h in json.loads(out)["hooks"])
        assert not hooks_json.exists()

    def test_strip_dry_run_reports_without_writing(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [
            {"name": "buckler:pre-shell-exec", "event": "beforeShellExecution", "command": "x"}
        ]}))
        from buckler.hooks import strip
        strip(hooks_path=hooks_json, dry_run=True)
        assert "Would remove" in capsys.readouterr().out
        assert len(json.loads(hooks_json.read_text())["hooks"]) == 1

    def test_status_lists_installed_hooks(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge, status
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        status(hooks_path=hooks_json)
        assert "buckler:pre-shell-exec" in capsys.readouterr().out

    def test_status_reports_when_empty(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        from buckler.hooks import status
        status(hooks_path=hooks_json)
        assert "No Buckler hooks" in capsys.readouterr().out

    def test_merge_falls_back_when_no_venv_python(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge
        merge(hooks_path=hooks_json)
        assert any(h["name"].startswith("buckler:") for h in json.loads(hooks_json.read_text())["hooks"])

    def test_read_hooks_json_returns_empty_on_bad_json(self, tmp_path: Path):
        bad = tmp_path / "hooks.json"
        bad.write_text("not json")
        from buckler.hooks import _read_hooks_json
        assert _read_hooks_json(bad) == {}
