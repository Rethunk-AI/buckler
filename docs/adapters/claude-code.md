# Claude Code Adapter (Stub)

Module: `buckler.adapters.claude` (planned)

This document is a **stub**. The Claude Code hook schema is not yet stable enough to ship a production adapter. This file captures the intended mapping plan.

## Status

| Item | Status |
|------|--------|
| Adapter module | Planned |
| Docs (this file) | Stub |
| Tests | Planned |

## Known Claude Code hook events (subject to change)

Claude Code exposes hooks via `~/.claude/settings.json` under a `hooks` key. As of early 2026, the following events are documented:

| Event | Timing | Buckler trigger (planned) |
|-------|--------|--------------------------|
| `PreToolUse` | Before a tool executes | `pre_shell_tool` (when `tool_name = "Bash"`) |
| `PostToolUse` | After a tool executes | `post_tool_success` |
| `PostToolUseFailure` | After a tool fails | `post_tool_failure` |

There is no direct equivalent to Cursor's `beforeShellExecution` in Claude Code's current hook schema. The `PreToolUse` + `Bash` matcher is the primary interception point.

## Planned `PolicyInput` mapping

Claude Code `PreToolUse` (Bash):
```json
{
  "hook_event_name": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": {
    "command": "git commit -m 'hello'",
    "restart": false
  },
  "cwd": "/home/user/project"
}
```

Planned Buckler `PolicyInput`:
```json
{
  "policy_io_version": "1",
  "trigger": "pre_shell_tool",
  "shell": {
    "command": "git commit -m 'hello'",
    "cwd": "/home/user/project"
  },
  "tool": {
    "name": "Bash",
    "input": {"command": "git commit -m 'hello'", "restart": false}
  },
  "env": {}
}
```

## Planned stdout mapping

Claude Code hooks are expected to use a similar `permission`/`message` pattern to Cursor. The exact field names should be confirmed against the stable schema before shipping.

## Wiring (planned)

The adapter would be invoked via a Claude Code hook config entry pointing at:
```
buckler --driver claude
```

## Contributing

Once the Claude Code hook schema stabilizes, contribute the adapter following [adapters/README.md](README.md). This stub document should be updated with the confirmed field mapping and the stub note removed.
