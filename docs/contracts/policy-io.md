# Policy I/O Contract

**`policy_io_version`**: `"1"`

This document is the normative definition of the harness-neutral internal contract between Buckler adapters and `buckler.core`. The JSON Schema lives alongside at [policy-io.schema.json](policy-io.schema.json).

## Overview

```
Adapter                     Core
  │                           │
  │   PolicyInput (JSON)       │
  ├──────────────────────────►│
  │                           │  evaluate(PolicyInput) → PolicyOutput
  │   PolicyOutput (JSON)      │
  │◄──────────────────────────┤
```

- **Adapters** translate native harness JSON → `PolicyInput`, and `PolicyOutput` → native response JSON.
- **`buckler.core`** never imports harness-specific modules. It only consumes `PolicyInput` and produces `PolicyOutput`.
- **Packs** reference `trigger` values from this document's abstract set—not from harness-specific event name strings.

## `PolicyInput`

```json
{
  "policy_io_version": "1",
  "trigger": "pre_shell_exec",
  "shell": {
    "command": "git commit -m 'hello'",
    "cwd": "/home/user/project"
  },
  "tool": null,
  "session": {
    "conversation_id": "abc123",
    "workspace_roots": ["/home/user/project"],
    "model": "claude-sonnet-4"
  },
  "env": {
    "RETHUNK_ALLOW_SHELL": "0"
  }
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `policy_io_version` | `string` | Yes | Schema version; currently `"1"`. |
| `trigger` | `string` (enum) | Yes | Abstract event kind (see trigger table). |
| `shell` | `object \| null` | No | Present for shell-related triggers. |
| `shell.command` | `string` | Yes (if shell) | Raw shell command string as received by the harness. |
| `shell.cwd` | `string \| null` | No | Working directory at invocation time. |
| `tool` | `object \| null` | No | Present for tool-related triggers. |
| `tool.name` | `string` | Yes (if tool) | Tool identifier (e.g. `"Shell"`, `"bash"`). |
| `tool.input` | `object \| null` | No | Tool input payload (harness-specific; opaque to core). |
| `tool.output` | `object \| null` | No | Tool output (post hooks only). |
| `session` | `object \| null` | No | Ambient session context. |
| `session.conversation_id` | `string \| null` | No | Harness conversation/session ID. |
| `session.workspace_roots` | `array[string]` | No | Workspace root paths. |
| `session.model` | `string \| null` | No | Model identifier in use. |
| `env` | `object` | No | Relevant environment variables (string → string). |

### Trigger values

| Trigger | Typical Cursor source | `failClosed` | Description |
|---------|----------------------|-------------|-------------|
| `pre_shell_tool` | `preToolUse` + `Shell` matcher | `true` | Shell command proposed by a tool call, before execution. |
| `pre_shell_exec` | `beforeShellExecution` | `true` | Final shell line about to execute. |
| `post_tool_success` | `postToolUse` | `false` | Tool completed successfully; nudge/context injection. |
| `post_tool_failure` | `postToolUseFailure` | `false` | Tool failed; optional diagnostic context. |
| `unknown_harness_event` | (unrecognized `hook_event_name`) | varies | Adapter escape hatch: matches no builtin rules unless you add user rules; core default is allow. |

## `PolicyOutput`

```json
{
  "policy_io_version": "1",
  "decision": "deny",
  "user_message": "git commit is blocked by the agent-git pack.",
  "agent_message": "BLOCKED: Use plugin-rethunk-git-rethunk-git batch_commit MCP tool to commit changes instead of git commit.",
  "additional_context": null,
  "updated_tool_input": null
}
```

### Fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `policy_io_version` | `string` | Yes | Must match the input version. |
| `decision` | `string` (enum) | Yes | `allow`, `deny`, `ask`, or `nudge`. |
| `user_message` | `string \| null` | No | Message shown to the human operator (UI). |
| `agent_message` | `string \| null` | No | Message injected into the agent's context. |
| `additional_context` | `string \| null` | No | Extra context appended to post-tool signals (nudge pattern). |
| `updated_tool_input` | `object \| null` | No | Replacement tool input (pre-tool hooks only; harness support varies). |

### Decision values

| Decision | Meaning | Harness behavior |
|----------|---------|-----------------|
| `allow` | Permit unconditionally | Harness proceeds; optional messages surfaced |
| `deny` | Block the action | Harness cancels; `user_message` shown; `agent_message` injected |
| `ask` | Surface to human for confirmation | Harness prompts; falls back to `deny` in non-interactive mode |
| `nudge` | Allow + inject context | Action proceeds; `additional_context` appended (post hooks) |

## Versioning

- `policy_io_version` is a monotonically increasing string integer (`"1"`, `"2"`, …).
- Additive, backward-compatible changes (new optional fields) do **not** require a version bump.
- Breaking changes (removed or renamed required fields, changed semantics) require a bump, a migration guide in this file, and an updated JSON Schema.
- Adapters must check `policy_io_version` and reject inputs they cannot handle.
