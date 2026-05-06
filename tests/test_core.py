"""Core evaluator tests — uses only PolicyInput/PolicyOutput, no Cursor JSON."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest import mock

import pytest

from buckler.core import _parse_segment, _segment_command, evaluate

FIXTURES = Path(__file__).parent / "fixtures" / "core"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ── Fixture-driven golden tests ──────────────────────────────────────────────


@pytest.mark.parametrize(
    "fixture_name",
    [
        "allow_basic.json",
        "deny_git_commit.json",
        "warn_git_add.json",
    ],
)
def test_golden_fixture(fixture_name: str):
    fx = _load(fixture_name)
    result = evaluate(fx["input"])
    assert result["decision"] == fx["expected_decision"], (
        f"Expected {fx['expected_decision']!r} but got {result['decision']!r} "
        f"for fixture {fixture_name}"
    )
    assert result["policy_io_version"] == "1"


# ── Segment parser unit tests ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command,expected_count",
    [
        ("git commit -m 'hello'", 1),
        ("git add . && git commit -m 'x'", 2),
        ("echo a; echo b; echo c", 3),
        ("git push || echo failed", 2),
        ("echo 'hello && world'", 1),  # quoted boundary
    ],
)
def test_segment_command(command: str, expected_count: int):
    segments = _segment_command(command)
    assert len(segments) == expected_count, f"segments={segments!r}"


def test_match_shell_segments_skips_empty_shlex_tokens(monkeypatch):
    """Empty argv from shlex is ignored (defensive; rare in real segments)."""
    from buckler import core

    real = core.shlex.split

    def split_wrap(s: str):
        if s == "__empty__":
            return []
        return real(s)

    monkeypatch.setattr(core.shlex, "split", split_wrap)
    cfg = {"shell_segments": [{"program": "git", "subcommand": "status"}]}
    assert core._match_shell_segments(cfg, "__empty__") is False


def test_parse_segment_git_unknown_flag_skipped():
    """Unknown single-dash tokens before subcommand are skipped (git parser loop)."""
    program, sub, _f = _parse_segment("git -W commit -m x")
    assert (program, sub) == ("git", "commit")


def test_parse_segment_gh_version_only():
    program, sub, _f = _parse_segment("gh -v")
    assert program == "gh"
    assert sub is None


def test_gh_tokens_have_api_delete_negative_cases():
    from buckler.core import _gh_tokens_have_api_delete

    assert _gh_tokens_have_api_delete(["gh"]) is False
    assert _gh_tokens_have_api_delete(["git", "api", "-X", "DELETE"]) is False
    assert _gh_tokens_have_api_delete(["gh", "repo", "view"]) is False


def test_parse_gh_subcommand_generic_flag_before_command():
    from buckler.core import _parse_gh_subcommand

    assert _parse_gh_subcommand(["--help", "repo", "delete", "x"]) == ("repo delete", [])


@pytest.mark.parametrize(
    "segment,expected_program,expected_sub",
    [
        ("git commit -m 'x'", "git", "commit"),
        ("git push --force origin main", "git", "push"),
        ("git -C /some/path commit -m 'x'", "git", "commit"),
        ("git remote remove origin", "git", "remote remove"),
        ("git remote rm upstream", "git", "remote rm"),
        ("git add -A", "git", "add"),
        ("ls -la /tmp", "ls", "/tmp"),
        ("/usr/bin/git commit -m 'x'", "git", "commit"),
        ("gh repo delete my/x", "gh", "repo delete"),
        ("gh -R o/r repo delete my", "gh", "repo delete"),
        ("gh pr close 9 --delete-branch", "gh", "pr close"),
        ("gh api x -X DELETE", "gh", "api"),
        ("gh release delete-asset t a", "gh", "release delete-asset"),
    ],
)
def test_parse_segment(segment: str, expected_program: str, expected_sub: str | None):
    program, sub, _flags = _parse_segment(segment)
    assert program == expected_program
    assert sub == expected_sub


# ── Edge cases & branch coverage ─────────────────────────────────────────────


class TestCoreEdgeCases:
    def test_segment_double_quoted_boundary(self):
        """&& inside double quotes must NOT split the command into two segments."""
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
        program, sub, _flags = _parse_segment("git --bare commit -m 'x'")
        assert (program, sub) == ("git", "commit")

        program, sub, _flags = _parse_segment("git -C /path commit -m 'x'")
        assert (program, sub) == ("git", "commit")

    def test_parse_segment_double_dash_stops_subcommand_search(self):
        """-- terminates global option parsing; the next token is not a subcommand."""
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
        result = evaluate(
            {
                "policy_io_version": "1",
                "trigger": "pre_shell_exec",
                "shell": {"command": "make test", "cwd": "/p"},
                "env": {},
            }
        )
        assert result["decision"] == "allow"
        assert result["user_message"] is None

    def test_evaluate_bypass_env_overrides_deny(self):
        """RETHUNK_ALLOW_SHELL=1 overrides even a deny rule."""
        result = evaluate(
            {
                "policy_io_version": "1",
                "trigger": "pre_shell_exec",
                "shell": {"command": "git commit -m 'x'", "cwd": "/p"},
                "env": {"RETHUNK_ALLOW_SHELL": "1"},
            }
        )
        assert result["decision"] == "allow"

    def test_evaluate_refspec_delete_detected(self):
        """git push with :branch implicit-delete refspec is denied end-to-end."""
        result = evaluate(
            {
                "policy_io_version": "1",
                "trigger": "pre_shell_exec",
                "shell": {"command": "git push origin :my-branch", "cwd": "/p"},
                "env": {},
            }
        )
        assert result["decision"] == "deny"

    def test_match_shell_segments_no_constraint_always_true(self):
        """A match_cfg with no shell_segments key immediately returns True."""
        from buckler.core import _match_shell_segments

        assert _match_shell_segments({}, "git commit -m 'x'") is True
        assert _match_shell_segments({"env": {"X": "y"}}, "make test") is True

    def test_malformed_segment_skipped_in_pipeline(self):
        """A malformed segment in a pipeline is silently skipped; evaluation continues."""
        from buckler.core import _match_shell_segments

        result = _match_shell_segments(
            {"shell_segments": [{"program": "git"}]},
            "echo hello && 'unclosed",
        )
        assert result is False


class TestCoreRemainingBranches:
    def test_match_tool_name_specified_and_matches(self):
        from buckler.core import _match_tool_name

        assert _match_tool_name({"tool_name": "Shell"}, "Shell") is True

    def test_match_tool_name_specified_no_match(self):
        from buckler.core import _match_tool_name

        assert _match_tool_name({"tool_name": "Shell"}, "Edit") is False

    def test_matches_shell_segments_empty_command(self):
        """When shell_segments in match but command is empty, rule does not fire."""
        from buckler.core import _matches

        rule = {
            "id": "r",
            "pack": "p",
            "source": "s",
            "trigger": ["pre_shell_exec"],
            "match": {"shell_segments": [{"program": "git"}]},
            "action": "deny",
            "priority": 100,
            "tier": "baseline",
            "user_message": None,
            "agent_message": None,
            "additional_context": None,
            "enabled": True,
        }
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": ""},
            "tool": None,
            "env": {},
        }
        assert _matches(rule, inp) is False

    def test_action_priority_unknown(self):
        from buckler.core import _action_priority

        assert _action_priority("unknown_action") == 0

    def test_evaluate_rule_priority_tie_higher_severity_wins(self):
        """When two rules tie on priority, higher-severity action wins."""
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

        result = _match_shell_segments(
            {"shell_segments": [{"program": "git", "subcommand": "commit"}]},
            "git commit && 'unclosed",
        )
        assert result is True

    def test_evaluate_refspec_delete_spec_no_match(self):
        """A rule with refspec_delete:true but no : refspec → not triggered."""
        inp = {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git push origin main"},
            "env": {},
        }
        assert evaluate(inp)["decision"] == "allow"

    def test_match_segments_none_program_continue_line(self):
        """continue fires when a trailing segment has program=None."""
        from buckler.core import _match_shell_segments

        result = _match_shell_segments(
            {"shell_segments": [{"program": "git"}]},
            "echo hello && 'unclosed",
        )
        assert result is False

    def test_evaluate_priority_tie_higher_severity_wins(self, tmp_path: Path):
        """Two rules at same priority: higher-severity action wins."""
        from buckler import pack_loader

        pack_yaml = tmp_path / "tie.yaml"
        pack_yaml.write_text(
            "pack: tie-test\nversion: '1'\nrules:\n"
            "  - id: r-allow\n    trigger: pre_shell_exec\n    action: allow\n"
            "    priority: 50\n    match:\n      shell_segments:\n        - program: ls\n"
            "    user_message: null\n    agent_message: null\n\n"
            "  - id: r-ask\n    trigger: pre_shell_exec\n    action: ask\n"
            "    priority: 50\n    match:\n      shell_segments:\n        - program: ls\n"
            "    user_message: 'Confirm?'\n    agent_message: null\n"
        )
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "nope"),
        ):
            rules = pack_loader.load_packs()

        with (
            mock.patch("buckler.core.load_packs", return_value=rules),
            mock.patch("buckler.core.load_config", return_value={"core": {"tier": "baseline"}}),
        ):
            result = evaluate(
                {
                    "policy_io_version": "1",
                    "trigger": "pre_shell_exec",
                    "shell": {"command": "ls -la"},
                    "env": {},
                }
            )
        assert result["decision"] == "ask"


class TestCorePolicyValidation:
    def test_audit_log_written_when_enabled(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        from buckler.core import evaluate

        log_path = tmp_path / "audit.log"

        def fake_audit() -> Path:
            return log_path

        monkeypatch.setattr("buckler.core.paths.audit_log", fake_audit)
        monkeypatch.setattr(
            "buckler.core.load_config",
            lambda: {"core": {"tier": "baseline", "audit_log": True}},
        )
        evaluate(
            {
                "policy_io_version": "1",
                "trigger": "pre_shell_exec",
                "shell": {"command": "make test", "cwd": "/p"},
                "env": {},
            }
        )
        text = log_path.read_text(encoding="utf-8")
        assert "decision=allow" in text
        assert "trigger=pre_shell_exec" in text

    def test_audit_log_write_failure_does_not_abort_evaluate(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ):
        """If the state directory cannot be written, policy outcome is still returned."""
        cfg_home = tmp_path / "cfg"
        state_home = tmp_path / "state"
        cfg_home.mkdir()
        state_home.mkdir()
        (cfg_home / "config.toml").write_text('[core]\naudit_log = true\ntier = "baseline"\n')
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(cfg_home))
        monkeypatch.setenv("BUCKLER_STATE_HOME", str(state_home))
        state_home.chmod(0o000)
        try:
            with caplog.at_level(logging.WARNING, logger="buckler.core"):
                result = evaluate(
                    {
                        "policy_io_version": "1",
                        "trigger": "pre_shell_exec",
                        "shell": {"command": "git status", "cwd": "/p"},
                        "env": {},
                    }
                )
            assert result["decision"] == "allow"
            assert any("Audit log write failed" in r.message for r in caplog.records), caplog.text
        finally:
            state_home.chmod(0o700)

    def test_evaluate_rejects_wrong_policy_io_version(self):
        from buckler.core import PolicyError, evaluate

        with pytest.raises(PolicyError, match="policy_io_version"):
            evaluate(
                {
                    "policy_io_version": "2",
                    "trigger": "pre_shell_exec",
                    "shell": {"command": "git status"},
                    "env": {},
                }
            )

    def test_evaluate_rejects_unknown_trigger(self):
        from buckler.core import PolicyError, evaluate

        with pytest.raises(PolicyError, match="Unsupported trigger"):
            evaluate(
                {
                    "policy_io_version": "1",
                    "trigger": "not_a_real_trigger",
                    "env": {},
                }
            )

    def test_evaluate_unknown_harness_event_is_allow(self):
        from buckler.core import evaluate

        result = evaluate(
            {
                "policy_io_version": "1",
                "trigger": "unknown_harness_event",
                "env": {},
            }
        )
        assert result["decision"] == "allow"
