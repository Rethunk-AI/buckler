# Tasks — code-quality-sweep

Status: DONE 060616ZMAY26 — Code quality sweep: template format_map, utf-8 CLI IO, TypedDict hooks, adapter registry, paths Windows heuristic, workspace_roots pair, HUMANS audit note, CONTRIBUTING coverage, CHANGELOG 0.1.0; misnamed test removed; 100% coverage.

## P0

- [x] [HUMAN] Ratify Q1 (delete vs rewrite misnamed test), Q2 (audit log doc vs lock), Q3 (README badge), Q4 (version/CHANGELOG), Q5 (`TypedDict` style), Q6 (`workspace_roots` order).
- [x] Resolve `tests/test_core.py` misnamed test per Q1 (acceptance A1).
- [x] `read_text(encoding="utf-8")` in `src/buckler/cli.py` (A2).
- [x] Single-pass `_apply_template` without double-substitution (A3).
- [x] Document audit serial-invocation assumption in `HUMANS.md` per Q2 (A4).
- [x] `TypedDict` for `_HOOK_DEFINITIONS`; mypy strict passes (A5).
- [x] `--driver` choices from registry; default `cursor` (A6).
- [x] `_is_windows` tightening + Linux+`COMSPEC` test row (A7).
- [x] `CONTRIBUTING.md` coverage gate + `pragma: no cover` (A8).
- [x] README badge per Q3 (A9).
- [x] Version / `CHANGELOG` per Q4 (A10).
- [x] Cursor adapter `workspace_roots` dedupe (A11).
- [x] Maintain 100% coverage (A12).
- [x] Land as one PR with one commit per item (or paired where sensible) (A13).
- [x] Q-table ratified in spec (A14).

## P1

- [x] Spot-check each commit message follows conventional commits and explains “why” where non-obvious.

## P2

- [ ] Optional: grep for other `read_text()`/`write_text()` without encoding in package scope.
