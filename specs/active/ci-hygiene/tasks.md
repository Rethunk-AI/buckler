# Tasks — ci-hygiene

Status: IN_PROGRESS 060452ZMAY26

## P0

- [x] [HUMAN] Ratify Q-table (Q1–Q4), especially Q1: delete `BUCKLER_HOOK_PREFIX` vs wire through `_strip_hooks` / `_purge_legacy`.
- [x] Add Python matrix to `.github/workflows/ci.yml` test job (ubuntu 3.11–3.13; macOS/Windows 3.13); pin installs per matrix; keep `fail-fast: false`.
- [x] Fix `scripts/setup.sh` so `shellcheck --shell=bash --severity=warning` exits 0 (after Q1 decision).
- [ ] Run one-shot deliberate shellcheck failure on CI; confirm red; revert (acceptance A3). _Procedure documented in `CONTRIBUTING.md`; operator runs on GitHub before/after merge._
- [x] Update `CONTRIBUTING.md` CI section: Python/OS matrix and blocking shellcheck expectation (acceptance A4).
- [x] Confirm `pyproject.toml` classifiers remain aligned with the matrix (acceptance A5).

## P1

- [x] Document matrix cost decision if Q2 ratified (comment in workflow or CONTRIBUTING).
- [x] If Q3 = implement: add coherence check test or script linking classifiers to matrix; otherwise record deferral in decision log / CONTRIBUTING.

## P2

- [ ] Revisit ARM macOS runner addition when sponsored (spec carry-forward note only).
