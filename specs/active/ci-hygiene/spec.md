# Spec — ci-hygiene

| | |
|---|---|
| Status | DRAFT 060431ZMAY26 |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. Two CI gating gaps: (a) `shellcheck --severity=warning scripts/setup.sh` exits 1 today on `SC2034` (`BUCKLER_HOOK_PREFIX` declared but never used), suggesting either CI hasn't actually re-run since the constant was orphaned or the step is silently advisory; (b) `pyproject.toml` claims support for Python 3.11 / 3.12 / 3.13 but `ci.yml` runs only one `uv python install` per OS, so the matrix is implicit and the support promise is unverified. |

## Why

The classifiers in `pyproject.toml` (`Programming Language :: Python :: 3.11`, `…3.12`, `…3.13`) and the `requires-python = ">=3.11"` constraint are a contract with packagers and downstream users. CI must verify the contract or the contract is fiction. As of today, locally `python3` resolves to 3.14.4 — the actual tested version — and we'd ship a 3.11-incompat surprise in the next refactor.

The shellcheck gap is more pernicious. The CI workflow contains the step:

```yaml
- name: Shellcheck
  run: shellcheck --shell=bash --severity=warning scripts/setup.sh
```

with no `continue-on-error: true` and no `|| true`. If CI is actually running the step, it would have failed on every PR since `BUCKLER_HOOK_PREFIX` was orphaned. Either CI hasn't run shellcheck recently (workflow caching glitch, gating gap, or stale ref), or the step is being treated as advisory in some path. Either way, the job needs a known-good state and a known-failing state to be exercised before this can be relied on.

## In scope

### Python version matrix

- Add `python-version: ["3.11", "3.12", "3.13"]` as a matrix dimension to the `test` job in `.github/workflows/ci.yml`.
- Pin per-job via `uv python install ${{ matrix.python-version }}` (or the equivalent `astral-sh/setup-uv@v5` `python-version:` input — confirm which is current).
- Keep `fail-fast: false` so a 3.11-only failure doesn't cancel the 3.12 / 3.13 / 3.14 cells.
- Total cells become OS × Python = 3 × 3 = 9 (currently 3). Acceptable cost for the support promise.

### Resolve the shellcheck failure

- Decide and ratify (Q1): either delete `BUCKLER_HOOK_PREFIX` from `setup.sh:13` outright, or wire it into `_strip_hooks` / `_purge_legacy` so it's a single source of truth shared with the Python `BUCKLER_HOOK_PREFIX = "buckler:"` constant in `src/buckler/hooks.py:20`.
- Either path, `shellcheck --severity=warning` exits 0.

### Verify CI gating

- Land a one-commit "broken on purpose" branch (or a single PR) that introduces a deliberate shellcheck failure, push, confirm CI red. Then revert. This proves the step actually fails the build, closing the "is the gate even live" question.
- Document the matrix and the gating expectation in `CONTRIBUTING.md` "CI" section.

### Optional consistency check (small, fold-in if cheap)

- Add a tiny coherence test that confirms every classifier in `pyproject.toml` Programming-Language list has a corresponding matrix cell in `ci.yml`, and vice versa. Skip if it adds non-trivial complexity.

## Out of scope

- Python 3.14 in the matrix until a classifier promises it.
- Linting other shell scripts (only `setup.sh` ships in the repo right now).
- Speeding up CI cache or `uv` cache strategy.
- Adding the matrix to `release.yml` — the release builds one artifact and the matrix gating at PR time is sufficient.
- Migrating off GitHub Actions.

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Resolve `SC2034` by **delete** or by **use**? Proposal: **use** — pass the prefix into `_strip_hooks` and `_purge_legacy` so `setup.sh` and `buckler.hooks` share a single constant. Delete is simpler but loses the unification. | **Open** |
| Q2 | Matrix cell count: 3 × 3 = 9 cells acceptable for now? Proposal: **yes**. ARM macOS is the next likely add (`macos-14`), tracked separately. | **Open** |
| Q3 | Add the coherence check between classifiers and matrix? Proposal: **defer** — small payoff, easy to forget when classifiers change; revisit when a third dimension lands. | **Open** |
| Q4 | When the matrix expands and a job times out (`uv` cache miss × 9 cells), do we keep `enable-cache: true` or switch to a self-hosted cache? Proposal: **keep `enable-cache: true`**; revisit only if a job exceeds 5 minutes consistently. | **Open** |

## Acceptance

- A1. `.github/workflows/ci.yml` matrix tests Python 3.11, 3.12, 3.13 across `ubuntu-latest`, `macos-latest`, `windows-latest`.
- A2. `shellcheck --shell=bash --severity=warning scripts/setup.sh` exits 0 on a clean checkout of `main`.
- A3. CI is verified to actually fail on a shellcheck warning (one-shot deliberate-break smoke test, then reverted).
- A4. `CONTRIBUTING.md` "CI" section documents the matrix and the gating expectation.
- A5. `pyproject.toml` classifier list is unchanged (no scope creep) and matches the matrix cells.
- A6. Q-table ratified.
