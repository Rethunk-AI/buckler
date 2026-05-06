"""Buckler core evaluator.

evaluate(PolicyInput) -> PolicyOutput

This module has zero imports from harness-specific code. It takes a
PolicyInput dict, loads rules via pack_loader, and returns a PolicyOutput dict.
"""

from __future__ import annotations

import logging
import re
import shlex
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from buckler import POLICY_IO_VERSION, POLICY_TRIGGERS, paths
from buckler.pack_loader import load_config, load_packs

log = logging.getLogger(__name__)

# Git global options that appear before the subcommand and should be skipped
# during subcommand identification. See git(1) SYNOPSIS.
_GIT_GLOBAL_OPTS_WITH_ARG = frozenset(
    ["-C", "--git-dir", "--work-tree", "-c", "--namespace", "--super-prefix"]
)
_GIT_GLOBAL_FLAGS = frozenset(
    ["--bare", "--no-replace-objects", "--no-optional-locks", "--version", "--help", "-p"]
)

# Shell segment boundary patterns (unquoted)
_SEGMENT_BOUNDARY = re.compile(r"\s*(?:&&|\|\||;)\s*")


class PolicyError(Exception):
    pass


def _validate_policy_input(policy_input: dict[str, Any]) -> None:
    ver = policy_input.get("policy_io_version")
    if ver != POLICY_IO_VERSION:
        raise PolicyError(
            f"Unsupported policy_io_version: expected {POLICY_IO_VERSION!r}, got {ver!r}"
        )
    trig = policy_input.get("trigger", "")
    if trig not in POLICY_TRIGGERS:
        raise PolicyError(f"Unsupported trigger: {trig!r}")


def _write_audit_decision(
    cfg: dict[str, Any],
    policy_input: dict[str, Any],
    best_rule: dict[str, Any] | None,
    output: dict[str, Any],
) -> None:
    if not cfg.get("core", {}).get("audit_log"):
        return
    shell = policy_input.get("shell") or {}
    cmd = shell.get("command", "") if isinstance(shell, dict) else ""
    rule_id = best_rule["id"] if best_rule else ""
    pack_id = best_rule["pack"] if best_rule else ""
    ts = datetime.now(UTC).isoformat()
    line = (
        f"{ts}\ttrigger={policy_input.get('trigger', '')}\t"
        f"decision={output.get('decision', '')}\trule={rule_id}\tpack={pack_id}\tcommand={cmd!r}"
    )
    log_path = paths.audit_log()
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError as e:
        log.warning("Audit log write failed: %s", e)


def _segment_command(command: str) -> list[str]:
    """Split a shell command on &&, ||, ; respecting single and double quotes."""
    segments: list[str] = []
    current = ""
    in_single = False
    in_double = False
    i = 0
    while i < len(command):
        ch = command[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            current += ch
        elif ch == '"' and not in_single:
            in_double = not in_double
            current += ch
        elif not in_single and not in_double:
            # Look ahead for && or ||
            if command[i : i + 2] in ("&&", "||"):
                if current.strip():
                    segments.append(current.strip())
                current = ""
                i += 2
                continue
            if ch == ";":
                if current.strip():
                    segments.append(current.strip())
                current = ""
            else:
                current += ch
        else:
            current += ch
        i += 1
    if current.strip():
        segments.append(current.strip())
    return segments


def _parse_segment(segment: str) -> tuple[str | None, str | None, list[str]]:
    """Parse a single shell segment into (program, subcommand, flags).

    Returns (None, None, []) if the segment cannot be parsed.
    """
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return None, None, []
    if not tokens:
        return None, None, []

    program = tokens[0]
    # Strip path prefix (e.g. /usr/bin/git → git)
    program = Path(program).name

    args = tokens[1:]
    subcommand: str | None = None
    flags: list[str] = []

    if program == "git":
        # Skip git global options
        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "--":
                break
            if arg in _GIT_GLOBAL_FLAGS:
                i += 1
                continue
            if arg in _GIT_GLOBAL_OPTS_WITH_ARG:
                i += 2
                continue
            if arg.startswith("-"):
                i += 1
                continue
            # First non-flag, non-global-opt arg is the subcommand
            subcommand = arg
            flags = [a for a in args[i + 1 :] if a.startswith("-")]
            # For composite subcommands like "remote remove", grab the next token too
            rest_non_flags = [a for a in args[i + 1 :] if not a.startswith("-")]
            if subcommand == "remote" and rest_non_flags:
                subcommand = f"remote {rest_non_flags[0]}"
            break
    else:
        # Generic: first non-flag arg is the subcommand (or None)
        for arg in args:
            if not arg.startswith("-"):
                subcommand = arg
                break
        flags = [a for a in args if a.startswith("-")]

    return program, subcommand, flags


def _flags_match(
    rule_flags_any: list[str], rule_flags_all: list[str], actual_flags: list[str]
) -> bool:
    """Check flag constraints from a shell_segment match entry."""
    actual_set = set(actual_flags)
    if rule_flags_any and not any(f in actual_set for f in rule_flags_any):
        return False
    return not (rule_flags_all and not all(f in actual_set for f in rule_flags_all))


def _push_has_delete_refspec(segment: str) -> bool:
    """Detect git push with a refspec like ':branch' (implicit delete)."""
    try:
        tokens = shlex.split(segment)
    except ValueError:
        return False
    return any(t.startswith(":") and not t.startswith("::") for t in tokens)


def _match_shell_segments(match_cfg: dict[str, Any], command: str) -> bool:
    """Check if any shell segment in the command matches the shell_segments spec."""
    segment_specs = match_cfg.get("shell_segments", [])
    if not segment_specs:
        return True  # No segment constraint — always matches on other fields

    segments = _segment_command(command)
    for segment in segments:
        program, subcommand, flags = _parse_segment(segment)
        if program is None:
            continue
        for spec in segment_specs:
            spec_program = spec.get("program")
            spec_sub = spec.get("subcommand")
            spec_flags_any = spec.get("flags_any", [])
            spec_flags_all = spec.get("flags_all", [])
            spec_refspec_delete = spec.get("refspec_delete", False)

            if spec_program and program != spec_program:
                continue
            if spec_sub and subcommand != spec_sub:
                continue
            if not _flags_match(spec_flags_any, spec_flags_all, flags):
                continue
            if spec_refspec_delete and not _push_has_delete_refspec(segment):
                continue
            return True
    return False


def _match_env(match_cfg: dict[str, Any], env: dict[str, str]) -> bool:
    """Check env var conditions (AND)."""
    env_spec = match_cfg.get("env", {})
    return all(env.get(key) == expected for key, expected in env_spec.items())


def _match_tool_name(match_cfg: dict[str, Any], tool_name: str | None) -> bool:
    spec = match_cfg.get("tool_name")
    if spec is None:
        return True
    return bool(tool_name == spec)


def _matches(rule: dict[str, Any], policy_input: dict[str, Any]) -> bool:
    """Return True if the rule matches this PolicyInput."""
    # Trigger match
    trigger = policy_input.get("trigger", "")
    if trigger not in rule["trigger"]:
        return False

    match_cfg = rule.get("match", {})
    shell = policy_input.get("shell") or {}
    command = shell.get("command", "")
    env = policy_input.get("env") or {}
    tool = policy_input.get("tool") or {}
    tool_name = tool.get("name")

    # If shell_segments specified, command must be non-empty and match
    if "shell_segments" in match_cfg:
        if not command:
            return False
        if not _match_shell_segments(match_cfg, command):
            return False

    if not _match_env(match_cfg, env):
        return False

    return _match_tool_name(match_cfg, tool_name)


def _action_priority(action: str) -> int:
    return {"deny": 4, "ask": 3, "nudge": 2, "allow": 1}.get(action, 0)


def _apply_template(template: str | None, context: dict[str, str]) -> str | None:
    if template is None:
        return None
    for key, val in context.items():
        template = template.replace(f"{{{key}}}", val)
    return template


def evaluate(policy_input: dict[str, Any]) -> dict[str, Any]:
    """Evaluate policy rules against the given PolicyInput and return PolicyOutput.

    This function has no harness-specific imports. It loads packs from
    pack_loader and returns a harness-neutral PolicyOutput dict.
    """
    cfg = load_config()
    _validate_policy_input(policy_input)
    tier = cfg["core"].get("tier", "baseline")
    rules = load_packs(tier=tier)

    shell = policy_input.get("shell") or {}
    command = shell.get("command", "")

    template_ctx = {
        "command": command,
        "program": "",
        "subcommand": "",
        "pack": "",
        "rule": "",
    }
    if command:
        segments = _segment_command(command)
        if segments:
            prog, sub, _ = _parse_segment(segments[0])
            template_ctx["program"] = prog or ""
            template_ctx["subcommand"] = sub or ""

    # Find best matching rule
    best_rule: dict[str, Any] | None = None
    for rule in rules:
        if _matches(rule, policy_input) and (
            best_rule is None
            or rule["priority"] > best_rule["priority"]
            or (
                rule["priority"] == best_rule["priority"]
                and _action_priority(rule["action"]) > _action_priority(best_rule["action"])
            )
        ):
            best_rule = rule

    if best_rule is None:
        out: dict[str, Any] = {
            "policy_io_version": POLICY_IO_VERSION,
            "decision": "allow",
            "user_message": None,
            "agent_message": None,
            "additional_context": None,
            "updated_tool_input": None,
        }
        _write_audit_decision(cfg, policy_input, None, out)
        return out

    template_ctx["pack"] = best_rule["pack"]
    template_ctx["rule"] = best_rule["id"]

    out = {
        "policy_io_version": POLICY_IO_VERSION,
        "decision": best_rule["action"],
        "user_message": _apply_template(best_rule.get("user_message"), template_ctx),
        "agent_message": _apply_template(best_rule.get("agent_message"), template_ctx),
        "additional_context": _apply_template(best_rule.get("additional_context"), template_ctx),
        "updated_tool_input": None,
    }
    _write_audit_decision(cfg, policy_input, best_rule, out)
    return out
