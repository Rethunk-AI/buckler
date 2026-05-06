"""Cursor adapter round-trip tests.

Tests that the Cursor adapter correctly maps native stdin JSON to PolicyInput,
and PolicyOutput back to Cursor's expected stdout JSON shape.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from buckler.adapters.cursor import adapt_input, adapt_output
from buckler.core import evaluate

FIXTURES = Path(__file__).parent / "fixtures" / "adapters" / "cursor"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ── Fixture-driven round-trip tests ──────────────────────────────────────────


@pytest.mark.parametrize(
    "fixture_name",
    [
        "before_shell_exec_commit.json",
        "before_shell_exec_add.json",
    ],
)
def test_fixture_round_trip(fixture_name: str):
    fx = _load(fixture_name)
    cursor_input = fx["cursor_input"]
    policy_input = adapt_input(cursor_input)

    # Check trigger
    expected_trigger = fx.get("expected_policy_input", {}).get("trigger")
    if expected_trigger:
        assert policy_input["trigger"] == expected_trigger

    # Check shell command preservation
    expected_shell = fx.get("expected_policy_input", {}).get("shell", {})
    if expected_shell.get("command"):
        assert policy_input["shell"]["command"] == expected_shell["command"]

    # Run through core
    policy_output = evaluate(policy_input)

    # Adapt back to Cursor
    cursor_output = adapt_output(policy_output, cursor_input)

    # Verify expected keys exist
    for key in fx.get("expected_cursor_output_keys", []):
        assert key in cursor_output, f"Expected key {key!r} in cursor_output: {cursor_output!r}"

    # Verify expected permission
    if "expected_permission" in fx:
        assert cursor_output.get("permission") == fx["expected_permission"]


# ── adapt_input unit tests ────────────────────────────────────────────────────


def test_adapt_before_shell_exec():
    raw = {
        "hook_event_name": "beforeShellExecution",
        "shell_command": "git commit -m 'test'",
        "cwd": "/project",
        "workspace_root": "/project",
    }
    pi = adapt_input(raw)
    assert pi["trigger"] == "pre_shell_exec"
    assert pi["shell"]["command"] == "git commit -m 'test'"
    assert pi["shell"]["cwd"] == "/project"
    assert pi["session"]["workspace_roots"] == ["/project"]


def test_adapt_pre_tool_use_shell():
    raw = {
        "hook_event_name": "preToolUse",
        "tool_name": "Shell",
        "tool_input": {"command": "git add ."},
        "cwd": "/project",
        "workspace_root": "/project",
    }
    pi = adapt_input(raw)
    assert pi["trigger"] == "pre_shell_tool"
    assert pi["tool"]["name"] == "Shell"
    assert pi["shell"]["command"] == "git add ."


def test_adapt_workspace_roots_includes_both_when_distinct():
    raw = {
        "hook_event_name": "beforeShellExecution",
        "shell_command": "git status",
        "workspace_root": "/repo",
        "cwd": "/repo/sub",
    }
    pi = adapt_input(raw)
    assert pi["session"]["workspace_roots"] == ["/repo", "/repo/sub"]


def test_adapt_post_tool_use():
    raw = {
        "hook_event_name": "postToolUse",
        "tool_name": "Shell",
        "tool_input": {"command": "git status"},
        "tool_response": {"output": "On branch main"},
        "cwd": "/project",
    }
    pi = adapt_input(raw)
    assert pi["trigger"] == "post_tool_success"
    assert pi["tool"]["output"] == {"output": "On branch main"}


# ── adapt_output unit tests ───────────────────────────────────────────────────


def test_adapt_output_deny():
    policy_output = {
        "policy_io_version": "1",
        "decision": "deny",
        "user_message": "Blocked.",
        "agent_message": "Do not do this.",
        "additional_context": None,
        "updated_tool_input": None,
    }
    raw_input = {"hook_event_name": "beforeShellExecution"}
    result = adapt_output(policy_output, raw_input)
    assert result["permission"] == "deny"
    assert result["message"] == "Blocked."
    assert result["agent_message"] == "Do not do this."


def test_adapt_output_allow():
    policy_output = {
        "policy_io_version": "1",
        "decision": "allow",
        "user_message": None,
        "agent_message": None,
        "additional_context": None,
        "updated_tool_input": None,
    }
    raw_input = {"hook_event_name": "beforeShellExecution"}
    result = adapt_output(policy_output, raw_input)
    assert result["permission"] == "allow"


def test_adapt_output_post_tool_nudge():
    policy_output = {
        "policy_io_version": "1",
        "decision": "nudge",
        "user_message": None,
        "agent_message": None,
        "additional_context": "Use MCP tools instead.",
        "updated_tool_input": None,
    }
    raw_input = {"hook_event_name": "postToolUse"}
    result = adapt_output(policy_output, raw_input)
    # Post-tool hooks don't use 'permission', they use 'additional_context'
    assert "permission" not in result
    assert result.get("additional_context") == "Use MCP tools instead."


# ── Edge cases ────────────────────────────────────────────────────────────────


class TestCursorAdapter:
    def test_unknown_event_maps_to_unknown_harness_event(self):
        """Unrecognised hook_event_name uses unknown_harness_event (no shipped rules match)."""
        pi = adapt_input({"hook_event_name": "unknownEvent", "cwd": "/p"})
        assert pi["trigger"] == "unknown_harness_event"

    def test_adapt_input_rejects_wrong_policy_io_version(self):
        from buckler.core import PolicyError

        with pytest.raises(PolicyError, match="policy_io_version"):
            adapt_input({"hook_event_name": "beforeShellExecution", "policy_io_version": "99"})

    def test_unknown_event_evaluates_to_allow(self):
        pi = adapt_input({"hook_event_name": "futureHook", "cwd": "/p"})
        out = evaluate(pi)
        assert out["decision"] == "allow"

    def test_ask_decision_maps_to_cursor_ask(self):
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
        assert result == {
            "permission": "ask",
            "message": "Confirm?",
            "agent_message": "Please confirm.",
        }

    def test_nudge_on_pre_hook_is_allow_with_messages(self):
        """Nudge on a pre-hook = allow + advisory messages (not a block)."""
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
        pi = adapt_input(
            {
                "hook_event_name": "preToolUse",
                "tool_name": "Edit",
                "tool_input": {"path": "/file.py"},
                "cwd": "/p",
                "workspace_root": "/p",
            }
        )
        assert pi["trigger"] == "pre_shell_tool"
        assert pi["tool"]["name"] == "Edit"
        assert pi["shell"] is None

    def test_workspace_root_from_cwd(self):
        """cwd is used as workspace_root when workspace_root key is absent."""
        pi = adapt_input(
            {"hook_event_name": "beforeShellExecution", "shell_command": "ls", "cwd": "/myproject"}
        )
        assert pi["session"]["workspace_roots"] == ["/myproject"]
