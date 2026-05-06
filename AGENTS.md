# AGENTS.md

LLM + dev orientation. **This file is intentionally thin** — it points at the canon files and lists the contract-change rules.

## Canon pointers

| Topic | File |
|-------|------|
| Operator guide (install, packs, bypass, troubleshooting) | [HUMANS.md](HUMANS.md) |
| Core/adapter boundary, `policy_io_version` evolution, architecture | [ARCHITECTURE.md](ARCHITECTURE.md) |
| Harness-neutral `PolicyInput` / `PolicyOutput` JSON schema | [docs/contracts/policy-io.md](docs/contracts/policy-io.md) |
| YAML rule schema (triggers, match fields, actions, priorities) | [docs/rule-schema.md](docs/rule-schema.md) |
| Path resolution (XDG, Windows Git Bash, env overrides) | [docs/paths.md](docs/paths.md) |
| Cursor adapter mapping + `hooks.json` wiring | [docs/adapters/cursor.md](docs/adapters/cursor.md) |
| Adapter index + how to add a harness | [docs/adapters/README.md](docs/adapters/README.md) |
| Default Git pack operator matrix | [docs/agent-git.md](docs/agent-git.md) |
| Dev setup, commit conventions, MCP policy, CI | [CONTRIBUTING.md](CONTRIBUTING.md) |
| Threat model, Cosign verification, vulnerability reporting | [SECURITY.md](SECURITY.md) |
| Troubleshooting runbook (hooks, policy, audit log) | [docs/troubleshooting.md](docs/troubleshooting.md) |

## Contract-change rules

When you change a contract, update **all** canon locations:

| Contract | What to update |
|----------|---------------|
| `PolicyInput` / `PolicyOutput` schema | [docs/contracts/policy-io.md](docs/contracts/policy-io.md) + [docs/contracts/policy-io.schema.json](docs/contracts/policy-io.schema.json) + bump `policy_io_version` |
| Rule YAML schema (new field / trigger) | [docs/rule-schema.md](docs/rule-schema.md) + `buckler.core` implementation |
| Path layout (new dir / env var) | [docs/paths.md](docs/paths.md) + `buckler.paths` + `scripts/setup.sh` |
| New or renamed adapter | [docs/adapters/README.md](docs/adapters/README.md) + adapter doc + adapter module |
| CLI surface (add / remove / rename subcommand) | [HUMANS.md](HUMANS.md) + help strings in `buckler.cli` |
| New builtin pack | [HUMANS.md](HUMANS.md) pack table + pack YAML + pack doc |

## Development workflow

All implementation work — commit conventions, CI steps, MCP policy, and the stop-if-MCP-unavailable rule — is in [CONTRIBUTING.md](CONTRIBUTING.md).
