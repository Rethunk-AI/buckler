# Cursor Adapter

Module: `buckler.adapters.cursor`

This adapter maps Cursor's hook events (stdin JSON) to `PolicyInput`, and `PolicyOutput` back to Cursor's expected stdout JSON.

## Event mapping

| Cursor `hook_event_name` | Cursor matcher | Buckler `trigger` | `failClosed` |
|--------------------------|---------------|-------------------|-------------|
| `preToolUse` (+ `Shell` tool) | `type: Tool`, `name: Shell` | `pre_shell_tool` | `true` |
| `beforeShellExecution` | (all) | `pre_shell_exec` | `true` |
| `postToolUse` | (all) | `post_tool_success` | `false` |
| `postToolUseFailure` | (all) | `post_tool_failure` | `false` |

## Cursor stdin JSON → `PolicyInput`

### `beforeShellExecution` (→ `pre_shell_exec`)

Cursor stdin:
```json
{
  "hook_event_name": "beforeShellExecution",
  "shell_command": "git commit -m 'hello'",
  "cwd": "/home/user/project",
  "workspace_root": "/home/user/project"
}
```

Buckler `PolicyInput`:
```json
{
  "policy_io_version": "1",
  "trigger": "pre_shell_exec",
  "shell": {
    "command": "git commit -m 'hello'",
    "cwd": "/home/user/project"
  },
  "session": {
    "workspace_roots": ["/home/user/project"]
  },
  "env": {}
}
```

### `preToolUse` with Shell tool (→ `pre_shell_tool`)

Cursor stdin:
```json
{
  "hook_event_name": "preToolUse",
  "tool_name": "Shell",
  "tool_input": {
    "command": "git add -A"
  },
  "cwd": "/home/user/project",
  "workspace_root": "/home/user/project"
}
```

Buckler `PolicyInput`:
```json
{
  "policy_io_version": "1",
  "trigger": "pre_shell_tool",
  "shell": {
    "command": "git add -A",
    "cwd": "/home/user/project"
  },
  "tool": {
    "name": "Shell",
    "input": {"command": "git add -A"}
  },
  "session": {
    "workspace_roots": ["/home/user/project"]
  },
  "env": {}
}
```

### `postToolUse` (→ `post_tool_success`)

Cursor stdin:
```json
{
  "hook_event_name": "postToolUse",
  "tool_name": "Shell",
  "tool_input": {"command": "git status"},
  "tool_response": {"output": "On branch main"},
  "cwd": "/home/user/project"
}
```

Buckler `PolicyInput`:
```json
{
  "policy_io_version": "1",
  "trigger": "post_tool_success",
  "tool": {
    "name": "Shell",
    "input": {"command": "git status"},
    "output": {"output": "On branch main"}
  },
  "shell": {
    "command": "git status",
    "cwd": "/home/user/project"
  },
  "session": {
    "workspace_roots": ["/home/user/project"]
  },
  "env": {}
}
```

## `PolicyOutput` → Cursor stdout JSON

### Deny response

`PolicyOutput`: `{"decision": "deny", "user_message": "...", "agent_message": "..."}`

Cursor stdout:
```json
{
  "permission": "deny",
  "message": "...",
  "agent_message": "..."
}
```

### Allow response

Cursor stdout:
```json
{
  "permission": "allow"
}
```

### Ask response

Cursor stdout:
```json
{
  "permission": "ask",
  "message": "...",
  "agent_message": "..."
}
```

### Nudge (post hooks) — `additional_context`

For `postToolUse` hooks, Cursor doesn't use a `permission` field. Instead, the adapter writes:
```json
{
  "additional_context": "..."
}
```

## `hooks.json` wiring

`scripts/setup.sh install` (and `python -m buckler.hooks merge`) adds these entries to `~/.cursor/hooks.json`:

```json
{
  "hooks": [
    {
      "name": "buckler:pre-shell-exec",
      "description": "Buckler agent-git pack: deny git commit, force push, remote destruction",
      "event": "beforeShellExecution",
      "command": "/path/to/.local/share/buckler/current/.venv/bin/python -m buckler --driver cursor",
      "timeout": 5000,
      "failClosed": true
    },
    {
      "name": "buckler:pre-shell-tool",
      "description": "Buckler defense-in-depth: intercept Shell tool proposals",
      "event": "preToolUse",
      "matchers": [{"type": "Tool", "name": "Shell"}],
      "command": "/path/to/.local/share/buckler/current/.venv/bin/python -m buckler --driver cursor",
      "timeout": 5000,
      "failClosed": true
    },
    {
      "name": "buckler:post-tool",
      "description": "Buckler MCP nudge: steer agent toward MCP tools",
      "event": "postToolUse",
      "command": "/path/to/.local/share/buckler/current/.venv/bin/python -m buckler --driver cursor",
      "timeout": 3000,
      "failClosed": false
    }
  ]
}
```

The `command` path is an absolute path to the Buckler venv Python, set by `setup.sh` based on `buckler.paths.current_dir()`.
