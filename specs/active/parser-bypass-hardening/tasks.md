# Tasks — parser-bypass-hardening

Status: DRAFT 060431ZMAY26

## P0

- [ ] [HUMAN] Ratify Q1–Q5 (parse-failure default, `commit-graph` alignment, env prefix, depth=3, pipe deny semantics).
- [ ] Extend segmentation for `&`, `|`, newline while respecting quotes (A1).
- [ ] Strip env-var prefixes and `env` wrapper in `_parse_segment` flow (A2).
- [ ] Implement bounded recursion for `bash -c` / `sh -c` / `$(...)` / backticks (A3).
- [ ] Add `tests/test_agent_git_redteam.py` covering bypass rows + benign cases (A4).
- [ ] Add `git commit-graph write` fixture per Q2 outcome (A5).
- [ ] Update `SECURITY.md` known bypasses + `CHANGELOG.md` discipline for closures (A6).
- [ ] Maintain 100% coverage (A7).
- [ ] Run `python -m buckler evaluate` smoke on carry-forward examples (A8).
- [ ] Ratify Q-table (A9).

## P1

- [ ] Document recursion bound and failure behavior in `ARCHITECTURE.md` or `docs/rule-schema.md` if maintainers need a single pointer.

## P2

- [ ] Track ANSI-C quotes / here-doc escapes if redteam finds gaps.
