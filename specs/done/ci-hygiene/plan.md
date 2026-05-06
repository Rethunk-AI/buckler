# Plan — ci-hygiene

## Overview

Align GitHub Actions with the Python support contract in `pyproject.toml` and restore confidence that `shellcheck` on `scripts/setup.sh` is a real gate. Work splits into: matrix expansion, fixing `SC2034` for `BUCKLER_HOOK_PREFIX`, proving the shellcheck step fails the workflow when broken, and documenting expectations in `CONTRIBUTING.md`.

## Preconditions

- Read `pyproject.toml` classifiers and `requires-python` before editing `.github/workflows/ci.yml`.
- Confirm current `astral-sh/setup-uv` / `uv python install` usage in `ci.yml` so matrix pins are idiomatic.
- Resolve Q1 (delete vs use `BUCKLER_HOOK_PREFIX`) before editing `setup.sh` — the chosen path must satisfy `shellcheck --severity=warning`.

## Approach

### Python matrix

Add a `python-version` axis `["3.11", "3.12", "3.13"]` to the test job, keep `fail-fast: false`, and ensure each job installs and runs tests against that interpreter (via `uv` as today). Total jobs: 3 OS × 3 Python = 9.

### Shellcheck

Either remove the unused `BUCKLER_HOOK_PREFIX` from `scripts/setup.sh` or thread it through `_strip_hooks` / `_purge_legacy` so the constant is referenced and stays aligned with `src/buckler/hooks.py` (`BUCKLER_HOOK_PREFIX`). Goal: `shellcheck --shell=bash --severity=warning scripts/setup.sh` exits 0.

### Gate proof

One deliberate failing change on a throwaway branch or PR, workflow goes red, then revert — proves the step is not advisory.

### Documentation

Update `CONTRIBUTING.md` CI section: matrix dimensions, that shellcheck is blocking, and optional classifier/matrix coherence test only if Q3 stays open as “implement.”

## Dependencies

- None blocking implementation except operator/product answers for the Q-table (matrix cost Q2, coherence Q3, cache Q4).
- Optional coherence test is lowest priority and may be explicitly deferred per Q3.

## Risks

- CI duration and quota: nine cells; mitigate with existing `uv` cache (`enable-cache: true` per Q4 proposal).
- Windows/macOS matrix flakes: treat as infrastructure; document if recurring.

## Verification

- Local: `shellcheck --shell=bash --severity=warning scripts/setup.sh`; `uv run pytest` on 3.11 locally if available.
- CI: green on `main` after merge; optional one-shot red proof for shellcheck per acceptance A3.

## Out of scope reminder

Per `spec.md`: Python 3.14 not in matrix until classifiers promise it; no release workflow matrix change; no migration off GitHub Actions.
