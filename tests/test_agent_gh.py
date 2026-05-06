"""Agent-gh pack tests — destructive gh CLI commands."""

from __future__ import annotations

import pytest

from buckler.core import evaluate


def _input(command: str, trigger: str = "pre_shell_exec", env: dict | None = None) -> dict:
    return {
        "policy_io_version": "1",
        "trigger": trigger,
        "shell": {"command": command, "cwd": "/home/user/project"},
        "tool": None,
        "session": None,
        "env": env or {},
    }


@pytest.mark.parametrize(
    "command",
    [
        "gh repo delete myorg/myrepo --yes",
        "gh repo archive myorg/myrepo",
        "gh release delete v1.0.0",
        "gh release delete-asset v1.0.0 ./dist.tgz",
        "gh pr close 42 --delete-branch",
        "gh api repos/foo/bar -X DELETE",
        "gh api repos/foo/bar --method DELETE",
        "gh api repos/foo/bar --method delete",
        "gh secret remove MYSECRET",
        "gh ssh-key delete 12345",
        "gh gpg-key delete ABCD",
    ],
)
def test_deny_destructive_gh(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "deny", f"Expected deny for: {command!r}"


@pytest.mark.parametrize(
    "command",
    [
        "gh repo view myorg/myrepo",
        "gh pr list",
        "gh issue list",
        "gh release list",
        "gh pr close 42",
        "gh pr close --repo o/r 99",
    ],
)
def test_allow_read_only_or_safe_gh_pr_close(command: str):
    result = evaluate(_input(command))
    assert result["decision"] != "deny", (
        f"Expected not deny for: {command!r}, got {result['decision']!r}"
    )


def test_allow_gh_api_non_delete():
    result = evaluate(_input("gh api graphql -f query=foo"))
    assert result["decision"] != "deny"


@pytest.mark.parametrize(
    "command",
    [
        "gh repo delete x/y",
        "gh api repos/x -X DELETE",
    ],
)
def test_bypass_allows_gh(command: str):
    result = evaluate(_input(command, env={"RETHUNK_ALLOW_SHELL": "1"}))
    assert result["decision"] == "allow"


def test_pre_shell_tool_trigger_gh_delete_repo():
    result = evaluate(_input("gh repo delete x/y", trigger="pre_shell_tool"))
    assert result["decision"] == "deny"


def test_post_tool_nudge_gh():
    inp = {
        "policy_io_version": "1",
        "trigger": "post_tool_success",
        "shell": {"command": "gh pr list", "cwd": "/home/user/project"},
        "tool": {"name": "Shell", "input": {"command": "gh pr list"}, "output": {}},
        "session": None,
        "env": {},
    }
    result = evaluate(inp)
    assert result["decision"] == "nudge"
    assert "MCP" in result["additional_context"] or "mcp" in result["additional_context"].lower()
