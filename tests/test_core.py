"""Core evaluator tests — uses only PolicyInput/PolicyOutput, no Cursor JSON."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from buckler.core import _parse_segment, _segment_command, evaluate

FIXTURES = Path(__file__).parent / "fixtures" / "core"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


# ── Fixture-driven golden tests ──────────────────────────────────────────────

@pytest.mark.parametrize("fixture_name", [
    "allow_basic.json",
    "deny_git_commit.json",
    "warn_git_add.json",
])
def test_golden_fixture(fixture_name: str):
    fx = _load(fixture_name)
    result = evaluate(fx["input"])
    assert result["decision"] == fx["expected_decision"], (
        f"Expected {fx['expected_decision']!r} but got {result['decision']!r} "
        f"for fixture {fixture_name}"
    )
    assert result["policy_io_version"] == "1"


# ── Segment parser unit tests ────────────────────────────────────────────────

@pytest.mark.parametrize("command,expected_count", [
    ("git commit -m 'hello'", 1),
    ("git add . && git commit -m 'x'", 2),
    ("echo a; echo b; echo c", 3),
    ("git push || echo failed", 2),
    ("echo 'hello && world'", 1),  # quoted boundary
])
def test_segment_command(command: str, expected_count: int):
    segments = _segment_command(command)
    assert len(segments) == expected_count, f"segments={segments!r}"


@pytest.mark.parametrize("segment,expected_program,expected_sub", [
    ("git commit -m 'x'", "git", "commit"),
    ("git push --force origin main", "git", "push"),
    ("git -C /some/path commit -m 'x'", "git", "commit"),
    ("git remote remove origin", "git", "remote remove"),
    ("git remote rm upstream", "git", "remote rm"),
    ("git add -A", "git", "add"),
    ("ls -la /tmp", "ls", "/tmp"),
    ("/usr/bin/git commit -m 'x'", "git", "commit"),
])
def test_parse_segment(segment: str, expected_program: str, expected_sub: str | None):
    program, sub, flags = _parse_segment(segment)
    assert program == expected_program
    assert sub == expected_sub
