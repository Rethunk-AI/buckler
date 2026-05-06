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

# gh(1) global flags that take a following argument (before the command word).
_GH_GLOBAL_OPTS_WITH_ARG = frozenset({"-R", "--repo", "-h", "--hostname"})

_SHELL_WRAPPERS = frozenset({"bash", "sh", "dash"})
_MAX_POLICY_EXPAND_DEPTH = 3
_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


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


def _segment_command(command: str) -> list[str]:  # noqa: PLR0912, PLR0915
    """Split a shell command on &&, ||, ;, &, |, and newlines (not inside quotes)."""
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
            if command[i : i + 2] in ("&&", "||"):
                if current.strip():
                    segments.append(current.strip())
                current = ""
                i += 2
                continue
            if ch in "\n\r":
                if current.strip():
                    segments.append(current.strip())
                current = ""
                if ch == "\r" and i + 1 < len(command) and command[i + 1] == "\n":
                    i += 2
                else:
                    i += 1
                continue
            if ch == "|":
                if current.strip():
                    segments.append(current.strip())
                current = ""
                i += 1
                continue
            if ch == "&":
                if current.strip():
                    segments.append(current.strip())
                current = ""
                i += 1
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


def _strip_env_prefix_tokens(tokens: list[str]) -> list[str]:
    """Drop leading VAR=value assignments and a leading `env` invocation (spec parser-bypass)."""
    i = 0
    n = len(tokens)
    while i < n:
        t = tokens[i]
        if _ENV_ASSIGN_RE.match(t):
            i += 1
            continue
        if t == "env":
            i += 1
            if i < n and tokens[i] == "-i":
                i += 1
            while i + 1 < n and tokens[i] == "-u":
                i += 2
            while i < n and _ENV_ASSIGN_RE.match(tokens[i]):
                i += 1
            continue
        break
    return tokens[i:]


def _extract_substitution_bodies(segment: str) -> list[str] | None:  # noqa: PLR0912
    """Return inner command strings for `` `...` `` and `$(...)` (balanced parens)."""
    bodies: list[str] = []
    i = 0
    in_single = False
    in_double = False
    while i < len(segment):
        ch = segment[i]
        if ch == "'" and not in_double:
            in_single = not in_single
            i += 1
            continue
        if ch == '"' and not in_single:
            in_double = not in_double
            i += 1
            continue
        if not in_single and not in_double:
            if segment[i : i + 2] == "$(":
                depth = 1
                j = i + 2
                while j < len(segment) and depth:
                    if segment[j] == "(":
                        depth += 1
                    elif segment[j] == ")":
                        depth -= 1
                    j += 1
                if depth != 0:
                    return None
                bodies.append(segment[i + 2 : j - 1])
                i = j
                continue
            if ch == "`":
                j = i + 1
                while j < len(segment):
                    if segment[j] == "`":
                        bodies.append(segment[i + 1 : j])
                        i = j + 1
                        break
                    if segment[j] in "'\"":
                        q = segment[j]
                        j += 1
                        while j < len(segment) and segment[j] != q:
                            if segment[j] == "\\":
                                j += 1
                            j += 1
                        if j >= len(segment):
                            return None
                        j += 1
                        continue
                    j += 1
                else:
                    return None
                continue
        i += 1
    return bodies


def _expand_command_string(script: str, depth: int) -> list[str] | None:
    """Re-segment a script string and flatten each piece (recursion for parser-bypass)."""
    if depth > _MAX_POLICY_EXPAND_DEPTH:
        return None
    out: list[str] = []
    for part in _segment_command(script):
        chunk = _flatten_policy_segment(part, depth)
        if chunk is None:
            return None
        out.extend(chunk)
    return out


def _flatten_policy_segment(segment: str, depth: int) -> list[str] | None:  # noqa: PLR0911, PLR0912
    """Expand one segment for policy matching: env, bash -c, command substitution."""
    if depth > _MAX_POLICY_EXPAND_DEPTH:
        return None
    segment = segment.strip()
    if not segment:
        return []
    try:
        raw_toks = shlex.split(segment)
    except ValueError:
        return None
    bodies = _extract_substitution_bodies(segment)
    if bodies is None:
        return None

    etoks = _strip_env_prefix_tokens(raw_toks)
    out: list[str] = []
    if etoks:
        prog = Path(etoks[0]).name
        if prog in _SHELL_WRAPPERS and "-c" in etoks:
            ci = etoks.index("-c")
            if ci + 1 >= len(etoks):
                return None
            script = etoks[ci + 1]
            inner = _expand_command_string(script, depth + 1)
            if inner is None:
                return None
            out.extend(inner)
        elif Path(etoks[0]).name == "xargs" and "git" in etoks:
            out.append(segment)
            gi = etoks.index("git")
            synthetic = shlex.join(etoks[gi:])
            inner = _expand_command_string(synthetic, depth + 1)
            if inner is None:
                return None
            out.extend(inner)
        else:
            out.append(segment)
    for body in bodies:
        inner = _expand_command_string(body, depth + 1)
        if inner is None:
            return None
        out.extend(inner)
    return out


def _expand_policy_segments(command: str) -> list[str] | None:
    """Flatten a full shell command into strings to match against shell_segments rules."""
    out: list[str] = []
    for part in _segment_command(command):
        chunk = _flatten_policy_segment(part, 0)
        if chunk is None:
            return None
        out.extend(chunk)
    return out


def _gh_tokens_have_api_delete(tokens: list[str]) -> bool:
    """True if a gh argv uses `api` with `-X DELETE` or `--method DELETE` (case-insensitive)."""
    if not tokens or Path(tokens[0]).name != "gh":
        return False
    if "api" not in tokens:
        return False
    for i in range(len(tokens) - 1):
        if tokens[i] in ("-X", "--method") and tokens[i + 1].upper() == "DELETE":
            return True
    return False


def _parse_gh_subcommand(args: list[str]) -> tuple[str | None, list[str]]:
    """Parse gh argv (after `gh`) into composite subcommand + flags (for rule matching)."""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg.startswith("-"):
            if arg in _GH_GLOBAL_OPTS_WITH_ARG and i + 1 < len(args):
                i += 2
                continue
            i += 1
            continue
        cmd = arg
        rest = args[i + 1 :]
        flags = [a for a in rest if a.startswith("-")]
        rest_nf = [a for a in rest if not a.startswith("-")]
        sub = cmd
        if cmd == "repo" and rest_nf:
            head = rest_nf[0]
            if head in ("delete", "archive"):
                sub = f"repo {head}"
        elif cmd == "release" and rest_nf:
            head = rest_nf[0]
            if head == "delete":
                sub = "release delete"
            elif head == "delete-asset":
                sub = "release delete-asset"
        elif cmd == "pr" and rest_nf and rest_nf[0] == "close":
            sub = "pr close"
        elif cmd == "secret" and rest_nf and rest_nf[0] == "remove":
            sub = "secret remove"
        elif cmd == "ssh-key" and rest_nf and rest_nf[0] == "delete":
            sub = "ssh-key delete"
        elif cmd == "gpg-key" and rest_nf and rest_nf[0] == "delete":
            sub = "gpg-key delete"
        return sub, flags
    return None, []


def _parse_segment_tokens(tokens: list[str]) -> tuple[str | None, str | None, list[str]]:
    """Parse shlex tokens for one shell segment into (program, subcommand, flags)."""
    tokens = _strip_env_prefix_tokens(tokens)
    if not tokens:
        return None, None, []
    program = Path(tokens[0]).name
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
    elif program == "gh":
        subcommand, flags = _parse_gh_subcommand(args)
    else:
        # Generic: first non-flag arg is the subcommand (or None)
        for arg in args:
            if not arg.startswith("-"):
                subcommand = arg
                break
        flags = [a for a in args if a.startswith("-")]

    return program, subcommand, flags


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
    return _parse_segment_tokens(tokens)


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


def _match_shell_segments(match_cfg: dict[str, Any], segments: list[str]) -> bool:
    """Check if any expanded policy segment matches the shell_segments spec."""
    segment_specs = match_cfg.get("shell_segments", [])
    if not segment_specs:
        return True  # No segment constraint — always matches on other fields

    for segment in segments:
        try:
            raw_toks = shlex.split(segment)
        except ValueError:
            continue
        if not raw_toks:
            continue
        stoks = _strip_env_prefix_tokens(raw_toks)
        if not stoks:
            continue
        program, subcommand, flags = _parse_segment_tokens(raw_toks)
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
            if spec.get("gh_api_delete") and not _gh_tokens_have_api_delete(stoks):
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


def _matches(
    rule: dict[str, Any],
    policy_input: dict[str, Any],
    policy_segments: list[str],
    expansion_failed: bool,
) -> bool:
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
        if expansion_failed:
            return False
        if not _match_shell_segments(match_cfg, policy_segments):
            return False

    if not _match_env(match_cfg, env):
        return False

    return _match_tool_name(match_cfg, tool_name)


def _action_priority(action: str) -> int:
    return {"deny": 4, "ask": 3, "nudge": 2, "allow": 1}.get(action, 0)


class _TemplateContext(dict[str, str]):
    """Single-pass template fill: values cannot re-trigger placeholder substitution."""

    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


def _apply_template(template: str | None, context: dict[str, str]) -> str | None:
    if template is None:
        return None
    return template.format_map(_TemplateContext(context))


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

    policy_segments: list[str] = []
    expansion_failed = False
    if command:
        expanded = _expand_policy_segments(command)
        if expanded is None:
            expansion_failed = True
            policy_segments = []
        else:
            policy_segments = expanded

    if expansion_failed:
        out_fail: dict[str, Any] = {
            "policy_io_version": POLICY_IO_VERSION,
            "decision": "deny",
            "user_message": (
                "Command blocked: shell expansion depth exceeded or nested command "
                "could not be parsed."
            ),
            "agent_message": (
                "BLOCKED: {command}\n\n"
                "Buckler could not safely parse this command (recursion depth or "
                "quoting). Rewrite as a simpler command or ask the user to run it "
                "outside the agent."
            ),
            "additional_context": None,
            "updated_tool_input": None,
        }
        ctx0 = {"command": command}
        out_fail["agent_message"] = _apply_template(out_fail["agent_message"], ctx0)
        out_fail["user_message"] = _apply_template(out_fail["user_message"], ctx0)
        # Env-only rules (e.g. bypass) still apply when expansion fails
        best_bypass: dict[str, Any] | None = None
        for rule in rules:
            if _matches(rule, policy_input, policy_segments, expansion_failed) and (
                best_bypass is None
                or rule["priority"] > best_bypass["priority"]
                or (
                    rule["priority"] == best_bypass["priority"]
                    and _action_priority(rule["action"]) > _action_priority(best_bypass["action"])
                )
            ):
                best_bypass = rule
        if best_bypass is not None and best_bypass["action"] == "allow":
            out_ok = {
                "policy_io_version": POLICY_IO_VERSION,
                "decision": "allow",
                "user_message": _apply_template(best_bypass.get("user_message"), ctx0),
                "agent_message": _apply_template(best_bypass.get("agent_message"), ctx0),
                "additional_context": None,
                "updated_tool_input": None,
            }
            _write_audit_decision(cfg, policy_input, best_bypass, out_ok)
            return out_ok
        _write_audit_decision(cfg, policy_input, None, out_fail)
        return out_fail

    template_ctx = {
        "command": command,
        "program": "",
        "subcommand": "",
        "pack": "",
        "rule": "",
    }
    if policy_segments:
        prog, sub, _ = _parse_segment(policy_segments[0])
        template_ctx["program"] = prog or ""
        template_ctx["subcommand"] = sub or ""

    # Find best matching rule
    best_rule: dict[str, Any] | None = None
    for rule in rules:
        if _matches(rule, policy_input, policy_segments, expansion_failed) and (
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
