"""Agent-git pack tests.

Tests git argv/segment cases: commit, force push, remote rm, add,
bypass, pipeline commands, and false positives.
"""

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


# ── Deny: git commit ─────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'hello'",
        "git commit --amend --no-edit",
        "git -C /some/path commit -m 'x'",
        "git commit -a -m 'all changes'",
        "git --git-dir=/repo/.git commit -m 'x'",
    ],
)
def test_deny_git_commit(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "deny", f"Expected deny for: {command!r}"
    assert result["agent_message"] is not None


@pytest.mark.parametrize(
    "command",
    [
        "git add . && git commit -m 'x'",
        "cd /tmp; git commit -m 'x'",
        "git status || git commit -m 'x'",
    ],
)
def test_deny_git_commit_in_pipeline(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "deny", f"Expected deny for pipeline: {command!r}"


# ── Deny: force push ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git push --force origin main",
        "git push -f origin main",
        "git push --force",
        "git push origin main --force",
    ],
)
def test_deny_git_push_force(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "deny", f"Expected deny for: {command!r}"


# ── Deny: push --delete ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git push --delete origin my-branch",
        "git push -d origin old-feature",
    ],
)
def test_deny_git_push_delete_flag(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "deny", f"Expected deny for: {command!r}"


# ── Deny: push --mirror ───────────────────────────────────────────────────────


def test_deny_git_push_mirror():
    result = evaluate(_input("git push --mirror origin"))
    assert result["decision"] == "deny"


# ── Deny: remote remove ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git remote remove origin",
        "git remote rm upstream",
    ],
)
def test_deny_git_remote_remove(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "deny", f"Expected deny for: {command!r}"


# ── Nudge/warn: git add ───────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git add -A",
        "git add src/",
        "git add .",
        "git add --all",
    ],
)
def test_nudge_git_add(command: str):
    result = evaluate(_input(command))
    assert result["decision"] == "nudge", f"Expected nudge for: {command!r}"
    assert result["additional_context"] is not None


# ── Allow: bypass via env ─────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git commit -m 'emergency'",
        "git push --force origin main",
        "git remote remove origin",
    ],
)
def test_bypass_allow(command: str):
    result = evaluate(_input(command, env={"RETHUNK_ALLOW_SHELL": "1"}))
    assert result["decision"] == "allow", f"Expected bypass allow for: {command!r}"


# ── Allow: benign git commands ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git status",
        "git log --oneline -10",
        "git diff HEAD",
        "git branch -a",
        "git fetch origin",
        "git stash list",
        "git show HEAD",
        "git push origin feature-branch",  # normal push (no force/delete/mirror)
        "git pull origin main",
    ],
)
def test_allow_benign_git(command: str):
    result = evaluate(_input(command))
    assert result["decision"] in ("allow", "nudge"), (
        f"Expected allow or nudge for benign command: {command!r}, got {result['decision']!r}"
    )


# ── False positive avoidance ──────────────────────────────────────────────────


@pytest.mark.parametrize(
    "command",
    [
        "git log --grep=commit",  # 'commit' as grep arg, not subcommand
        "git show HEAD~1",  # 'show', not 'commit'
        "git branch commit-review",  # 'branch', not 'commit'
        "echo 'git commit message'",  # not even git
        "cat .git/COMMIT_EDITMSG",  # reading file, not running git
    ],
)
def test_false_positive_avoidance(command: str):
    result = evaluate(_input(command))
    assert result["decision"] != "deny", (
        f"False positive: should not deny {command!r}, got {result['decision']!r}"
    )


# ── pre_shell_tool trigger ────────────────────────────────────────────────────


def test_pre_shell_tool_trigger_commits():
    """Commit denial also fires on pre_shell_tool (Shell tool interception)."""
    result = evaluate(_input("git commit -m 'x'", trigger="pre_shell_tool"))
    assert result["decision"] == "deny"


# ── post_tool_success nudge ───────────────────────────────────────────────────


def test_post_tool_mcp_nudge():
    """After a successful git command, the pack injects MCP steering context."""
    inp = {
        "policy_io_version": "1",
        "trigger": "post_tool_success",
        "shell": {"command": "git status", "cwd": "/home/user/project"},
        "tool": {"name": "Shell", "input": {"command": "git status"}, "output": {}},
        "session": None,
        "env": {},
    }
    result = evaluate(inp)
    assert result["decision"] == "nudge"
    assert result["additional_context"] is not None
    assert "MCP" in result["additional_context"] or "mcp" in result["additional_context"].lower()
