# Tasks — ci-hygiene

Status: DONE 060455ZMAY26 — Python matrix (ubuntu 3.11–3.13, mac/win 3.13), setup.sh shellcheck SC2034 fix via BUCKLER_HOOK_PREFIX, coherence test, CONTRIBUTING CI docs, deliberate shellcheck CI red proof (run 25417202183).

## P0

- [x] [HUMAN] Ratify Q-table (Q1–Q4), especially Q1: delete `BUCKLER_HOOK_PREFIX` vs wire through `_strip_hooks` / `_purge_legacy`.
- [x] Add Python matrix to `.github/workflows/ci.yml` test job (ubuntu 3.11–3.13; macOS/Windows 3.13); pin installs per matrix; keep `fail-fast: false`.
- [x] Fix `scripts/setup.sh` so `shellcheck --shell=bash --severity=warning` exits 0 (after Q1 decision).
- [x] Run one-shot deliberate shellcheck failure on CI; confirm red; revert (acceptance A3). Draft PR #1 (since closed): shellcheck job failed with SC2034 on `SHELLCHECK_PROOF_SC2034` (GitHub Actions run `25417202183`); branch removed after close.
- [x] Update `CONTRIBUTING.md` CI section: Python/OS matrix and blocking shellcheck expectation (acceptance A4).
- [x] Confirm `pyproject.toml` classifiers remain aligned with the matrix (acceptance A5).

## P1

- [x] Document matrix cost decision if Q2 ratified (comment in workflow or CONTRIBUTING).
- [x] If Q3 = implement: add coherence check test or script linking classifiers to matrix; otherwise record deferral in decision log / CONTRIBUTING.

## P2

- [ ] Revisit ARM macOS runner addition when sponsored (spec carry-forward note only).
