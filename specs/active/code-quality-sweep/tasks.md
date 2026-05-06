# Tasks — code-quality-sweep

## P0

- [ ] [HUMAN] Ratify Q1 (delete vs rewrite misnamed test), Q2 (audit log doc vs lock), Q3 (README badge), Q4 (version/CHANGELOG), Q5 (`TypedDict` style), Q6 (`workspace_roots` order).
- [ ] Resolve `tests/test_core.py` misnamed test per Q1 (acceptance A1).
- [ ] `read_text(encoding="utf-8")` in `src/buckler/cli.py` (A2).
- [ ] Single-pass `_apply_template` without double-substitution (A3).
- [ ] Document audit serial-invocation assumption in `HUMANS.md` per Q2 (A4).
- [ ] `TypedDict` for `_HOOK_DEFINITIONS`; mypy strict passes (A5).
- [ ] `--driver` choices from registry; default `cursor` (A6).
- [ ] `_is_windows` tightening + Linux+`COMSPEC` test row (A7).
- [ ] `CONTRIBUTING.md` coverage gate + `pragma: no cover` (A8).
- [ ] README badge per Q3 (A9).
- [ ] Version / `CHANGELOG` per Q4 (A10).
- [ ] Cursor adapter `workspace_roots` dedupe (A11).
- [ ] Maintain 100% coverage (A12).
- [ ] Land as one PR with one commit per item (or paired where sensible) (A13).
- [ ] Q-table ratified in spec (A14).

## P-1

- [ ] Spot-check each commit message follows conventional commits and explains “why” where non-obvious.

## P2

- [ ] Optional: grep for other `read_text()`/`write_text()` without encoding in package scope.
