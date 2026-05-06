# Tasks — hooks-cross-platform-quoting

Status: DRAFT 060431ZMAY26

## P0

- [ ] [HUMAN] Ratify Q1–Q4 (Windows list2cmdline, bare `-m` tail, fallback quoting, newline handling).
- [ ] Implement quoted `_buckler_command` using `shlex.quote` (Unix) and Windows rules per Q1; apply to `sys.executable` fallback (Q3).
- [ ] Refuse or escape paths with embedded newline per Q4 if ratified.
- [ ] Add parametrize / fixture tests for spaces and quote edge cases; round-trip `hooks.json` test (A3–A4).
- [ ] Update `docs/adapters/cursor.md` and `docs/paths.md` (A5–A6).
- [ ] Maintain 100% coverage (A7).
- [ ] Ratify Q-table (A8).

## P1

- [ ] Add brief comment in `hooks.py` pointing to docs for maintainers.

## P2

- [ ] Consider extracting shared quoting helper for future adapters.
