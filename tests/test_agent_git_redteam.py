"""Red-team tests for agent-git pack parser (parser-bypass-hardening spec)."""

from __future__ import annotations

import shlex

import pytest

from buckler.core import evaluate


def _inp(command: str, env: dict | None = None) -> dict:
    return {
        "policy_io_version": "1",
        "trigger": "pre_shell_exec",
        "shell": {"command": command, "cwd": "/home/user/p"},
        "tool": None,
        "session": None,
        "env": env or {},
    }


@pytest.mark.parametrize(
    "command",
    [
        "git status & git commit -m foo",
        "git status | xargs git commit -m foo",
        "$(git commit -m foo)",
        "`git commit -m foo`",
        'bash -c "git commit -m foo"',
        'sh -c "git commit -m foo"',
        "FOO=bar git commit -m foo",
        "env GIT_AUTHOR_DATE=now git commit -m foo",
    ],
)
def test_baseline_bypass_vectors_now_deny(command: str):
    assert evaluate(_inp(command))["decision"] == "deny"


@pytest.mark.parametrize(
    "command",
    [
        "git log --grep=commit",
        "git branch commit-review",
        "cat .git/COMMIT_EDITMSG",
        "git commit-graph write",
    ],
)
def test_benign_patterns_not_deny(command: str):
    assert evaluate(_inp(command))["decision"] != "deny"


def test_recursion_depth_exceeded_denies():
    inner = "git commit -m x"
    for _ in range(6):
        inner = f"bash -c {shlex.quote(inner)}"
    assert evaluate(_inp(inner))["decision"] == "deny"


def test_unbalanced_substitution_denies():
    assert evaluate(_inp("echo $(git commit"))["decision"] == "deny"
