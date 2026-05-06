# Rule Schema

Rules are defined in YAML pack files. Buckler ships builtin packs under `packs/`; users add packs to `$XDG_CONFIG_HOME/buckler/rules.d/`.

## Pack file structure

```yaml
pack: agent-git          # Unique pack identifier (slug)
version: "1"             # Pack format version
description: |
  Safe git + MCP steering for AI coding agents.

# Optional: per-pack defaults (can be overridden by user config)
defaults:
  tier: baseline         # baseline | strict

rules:
  - id: deny-git-commit
    # ... (see Rule fields below)
```

## Rule fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `string` | Yes | Unique within the pack. |
| `trigger` | `string \| list[string]` | Yes | Abstract trigger kind(s) from `policy-io.md`. |
| `match` | `object` | No | Match conditions (all must pass). Default: unconstrained (`{}`). |
| `action` | `string` | Yes | `allow`, `deny`, `ask`, or `nudge`. |
| `priority` | `integer` | No | Higher wins on conflict. Default: `50`. |
| `tier` | `string` | No | `baseline` or `strict`. Rules with `tier: strict` only fire when `config.toml` sets `tier = "strict"`. Default: `baseline`. |
| `user_message` | `string \| null` | No | Message for the IDE UI. Supports `{command}` template. |
| `agent_message` | `string \| null` | No | Message injected into agent context. Supports `{command}`. |
| `additional_context` | `string \| null` | No | Extra context for nudge signals. |
| `enabled` | `boolean` | No | Default: `true`. Set `false` to disable without removing. |

## `match` object

All specified fields in `match` must match for the rule to fire. Omitted fields are unconstrained (match anything).

```yaml
match:
  # Matches if any shell segment matches this program/subcommand/flags profile
  shell_segments:
    - program: git            # exact match on argv[0] after global-option skip
      subcommand: commit      # exact match on first non-flag arg after program
      flags_any: []           # (optional) at least one of these flags present
      flags_all: []           # (optional) all of these flags must be present
      refspec_delete: false   # (optional) when true, segment must be git push with ':ref' delete refspec

  # Matches on the tool name (for pre_shell_tool / post_tool_* triggers)
  tool_name: Shell            # exact string match

  # Matches if env var is set to this value
  env:
    RETHUNK_ALLOW_SHELL: "0"  # if set to "1", bypass rules fire instead
```

### `shell_segments` matching

Buckler segments shell commands on `&&`, `||`, and `;` (respecting quoting), then parses each segment with `shlex.split`. For `git` commands, global options (`-C`, `--git-dir`, `--work-tree`, `-c`, `--namespace`, `--super-prefix`, `--bare`, `--no-replace-objects`, `--no-optional-locks`) are skipped before identifying the subcommand.

Multiple entries in `shell_segments` are OR-ed (any segment matching any entry fires the rule).

When `refspec_delete` is `true`, the segment must be a `git push` that includes an implicit-delete refspec (a token starting with `:` that is not `::`).

### `env` matching

Env conditions are AND-ed. Use `env: { RETHUNK_ALLOW_SHELL: "1" }` to match bypass requests (bypass rules have `action: allow` and very high priority).

## Priority and precedence

1. Higher `priority` wins.
2. On equal priority: `deny` > `ask` > `nudge` > `allow`.
3. User rules in `rules.d/` are loaded after builtin packs and may override by providing higher priority.
4. Tier filtering: `strict` rules are excluded unless `config.toml` sets `tier = "strict"`.

## Template variables

`user_message`, `agent_message`, and `additional_context` support these substitutions:

| Variable | Value |
|----------|-------|
| `{command}` | The raw shell command string |
| `{program}` | The matched program (e.g. `git`) |
| `{subcommand}` | The matched subcommand (e.g. `commit`) |
| `{pack}` | The pack id |
| `{rule}` | The rule id |

## Example: deny `git commit`

```yaml
- id: deny-git-commit
  trigger: [pre_shell_exec, pre_shell_tool]
  match:
    shell_segments:
      - program: git
        subcommand: commit
  action: deny
  priority: 100
  user_message: "git commit is blocked. Use the user-rethunk-git MCP (batch_commit) instead."
  agent_message: "BLOCKED: {command}\n\nUse user-rethunk-git batch_commit MCP tool to commit changes. Do not attempt git commit again."
```

## Example: warn `git add`

```yaml
- id: warn-git-add
  trigger: [pre_shell_exec, pre_shell_tool]
  match:
    shell_segments:
      - program: git
        subcommand: add
  action: nudge
  priority: 50
  additional_context: "git add detected. Prefer user-rethunk-git MCP (batch_commit) which stages and commits atomically. git add is allowed but you should confirm with the user before proceeding."
```

## Example: bypass allowlist

```yaml
- id: bypass-allow
  trigger: [pre_shell_exec, pre_shell_tool]
  match:
    env:
      RETHUNK_ALLOW_SHELL: "1"
  action: allow
  priority: 1000
  user_message: "Buckler bypass: RETHUNK_ALLOW_SHELL=1 detected."
```
