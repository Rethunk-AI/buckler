# Buckler — Agent Gatehouse

> **Protect your system from unauthorized agentic actions.** Declarative, multi-harness policy engine that intercepts shell commands and tool calls from AI coding assistants—before they cause damage.

[![CI](https://github.com/Rethunk-AI/buckler/actions/workflows/ci.yml/badge.svg)](https://github.com/Rethunk-AI/buckler/actions/workflows/ci.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://python.org)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Checked with mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Summary

Buckler is a **harness-neutral** policy engine: declarative YAML rules evaluate normalized signals from any AI coding assistant and decide whether to **allow**, **deny**, **ask**, or **nudge**—independent of which harness fired the hook. The `agent-git` and `agent-gh` packs ship enabled by default, blocking uncontrolled `git` commits, force-pushes, remote destruction, and destructive `gh` commands out of the box.

## Feature Highlights

- **Harness-neutral core** — the evaluator knows nothing about Cursor's `hooks.json`; only thin adapters do
- **Declarative YAML packs** — rules match on abstract trigger kinds, not harness-specific strings
- **`agent-git` + `agent-gh` packs** — deny uncontrolled git commits / force-push / remote destruction; deny destructive `gh` subcommands; nudge toward MCP tools
- **Cosign-signed releases** — every release tarball is verified before install
- **Cross-platform** — Linux, macOS, Windows (Git Bash)

## Documentation

| Audience | File |
|----------|------|
| **Install, configure, bypass, troubleshoot** | [HUMANS.md](HUMANS.md) |
| **LLM / dev internals, contract rules** | [AGENTS.md](AGENTS.md) |
| **Architecture & adapter boundary** | [ARCHITECTURE.md](ARCHITECTURE.md) |
| **Commit conventions, CI, dev setup** | [CONTRIBUTING.md](CONTRIBUTING.md) |
| **Threat model, Cosign verification, disclosure** | [SECURITY.md](SECURITY.md) |
| **Troubleshooting (hooks, policy, audit log)** | [docs/troubleshooting.md](docs/troubleshooting.md) |
| Rule YAML schema | [docs/rule-schema.md](docs/rule-schema.md) |
| Default `agent-git` pack matrix | [docs/agent-git.md](docs/agent-git.md) |
| Default `agent-gh` pack matrix | [docs/agent-gh.md](docs/agent-gh.md) |
| Path resolution (XDG, Windows, env overrides) | [docs/paths.md](docs/paths.md) |
