---
name: buckler
description: >-
  Buckler Agent Gatehouse: install, configure, use, and troubleshoot the
  Buckler hook policy engine. Use when the user mentions Buckler, asks about
  the agent-git pack, wants to install or update Buckler, bypass a hook,
  add custom rules, or migrate from rethunk-mcp-nudge.py.
---

# Buckler — Agent Gatehouse Skill

**Buckler** is a harness-neutral policy engine that intercepts shell commands and tool calls from AI coding assistants. It evaluates declarative YAML rules and decides whether to allow, deny, ask, or nudge—before commands execute.

## Repository

`https://github.com/Rethunk-AI/buckler`

## Install / update / uninstall

```bash
# Install (Linux / macOS / Windows Git Bash)
curl -fsSL https://github.com/Rethunk-AI/buckler/releases/latest/download/setup.sh | bash -s install

# Migrate from rethunk-mcp-nudge.py
bash setup.sh install --purge-legacy

# Update to latest release
bash setup.sh update

# Uninstall (preserve config)
bash setup.sh uninstall

# Uninstall + remove config
bash setup.sh uninstall --purge-config
```

## Default behavior (agent-git pack)

| Command | Decision |
|---------|----------|
| `git commit` | Deny |
| `git push --force` / `-f` | Deny |
| `git push --delete` / mirror | Deny |
| `git remote remove` | Deny |
| `git add` | Nudge (warn; allowed) |
| `git push --force-with-lease` | Nudge (baseline); Deny (strict) |
| Benign `git` commands | Allow |

## Bypass (emergency)

```bash
RETHUNK_ALLOW_SHELL=1 git commit -m "emergency bypass"
```

## Debug

```bash
# Test a PolicyInput directly
echo '{"policy_io_version":"1","trigger":"pre_shell_exec","shell":{"command":"git commit -m test","cwd":"/tmp"}}' \
  | python -m buckler evaluate

# Check hooks.json wiring
python -m buckler.hooks status
```

## Adding custom rules

Add YAML files to `~/.config/buckler/rules.d/`. See [docs/rule-schema.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/rule-schema.md).

## Key documents

| Doc | Purpose |
|-----|---------|
| [HUMANS.md](https://github.com/Rethunk-AI/buckler/blob/main/HUMANS.md) | Operator guide (install, packs, bypass, troubleshooting) |
| [docs/troubleshooting.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/troubleshooting.md) | Hooks not firing, unexpected allow/deny, audit log, Windows quoting |
| [docs/agent-git.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/agent-git.md) | Full Git pack matrix |
| [docs/agent-gh.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/agent-gh.md) | Full GitHub CLI pack matrix |
| [docs/rule-schema.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/rule-schema.md) | YAML rule authoring reference |
| [docs/contracts/policy-io.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/contracts/policy-io.md) | PolicyInput/PolicyOutput contract |
| [docs/adapters/cursor.md](https://github.com/Rethunk-AI/buckler/blob/main/docs/adapters/cursor.md) | Cursor event mapping + hooks.json wiring |
| [ARCHITECTURE.md](https://github.com/Rethunk-AI/buckler/blob/main/ARCHITECTURE.md) | Core/adapter boundary, versioning, plugin RFC |
