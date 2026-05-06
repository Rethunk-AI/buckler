# Agent-safe Git Pack (`agent-git`)

The `agent-git` pack ships enabled by default. It makes it safe to give your AI coding agent access to `git` and `gh` without worrying about them destroying your version history or remote repositories.

## Design rationale

AI agents running `git` can cause irreversible damage:

- **`git push --force`** rewrites remote history, potentially losing teammates' work.
- **`git remote remove`** severs the connection between local and remote.
- **`git commit`** run unilaterally bypasses the MCP commit workflow, which is the correct, reviewable path in Rethunk-AI environments.

Buckler intercepts these commands before execution and either blocks them outright (deny) or injects steering context (nudge) to redirect the agent toward safe alternatives.

## Baseline rule matrix (default-on)

| Rule id | Trigger | Program | Subcommand / pattern | Decision | Notes |
|---------|---------|---------|---------------------|----------|-------|
| `bypass-allow` | pre_shell_exec, pre_shell_tool | any | `RETHUNK_ALLOW_SHELL=1` env | **Allow** | Emergency bypass, priority 1000 |
| `deny-git-commit` | pre_shell_exec, pre_shell_tool | `git` | `commit` | **Deny** | Includes `--amend`, `-C path commit` |
| `deny-git-push-force` | pre_shell_exec, pre_shell_tool | `git` | `push` + `--force\|-f` flag | **Deny** | Hard deny; use `--force-with-lease` (warn in baseline) |
| `deny-git-push-delete` | pre_shell_exec, pre_shell_tool | `git` | `push` + `--delete\|-d` flag | **Deny** | Remote branch deletion |
| `deny-git-push-refspec-delete` | pre_shell_exec, pre_shell_tool | `git` | `push` + `:branch` refspec | **Deny** | Implicit delete via empty src |
| `deny-git-push-mirror` | pre_shell_exec, pre_shell_tool | `git` | `push` + `--mirror` flag | **Deny** | Overwrites entire remote |
| `deny-git-remote-remove` | pre_shell_exec, pre_shell_tool | `git` | `remote remove` or `remote rm` | **Deny** | Remote deletion |
| `warn-git-add` | pre_shell_exec, pre_shell_tool | `git` | `add` | **Nudge** | Steering toward MCP; non-blocking |
| `warn-git-push-force-with-lease` | pre_shell_exec, pre_shell_tool | `git` | `push` + `--force-with-lease` | **Nudge** | Warn; baseline allows; strict denies |
| `nudge-mcp-available` | post_tool_success | any git/gh shell tool | — | **Nudge** | Reminds agent that MCP tools exist |

## Strict tier additions (`tier: strict`)

Enable via `config.toml`: `tier = "strict"`.

| Rule id | Trigger | Program | Subcommand / pattern | Decision |
|---------|---------|---------|---------------------|----------|
| `deny-git-push-force-with-lease-strict` | pre_shell_exec, pre_shell_tool | `git` | `push` + `--force-with-lease` | **Deny** |
| `deny-git-reset-hard` | pre_shell_exec, pre_shell_tool | `git` | `reset` + `--hard` | **Deny** |
| `deny-git-merge` | pre_shell_exec, pre_shell_tool | `git` | `merge` | **Deny** |
| `deny-git-rebase` | pre_shell_exec, pre_shell_tool | `git` | `rebase` | **Deny** |
| `deny-git-commit-tree` | pre_shell_exec, pre_shell_tool | `git` | `commit-tree` | **Deny** |
| `deny-git-remote-set-url` | pre_shell_exec, pre_shell_tool | `git` | `remote set-url` | **Deny** |

## False positive avoidance

The parser avoids common false positives:

| Pattern | Not blocked | Reason |
|---------|-------------|--------|
| `git log --grep=commit` | Not blocked | "commit" is an argument, not a subcommand |
| `git show HEAD~1` | Not blocked | `show` subcommand, not `commit` |
| `git branch commit-review` | Not blocked | `branch` subcommand |
| `git commit-graph write` | Blocked | `commit-graph` treated as subcommand starting with "commit" — intentional conservative match |

## Bypass

```bash
RETHUNK_ALLOW_SHELL=1 git commit -m "emergency"
```

The bypass rule has priority 1000 (higher than all git rules). Set `RETHUNK_ALLOW_SHELL=1` in the environment before the command.

## MCP steering (nudge)

The `nudge-mcp-available` rule injects `additional_context` into post-tool signals when the agent runs raw `git` or `gh` commands, reminding it to use the available MCP tools instead:

- `user-rethunk-git` / `batch_commit` for staging and committing
- `user-rethunk-github` for GitHub operations (PRs, issues, CI)
