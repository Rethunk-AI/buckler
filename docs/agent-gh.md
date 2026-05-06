# Agent-safe GitHub CLI Pack (`agent-gh`)

The `agent-gh` pack ships enabled by default alongside [`agent-git`](agent-git.md). It adds baseline **deny** rules for destructive `gh` subcommands so operators are not misled by raw shell access to the GitHub CLI.

## Baseline rule matrix (default-on)

| Rule id | Trigger | Program | Subcommand / pattern | Decision | Notes |
|---------|---------|---------|---------------------|----------|-------|
| `bypass-allow` | pre_shell_exec, pre_shell_tool | any | `RETHUNK_ALLOW_SHELL=1` env | **Allow** | Same emergency bypass as `agent-git` |
| `deny-gh-repo-delete` | pre_shell_exec, pre_shell_tool | `gh` | `repo delete` | **Deny** | Irreversible |
| `deny-gh-repo-archive` | pre_shell_exec, pre_shell_tool | `gh` | `repo archive` | **Deny** | Read-only archive |
| `deny-gh-release-delete` | pre_shell_exec, pre_shell_tool | `gh` | `release delete` | **Deny** | |
| `deny-gh-release-delete-asset` | pre_shell_exec, pre_shell_tool | `gh` | `release delete-asset` | **Deny** | |
| `deny-gh-pr-close-delete-branch` | pre_shell_exec, pre_shell_tool | `gh` | `pr close` + `--delete-branch` | **Deny** | Plain `gh pr close` remains allow |
| `deny-gh-api-delete` | pre_shell_exec, pre_shell_tool | `gh` | `api` + `-X DELETE` or `--method DELETE` | **Deny** | Case-insensitive method token |
| `deny-gh-secret-remove` | pre_shell_exec, pre_shell_tool | `gh` | `secret remove` | **Deny** | |
| `deny-gh-ssh-key-delete` | pre_shell_exec, pre_shell_tool | `gh` | `ssh-key delete` | **Deny** | Account SSH keys |
| `deny-gh-gpg-key-delete` | pre_shell_exec, pre_shell_tool | `gh` | `gpg-key delete` | **Deny** | Account GPG keys |
| `nudge-mcp-github-cli` | post_tool_success | `gh` | — | **Nudge** | Steer toward MCP |

## Read-only examples (remain allow)

Examples: `gh repo view`, `gh pr list`, `gh issue list`, `gh release list`, `gh pr close 42` (without `--delete-branch`).

## Disabling

Use `pack_override` in `config.toml` (see [rule-schema.md](rule-schema.md)) to disable `agent-gh` or `agent-git` independently.

## Parser note

Composite `gh` subcommands (`repo delete`, `release delete-asset`, `pr close`, …) are recognized by Buckler’s segment parser; `gh api` DELETE matching looks for `-X DELETE` or `--method DELETE` pairs in the segment.
