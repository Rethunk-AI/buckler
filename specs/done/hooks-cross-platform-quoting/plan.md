# Plan — hooks-cross-platform-quoting

## Overview

Fix `_buckler_command` in `src/buckler/hooks.py` so the generated `hooks.json` `command` string quotes the interpreter path with POSIX **`shlex.quote` on all platforms** (bash / Git Bash on Windows). Add regression tests for paths with spaces and edge quotes; document the contract in `docs/adapters/cursor.md` and `docs/paths.md`.

## Preconditions

- Ratify Q1–Q4 (Windows quoting mechanism, bare suffix tokens, quote `sys.executable` fallback, newline refusal).

## Approach

### Implementation

- Centralize `_quote_hook_interpreter` using `shlex.quote` (no Windows/cmd split).
- Always quote `venv_python` and `sys.executable` fallback per Q3.
- Optionally detect newline in path and error clearly per Q4.

### Tests

- Extend `tests/test_hooks.py::TestHooks` with parametrized paths (spaces, embedded quotes, `C:/...` forms); round-trip via `shlex.split(..., posix=True)`.
- Add round-trip test: write JSON, parse `command` field, recover `argv[0]`.

### Docs

- `docs/adapters/cursor.md`: shell string vs argv; operators hand-editing must quote.
- `docs/paths.md`: align with actual quoting behavior (remove inaccurate promises).

## Dependencies

- None hard; Claude Code adapter can reuse helper later (out of scope).

## Risks

- Cursor invokes hooks with bash / Git Bash posture on Windows — POSIX quoting only.
- Over-quoting `-m buckler` tokens — keep suffix bare per Q2.

## Verification

- Full pytest + 100% coverage.
- Manual smoke: generated `hooks.json` fragment with space path on relevant OS if available.

## Out of scope reminder

No `setup.sh` quoting changes beyond indirect behavior; no audit logging of command string here.
