# Tasks — ci-hygiene

Status: DRAFT 060431ZMAY26

## P0

- [ ] [HUMAN] Ratify Q-table (Q1–Q4), especially Q1: delete `BUCKLER_HOOK_PREFIX` vs wire through `_strip_hooks` / `_purge_legacy`.
- [ ] Add `python-version: ["3.11", "3.12", "3.13"]` matrix to `.github/workflows/ci.yml` test job; pin installs per matrix; keep `fail-fast: false`.
- [ ] Fix `scripts/setup.sh` so `shellcheck --shell=bash --severity=warning` exits 0 (after Q1 decision).
- [ ] Run one-shot deliberate shellcheck failure on CI; confirm red; revert (acceptance A3).
- [ ] Update `CONTRIBUTING.md` CI section: Python/OS matrix and blocking shellcheck expectation (acceptance A4).
- [ ] Confirm `pyproject.toml` classifiers remain aligned with the matrix (acceptance A5).

## P1

- [ ] Document matrix cost decision if Q2 ratified (comment in workflow or CONTRIBUTING).
- [ ] If Q3 = implement: add coherence check test or script linking classifiers to matrix; otherwise record deferral in decision log / CONTRIBUTING.

## P2

- [ ] Revisit ARM macOS runner addition when sponsored (spec carry-forward note only).
