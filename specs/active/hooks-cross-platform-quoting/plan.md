# Plan — hooks-cross-platform-quoting

## Overview

Fix `_buckler_command` in `src/buckler/hooks.py` so the generated `hooks.json` `command` string quotes the interpreter path correctly on Unix (`shlex.quote`) and Windows (`subprocess.list2cmdline` semantics). Add regression tests for paths with spaces and edge quotes; document the contract in `docs/adapters/cursor.md` and `docs/paths.md`.

## Preconditions

- Ratify Q1–Q4 (Windows quoting mechanism, bare suffix tokens, quote `sys.executable` fallback, newline refusal).

## Approach

### Implementation

- Centralize platform-specific quoting helper using `buckler.paths._is_windows()`.
- Always quote `venv_python` and `sys.executable` fallback per Q3.
- Optionally detect newline in path and error clearly per Q4.

### Tests

- Extend `tests/test_hooks.py::TestHooks::test_buckler_command_*` with Linux/macOS and Windows-mocked cases; edge cases for embedded quotes.
- Add round-trip test: write JSON, parse `command` field, recover `argv[0]`.

### Docs

- `docs/adapters/cursor.md`: shell string vs argv; operators hand-editing must quote.
- `docs/paths.md`: align with actual quoting behavior (remove inaccurate promises).

## Dependencies

- None hard; Claude Code adapter can reuse helper later (out of scope).

## Risks

- Cursor command parsing assumptions — stick to cmd.exe-style on Windows per Q1.
- Over-quoting `-m buckler` tokens — keep suffix bare per Q2.

## Verification

- Full pytest + 100% coverage.
- Manual smoke: generated `hooks.json` fragment with space path on relevant OS if available.

## Out of scope reminder

No `setup.sh` quoting changes beyond indirect behavior; no audit logging of command string here.
