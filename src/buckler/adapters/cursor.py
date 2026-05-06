"""Cursor adapter.

Maps Cursor hook stdin JSON → PolicyInput, and PolicyOutput → Cursor stdout JSON.

Supported events:
  beforeShellExecution  → trigger: pre_shell_exec
  preToolUse (Shell)    → trigger: pre_shell_tool
  postToolUse           → trigger: post_tool_success
  postToolUseFailure    → trigger: post_tool_failure
  (unknown)             → trigger: unknown_harness_event (matches no builtin rules)

See docs/adapters/cursor.md for the full field mapping.
"""

from __future__ import annotations

from typing import Any

from buckler import POLICY_IO_VERSION
from buckler.core import PolicyError

_EVENT_TO_TRIGGER = {
    "beforeShellExecution": "pre_shell_exec",
    "preToolUse": "pre_shell_tool",
    "postToolUse": "post_tool_success",
    "postToolUseFailure": "post_tool_failure",
}


def adapt_input(raw: dict[str, Any]) -> dict[str, Any]:
    """Translate Cursor hook stdin JSON to PolicyInput."""
    raw_ver = raw.get("policy_io_version")
    if raw_ver is not None and str(raw_ver) != POLICY_IO_VERSION:
        raise PolicyError(
            f"Unsupported policy_io_version on Cursor payload: expected "
            f"{POLICY_IO_VERSION!r}, got {raw_ver!r}"
        )

    event = raw.get("hook_event_name", "")
    trigger = _EVENT_TO_TRIGGER.get(event)
    if trigger is None:
        # Unknown event: use a trigger that matches no shipped rules (default allow).
        trigger = "unknown_harness_event"

    shell: dict[str, Any] | None = None
    tool: dict[str, Any] | None = None
    cwd = raw.get("cwd") or raw.get("workspace_root")

    if event == "beforeShellExecution":
        shell = {
            "command": raw.get("shell_command", ""),
            "cwd": cwd,
        }

    elif event == "preToolUse":
        tool_name = raw.get("tool_name", "")
        tool_input = raw.get("tool_input") or {}
        tool = {"name": tool_name, "input": tool_input, "output": None}
        # If this is a Shell tool, extract the shell command too
        if tool_name == "Shell":
            command = tool_input.get("command", "") if isinstance(tool_input, dict) else ""
            shell = {"command": command, "cwd": cwd}

    elif event in ("postToolUse", "postToolUseFailure"):
        tool_name = raw.get("tool_name", "")
        tool_input = raw.get("tool_input") or {}
        tool_output = raw.get("tool_response") or {}
        tool = {"name": tool_name, "input": tool_input, "output": tool_output}
        # Populate shell.command from tool input for matching purposes
        if tool_name == "Shell" and isinstance(tool_input, dict):
            shell = {"command": tool_input.get("command", ""), "cwd": cwd}

    workspace_roots: list[str] = []
    wr = raw.get("workspace_root")
    cwd = raw.get("cwd")
    if wr and cwd and wr != cwd:
        workspace_roots = [wr, cwd]
    elif wr:
        workspace_roots = [wr]
    elif cwd:
        workspace_roots = [cwd]

    return {
        "policy_io_version": POLICY_IO_VERSION,
        "trigger": trigger,
        "shell": shell,
        "tool": tool,
        "session": {
            "conversation_id": raw.get("conversation_id"),
            "workspace_roots": workspace_roots,
            "model": raw.get("model"),
        },
        "env": {},
    }


def adapt_output(output: dict[str, Any], raw_input: dict[str, Any]) -> dict[str, Any]:
    """Translate PolicyOutput to Cursor hook stdout JSON."""
    event = raw_input.get("hook_event_name", "")
    decision = output.get("decision", "allow")

    # Post-tool hooks: Cursor reads 'additional_context', not 'permission'
    if event in ("postToolUse", "postToolUseFailure"):
        result: dict[str, Any] = {}
        ctx = output.get("additional_context")
        if ctx:
            result["additional_context"] = ctx
        return result

    # Pre-tool and shell execution hooks: Cursor reads 'permission'
    if decision == "deny":
        result = {"permission": "deny"}
        if output.get("user_message"):
            result["message"] = output["user_message"]
        if output.get("agent_message"):
            result["agent_message"] = output["agent_message"]
        return result

    if decision == "ask":
        result = {"permission": "ask"}
        if output.get("user_message"):
            result["message"] = output["user_message"]
        if output.get("agent_message"):
            result["agent_message"] = output["agent_message"]
        return result

    if decision == "nudge":
        # Nudge on a pre-hook = allow + optional messages
        result = {"permission": "allow"}
        if output.get("user_message"):
            result["message"] = output["user_message"]
        if output.get("agent_message"):
            result["agent_message"] = output["agent_message"]
        return result

    # allow
    return {"permission": "allow"}
