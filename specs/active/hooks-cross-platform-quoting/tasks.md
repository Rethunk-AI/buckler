# Tasks — hooks-cross-platform-quoting

Status: IN_PROGRESS (claimed Bastion)

## P0

- [x] [HUMAN] Ratify Q1–Q4 (POSIX `shlex.quote` everywhere incl. Windows/Git Bash, bare `-m` tail, fallback quoting, refuse newline/CR).
- [x] Implement quoted `_buckler_command` via `shlex.quote` + newline refusal (Q4).
- [x] Add parametrize / fixture tests for spaces and quote edge cases; round-trip `hooks.json` test (A3–A4).
- [x] Update `docs/adapters/cursor.md` and `docs/paths.md` (A5–A6).
- [x] Maintain 100% coverage (A7).
- [x] Q-table ratified (A8).

## P1

- [x] Brief comment in `hooks.py` (`_HOOK_CMD_SUFFIX` / `_quote_hook_interpreter` docstrings).

## P2

- [ ] Consider extracting shared quoting helper for future adapters.
