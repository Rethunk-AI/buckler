# Migration from `rethunk-mcp-nudge.py`

If you previously used the `rethunk-mcp-nudge.py` hook in `~/.cursor/hooks.json`, Buckler supersedes it entirely. The `agent-git` pack ports and improves all nudge rules from the legacy script.

## What changed

| Legacy (`rethunk-mcp-nudge.py`) | Buckler (`agent-git` pack) |
|---------------------------------|---------------------------|
| Shell heuristic: detect `git commit` in `beforeShellExecution` | Proper shlex parser with global-option skipping, segment boundary handling |
| Shell heuristic: detect raw `git`/`gh` in `postToolUse` | `nudge-mcp-available` rule on `post_tool_success` |
| Single Python script, no tests | Tested rule engine with 64 passing tests |
| Hardcoded rules | Declarative YAML pack; user-extensible via `rules.d/` |
| Only `beforeShellExecution` + `postToolUse` | Three hooks: `beforeShellExecution`, `preToolUse`, `postToolUse` |
| No bypass | `RETHUNK_ALLOW_SHELL=1` bypass with priority 1000 |
| No force-push protection | `deny-git-push-force`, `deny-git-push-delete`, `deny-git-push-mirror` |
| No remote-remove protection | `deny-git-remote-remove` |

## Migration steps

### Option 1: Automatic (recommended)

```bash
bash setup.sh install --purge-legacy
```

The `--purge-legacy` flag removes `rethunk-mcp-nudge.py` entries from `~/.cursor/hooks.json` during install.

### Option 2: Manual

1. Install Buckler normally:
   ```bash
   bash setup.sh install
   ```

2. Open `~/.cursor/hooks.json` and remove any entries whose `command` includes `rethunk-mcp-nudge.py`.

3. Verify Buckler hooks are present:
   ```bash
   python -m buckler.hooks status
   ```

## Behavior differences to be aware of

- **`git add` is now a nudge, not a block.** The legacy script warned on `git add`; Buckler's baseline tier does the same (non-blocking nudge). This is intentional.
- **Force-push and remote deletion are now hard denies.** The legacy script did not block these. Buckler denies them at baseline.
- **`preToolUse` hook is new.** Buckler adds defense-in-depth by also intercepting the Cursor `Shell` tool call before it becomes a shell execution.
- **MCP nudge context is richer.** The `nudge-mcp-available` rule injects a more detailed message listing specific MCP tools and their use cases.
