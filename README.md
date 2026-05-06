# Buckler — Agent Gatehouse

> **Protect your system from unauthorized agentic actions.** Buckler is a declarative, multi-harness policy engine that intercepts shell commands and tool calls from AI coding assistants—before they cause damage.

[![CI](https://github.com/Rethunk-AI/buckler/actions/workflows/ci.yml/badge.svg)](https://github.com/Rethunk-AI/buckler/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## What is Buckler?

Buckler is an **Agent Gatehouse**: a harness-neutral policy engine that sits between your AI coding assistant and your shell. It evaluates declarative YAML rules against normalized signals, then decides whether to **allow**, **deny**, or **warn** the action—independent of which tool fired the hook.

```
Harness (Cursor / Claude Code / …)
         │  native hook JSON
         ▼
   ┌─────────────┐
   │   Adapter   │  translates to/from PolicyInput / PolicyOutput
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │  buckler.core│  evaluate(PolicyInput) → PolicyOutput
   └──────┬──────┘
          │
   ┌──────▼──────┐
   │  YAML Packs │  declarative rules, command-agnostic
   └─────────────┘
```

### Key properties

- **Harness-neutral core.** The evaluator knows nothing about Cursor's `hooks.json` or Claude Code's hook file. Only thin adapters do.
- **Command-agnostic packs.** Rules match on abstract trigger kinds (`pre_shell_exec`, `pre_shell_tool`, `post_tool_success`) and fields—not on harness-specific strings.
- **Git pack included.** The `agent-git` pack ships enabled by default: deny uncontrolled commits, deny force-push and remote destruction, warn on `git add`, nudge toward MCP tools.
- **Cosign-signed releases.** Every release tarball is signed keylessly via Sigstore—`setup.sh` verifies before installing.
- **Cross-platform.** Linux, macOS, Windows (Git Bash).

---

## Quickstart (Cursor)

```bash
# Install (Linux / macOS / Windows Git Bash)
curl -fsSL https://github.com/Rethunk-AI/buckler/releases/latest/download/setup.sh | bash -s install
```

That's it. `setup.sh` verifies the Cosign signature, unpacks Buckler into `~/.local/share/buckler/`, and merges the required entries into `~/.cursor/hooks.json`.

Restart Cursor and Buckler is live.

### Manual verify-before-run

```bash
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/setup.sh
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/buckler-latest.tar.gz
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/buckler-latest.tar.gz.bundle
cosign verify-blob buckler-latest.tar.gz \
  --bundle buckler-latest.tar.gz.bundle \
  --certificate-identity-regexp "https://github.com/Rethunk-AI/buckler/.github/workflows/release.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
bash setup.sh install
```

---

## Default Git pack (`agent-git`)

The bundled `agent-git` pack makes it safe to give your agents access to `git` and `gh` without worrying about them destroying your remotes.

| Action | Decision | Examples |
|--------|----------|----------|
| `git commit` | **Deny** | Any variant: `-C`, `--amend`, `git -C path commit` |
| `git push --force` / `--delete` / `:branch` | **Deny** | Remote-destructive push variants |
| `git remote remove` / `git remote set-url` | **Deny** | Baseline; configurable to warn |
| `git push --mirror` | **Deny** | Mirror wipes the remote |
| `git add` | **Warn** | Non-blocking; steers agent toward MCP |
| Raw `git` / `gh` (when MCP available) | **Nudge** | Context injected post-tool |

Bypass for one command: set `RETHUNK_ALLOW_SHELL=1` in the command environment.

Full matrix: [docs/agent-git.md](docs/agent-git.md).

---

## Packs

Packs are YAML files that define rules. Buckler ships with:

| Pack | Enabled by default | Purpose |
|------|--------------------|---------|
| `agent-git` | Yes | Safe git + MCP steering |

**User rules** live in `$XDG_CONFIG_HOME/buckler/rules.d/*.yaml` (same schema, merged after builtin packs). See [docs/rule-schema.md](docs/rule-schema.md).

---

## Multi-harness

Buckler v1 ships the **Cursor** adapter. Other adapters map the same core:

| Harness | Status | Notes |
|---------|--------|-------|
| Cursor | **Shipped** | `hooks.json` wiring via `setup.sh` |
| Claude Code | Stub | Adapter documented; ships when hook schema stabilizes |
| Generic | **Shipped** | `buckler evaluate --input policy.json` for CI / custom wiring |

See [docs/adapters/README.md](docs/adapters/README.md).

---

## Operator guide

For installation, configuration, bypass, and troubleshooting: see [HUMANS.md](HUMANS.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Buckler itself is governed by the same Git pack it ships.

## Security

See [SECURITY.md](SECURITY.md) for the threat model, Cosign verification copy-paste, and vulnerability reporting.

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for the core/adapter boundary, `policy_io_version` evolution, and the signed-plugin RFC.
