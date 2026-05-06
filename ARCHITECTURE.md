# Architecture

## Overview

Buckler is a **harness-neutral policy engine**. Its core evaluator knows nothing about Cursor's `hooks.json` or Claude Code's hook config. Only thin adapters do.

```
┌─────────────────────────────────────────────┐
│                  Harnesses                  │
│  Cursor hooks   Claude Code hooks   Other   │
└────────┬──────────────┬───────────────┬─────┘
         │              │               │
         ▼              ▼               ▼
┌─────────────────────────────────────────────┐
│                  Adapters                   │
│  buckler.adapters.cursor  (v1 — shipped)    │
│  buckler.adapters.claude  (stub)            │
│  buckler evaluate CLI     (generic)         │
└────────────────────┬────────────────────────┘
                     │ PolicyInput (JSON)
                     ▼
┌─────────────────────────────────────────────┐
│             buckler.core                    │
│  evaluate(PolicyInput) → PolicyOutput       │
│  No harness imports.                        │
└────────────────────┬────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────┐
│               YAML Packs                    │
│  packs/agent-git.yaml   (default-on)        │
│  ~/.config/buckler/rules.d/*.yaml           │
└─────────────────────────────────────────────┘
```

## Core / adapter boundary

**The invariant:** `buckler.core` may only import from:
- The Python standard library
- `buckler.pack_loader` (which is also harness-free)
- `buckler.__init__` (constants)

If a proposed change to `buckler.core` requires importing `buckler.adapters.*` or any harness-specific module, that code belongs in an adapter or in the CLI dispatch layer.

This boundary is verified in practice by the test split:
- `tests/test_core.py` — works only with `PolicyInput` JSON fixtures; passes without any Cursor dependency.
- `tests/test_adapter_cursor.py` — imports from `buckler.adapters.cursor` and uses Cursor-shaped fixtures.

## `policy_io_version` evolution

The version field in `PolicyInput` and `PolicyOutput` is a monotonically increasing string integer (`"1"`, `"2"`, …).

| Kind of change | Requires version bump? |
|---------------|------------------------|
| Add an optional field to `PolicyInput` or `PolicyOutput` | No |
| Remove a field | Yes |
| Rename a required field | Yes |
| Change the semantics of an existing field | Yes |
| Add a new `trigger` value | No (backward-compatible extension) |
| Rename a `trigger` value | Yes |

When the version is bumped:
1. Update `policy_io_version` constant in `buckler/__init__.py`.
2. Update `docs/contracts/policy-io.md` with a migration section.
3. Update `docs/contracts/policy-io.schema.json` (add new version to enum or use anyOf).
4. Adapters must check `policy_io_version` and raise `PolicyError` for unsupported versions.
5. Document the bump in `CHANGELOG.md` (or release notes).

## Pack model

Packs are YAML files processed by `buckler.pack_loader.load_packs()`:

1. **Builtin packs** from `buckler.paths.packs_dir()` (the installed `packs/` directory), sorted by filename.
2. **User overlays** from `buckler.paths.user_rules_dir()` (`~/.config/buckler/rules.d/*.yaml`), sorted alphabetically.

Rule precedence: higher `priority` wins; ties broken by action severity (`deny > ask > nudge > allow`).

Tier filtering: `strict` rules are excluded unless `config.toml` sets `tier = "strict"`.

## Adapter design

Each adapter is a module with two pure functions:

```python
def adapt_input(raw: dict) -> dict:  # returns PolicyInput
    ...

def adapt_output(output: dict, raw_input: dict) -> dict:  # returns harness response
    ...
```

The adapter maps the harness's native event names to abstract `trigger` values (`pre_shell_exec`, `pre_shell_tool`, `post_tool_success`, `post_tool_failure`). Rules reference only these abstract triggers, so they work unchanged across adapters.

## CLI dispatch

```
buckler [--driver cursor]          → cursor adapter (reads stdin, writes stdout)
buckler evaluate [--input/-i F]    → harness-neutral (reads PolicyInput, writes PolicyOutput)
python -m buckler.hooks merge      → idempotent hooks.json update
python -m buckler.hooks strip      → remove Buckler entries from hooks.json
python -m buckler.hooks status     → show current Buckler entries
```

The `BUCKLER_DRIVER` environment variable sets the default driver (default: `cursor`).

## Path resolver

`buckler.paths` is the single source of truth for all file system paths. `scripts/setup.sh` mirrors its logic in Bash. If either changes, both must change together.

See [docs/paths.md](docs/paths.md).

## Signed-plugin RFC (future)

This is not implemented in v1 but reserved for future exploration:

**Goal:** Allow third-party packs to be distributed as signed artifacts that `setup.sh update` can fetch and verify separately from the core Buckler release.

**Design sketch:**
- A `plugin` top-level key in a YAML pack declares a pack as a plugin with a registry URL and a Cosign bundle reference.
- `buckler plugin install <name>` fetches, verifies, and installs into `~/.local/share/buckler/plugins/`.
- Plugins are loaded after builtin packs and user rules.
- The plugin registry is out of scope for v1.

This RFC exists to prevent `buckler.core` from assuming it is the only source of packs, and to keep the pack loading architecture extensible.
