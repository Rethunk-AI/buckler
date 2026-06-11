"""Buckler — Agent Gatehouse.

A harness-neutral policy engine that evaluates declarative YAML rules
against normalized agent signals (shell text, tool identity, metadata)
and decides whether to allow, deny, ask, or nudge the action.
"""

__version__ = "0.2.2"
POLICY_IO_VERSION = "1"

# Abstract trigger kinds for PolicyInput (must match policy-io schema + pack_loader).
POLICY_TRIGGERS = frozenset(
    {
        "pre_shell_tool",
        "pre_shell_exec",
        "post_tool_success",
        "post_tool_failure",
        "unknown_harness_event",
    }
)
