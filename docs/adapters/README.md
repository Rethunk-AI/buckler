# Adapters

Adapters translate between a harness's native hook JSON and Buckler's harness-neutral `PolicyInput` / `PolicyOutput` contract (see [docs/contracts/policy-io.md](../contracts/policy-io.md)).

## Available adapters

| Adapter | Module | Status | Harness docs |
|---------|--------|--------|-------------|
| **Cursor** | `buckler.adapters.cursor` | Shipped (v1) | [cursor.md](cursor.md) |
| **Claude Code** | `buckler.adapters.claude` | Stub | [claude-code.md](claude-code.md) |
| **Generic** | (CLI `evaluate` subcommand) | Shipped | [policy-io contract](../contracts/policy-io.md) |

## How adapters work

An adapter is a thin translation layer with two responsibilities:

1. **`adapt_input(raw: dict) -> PolicyInput`** — Read the harness's stdin JSON, identify the event, and populate `PolicyInput` fields.
2. **`adapt_output(output: PolicyOutput, raw: dict) -> dict`** — Translate `PolicyOutput` back into the harness's expected stdout JSON format.

The adapter may also set the exit code if the harness uses exit codes for flow control (Cursor does not for `beforeShellExecution` — it reads `permission` from stdout JSON).

## Contributing a new adapter

1. Create `src/buckler/adapters/<harness>.py`:
   - Implement `adapt_input(raw: dict) -> PolicyInput`.
   - Implement `adapt_output(output: PolicyOutput, raw_input: dict) -> dict`.
   - Map the harness's event names to abstract `trigger` values.
2. Register the adapter in `buckler.cli` under `--driver <harness>`.
3. Add golden test fixtures in `tests/fixtures/adapters/<harness>/`.
4. Write tests in `tests/test_adapter_<harness>.py`.
5. Document the field mapping in `docs/adapters/<harness>.md`.
6. Update this README's adapter table and `AGENTS.md`.

## Adapter contract

- Adapters **must not** import from `buckler.core`'s internals—use the public `evaluate()` function.
- Adapters **must not** load packs or apply rules themselves.
- Adapters **may** normalize harness-specific fields (e.g. merge tool input fields into `shell.command` when the Cursor `Shell` tool fires `beforeShellExecution`).
- Adapters **must** propagate `env` fields relevant to bypass detection (`RETHUNK_ALLOW_SHELL`, etc.).
