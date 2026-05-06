# Tasks — parser-bypass-hardening

Status: DONE 051500ZMAY26

## P0

- [x] Ratify Q1–Q5.
- [x] Extend `_segment_command` for `&`, `|`, `\n`/`\r\n` (quote-aware).
- [x] Env / `env` stripping in `_parse_segment_tokens`.
- [x] Recurse `bash -c` / `sh -c` / `dash -c`, `$(…)`, backticks; depth cap; `xargs git …` heuristic.
- [x] `evaluate()` expansion failure path + env-only bypass override.
- [x] `tests/test_agent_git_redteam.py` + core coverage tests.
- [x] `SECURITY.md` + `CHANGELOG.md`.
- [x] 100% coverage.

## P1

- [x] Ruff noqa on intentionally complex parsers (`PLR091*`).

## P2

- [ ] Deeper POSIX parity (here-docs, `$'…'`) if proven exploitable.
