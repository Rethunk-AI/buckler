"""Validate PolicyInput and PolicyOutput structures against policy-io.schema.json.

Tests confirm that the JSON Schema file correctly accepts valid structures and
rejects invalid ones, closing the loop on schema-policy-io-json.
"""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

SCHEMA_PATH = Path(__file__).parent.parent / "docs" / "contracts" / "policy-io.schema.json"


@pytest.fixture(scope="module")
def policy_input_schema() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text())
    return schema["definitions"]["PolicyInput"]


@pytest.fixture(scope="module")
def policy_output_schema() -> dict:
    schema = json.loads(SCHEMA_PATH.read_text())
    return schema["definitions"]["PolicyOutput"]


# ── Valid PolicyInput structures ─────────────────────────────────────────────

VALID_INPUTS = [
    # Minimal: only required fields
    {"policy_io_version": "1", "trigger": "pre_shell_exec"},
    # With shell
    {
        "policy_io_version": "1",
        "trigger": "pre_shell_exec",
        "shell": {"command": "git commit -m 'x'", "cwd": "/project"},
    },
    # With tool
    {
        "policy_io_version": "1",
        "trigger": "pre_shell_tool",
        "tool": {"name": "Shell", "input": {"command": "git add ."}, "output": None},
    },
    # With session
    {
        "policy_io_version": "1",
        "trigger": "post_tool_success",
        "session": {
            "conversation_id": "abc123",
            "workspace_roots": ["/project"],
            "model": "claude-sonnet",
        },
    },
    # With env
    {
        "policy_io_version": "1",
        "trigger": "pre_shell_exec",
        "shell": {"command": "git commit"},
        "env": {"RETHUNK_ALLOW_SHELL": "1"},
    },
    # Adapter escape hatch trigger (matches no shipped rules by default)
    {"policy_io_version": "1", "trigger": "unknown_harness_event"},
    # Post-tool failure trigger
    {
        "policy_io_version": "1",
        "trigger": "post_tool_failure",
        "tool": {"name": "Shell", "input": None, "output": None},
    },
]


@pytest.mark.parametrize("data", VALID_INPUTS)
def test_valid_policy_input(data: dict, policy_input_schema: dict):
    jsonschema.validate(instance=data, schema=policy_input_schema)


# ── Invalid PolicyInput structures ────────────────────────────────────────────

INVALID_INPUTS = [
    # Missing trigger
    {"policy_io_version": "1"},
    # Unknown trigger value
    {"policy_io_version": "1", "trigger": "unknown_trigger"},
    # Wrong version
    {"policy_io_version": "2", "trigger": "pre_shell_exec"},
    # Extra field (additionalProperties: false)
    {"policy_io_version": "1", "trigger": "pre_shell_exec", "extra_field": True},
]


@pytest.mark.parametrize("data", INVALID_INPUTS)
def test_invalid_policy_input_rejected(data: dict, policy_input_schema: dict):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=policy_input_schema)


# ── Valid PolicyOutput structures ─────────────────────────────────────────────

VALID_OUTPUTS = [
    # Allow — minimal
    {"policy_io_version": "1", "decision": "allow"},
    # Deny with messages
    {
        "policy_io_version": "1",
        "decision": "deny",
        "user_message": "Blocked.",
        "agent_message": "Use MCP instead.",
    },
    # Nudge with additional_context
    {
        "policy_io_version": "1",
        "decision": "nudge",
        "additional_context": "Prefer batch_commit.",
    },
    # Ask
    {"policy_io_version": "1", "decision": "ask", "user_message": "Confirm?"},
    # All fields null
    {
        "policy_io_version": "1",
        "decision": "allow",
        "user_message": None,
        "agent_message": None,
        "additional_context": None,
        "updated_tool_input": None,
    },
]


@pytest.mark.parametrize("data", VALID_OUTPUTS)
def test_valid_policy_output(data: dict, policy_output_schema: dict):
    jsonschema.validate(instance=data, schema=policy_output_schema)


# ── Invalid PolicyOutput structures ───────────────────────────────────────────

INVALID_OUTPUTS = [
    # Missing decision
    {"policy_io_version": "1"},
    # Unknown decision value
    {"policy_io_version": "1", "decision": "block"},
    # Wrong version
    {"policy_io_version": "99", "decision": "allow"},
    # Extra field
    {"policy_io_version": "1", "decision": "allow", "rogue_field": True},
]


@pytest.mark.parametrize("data", INVALID_OUTPUTS)
def test_invalid_policy_output_rejected(data: dict, policy_output_schema: dict):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=data, schema=policy_output_schema)


# ── Cross-check: core evaluate() output validates against schema ───────────────


def test_evaluate_output_is_valid_schema(policy_output_schema: dict):
    """PolicyOutput from evaluate() must always conform to the JSON Schema."""
    from buckler.core import evaluate

    test_cases = [
        {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git commit -m 'x'"},
            "env": {},
        },
        {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git add ."},
            "env": {},
        },
        {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "ls -la"},
            "env": {},
        },
        {
            "policy_io_version": "1",
            "trigger": "pre_shell_exec",
            "shell": {"command": "git push --force origin main"},
            "env": {},
        },
    ]
    for inp in test_cases:
        output = evaluate(inp)
        jsonschema.validate(instance=output, schema=policy_output_schema)
