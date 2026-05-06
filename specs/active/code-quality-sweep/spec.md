# Spec — code-quality-sweep

| | |
|---|---|
| Status | DRAFT 060431ZMAY26 |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. One misleading test name (P5) plus a table of small smells (P9): individually trivial, collectively cohesive — bundled here as a single sweep so each item is acknowledged and lands rather than getting deferred indefinitely. |

## Why

Each of the items below is too small to warrant its own spec. They are also all small enough to keep deferring — the failure mode of a long-running project is that smells like these accumulate into a "we should clean this up someday" backlog that never gets a sponsor. Bundling them into one explicit sweep produces a single PR-shaped unit of work, sized for one focused afternoon, with each item visible as its own commit and acceptance row.

This is **not** a refactor. No external behavior changes; no contract changes; no parser semantic changes. Anything that touches user-facing behavior lives in a different spec (`parser-bypass-hardening`, `pack-gh-coverage`, `hooks-cross-platform-quoting`, `legacy-deprecation-window`, `docs-and-runbooks`, `ci-hygiene`).

## In scope

Each of the following is a discrete unit, intended to land as one commit. Acceptance rows below mirror the order.

### Test name correctness (P5)

`tests/test_core.py:222 TestCoreRemainingBranches.test_evaluate_rule_priority_tie_higher_severity_wins` is misnamed. It uses `git add .`, which only matches one rule (`warn-git-add` priority 50). There's no actual tie. The assertion `decision == "nudge"` passes because that's the only matching rule, not because of tie-breaking. The genuine tie-breaker test is the sibling at line 263 (`test_evaluate_priority_tie_higher_severity_wins`) which constructs two rules in a `tmp_path` pack.

Resolution (Q1): delete the misnamed test, OR rewrite it to genuinely tie two rules without `tmp_path`.

### File reading encoding (P9)

`src/buckler/cli.py:32` calls `Path(source).read_text()` without `encoding="utf-8"`. On Windows under `cp1252`, a payload containing non-ASCII shell characters can hit a decode error. Fix: explicit `encoding="utf-8"`.

### Template substitution safety (P9)

`src/buckler/core.py:262 _apply_template` does naïve sequential `.replace()`. If the value of `command` happens to contain `{program}`, it gets re-substituted on the next iteration (insertion-order dependent on Python dict iteration). Fix: switch to `str.format_map(_DefaultDict(str))` — one pass, missing keys leave the placeholder intact, no double-substitution.

### Audit log concurrency (P9)

`src/buckler/core.py:69` opens the audit log with `open("a")` and writes one line per `evaluate()` call. No `flock`, no atomic guard. Cursor invokes hooks serially per session today, but the moment Buckler is invoked by parallel hooks (or the planned Claude Code adapter sharing the same audit file), lines can interleave. Resolution (Q2): document the serial-invocation assumption in `HUMANS.md` "Audit log operations" — defer locking until there's a demonstrated race.

### Typed hook definitions (P9)

`src/buckler/hooks.py:22 _HOOK_DEFINITIONS` is `list[dict[str, Any]]`. mypy can't catch a typo in `failClosed` / `timeout` / `matchers`. Fix: `class HookDefinition(TypedDict, total=False)` and annotate the list. Strict mypy will then flag any drift.

### Dynamic adapter registry (P9)

`src/buckler/cli.py:103` hard-codes `--driver` `choices=["cursor"]`. The planned Claude Code adapter will need a second entry, easy to forget. Fix: build `choices` from `buckler.adapters.__all__` (or a small registry). Keep the default behavior (`cursor`) unchanged.

### `_is_windows` tightening (P9)

`src/buckler/paths.py:30` returns True if `COMSPEC` is set, even on Unix shells where a user re-exported it (rare but possible — some IDE setups). Fix: prefer `platform.system() == "Windows"` first; fall back to `COMSPEC` only when `OSTYPE in ("msys", "cygwin")`. Existing tests pass; add one parametrize row asserting Linux + `COMSPEC` set returns False.

### Coverage gate documented (P9)

`pyproject.toml:49` carries `--cov-fail-under=100`. New PR authors who add a module hit a confusing failure. Fix: document the policy in `CONTRIBUTING.md` "Testing" section; explain the `pragma: no cover` carve-out convention (`if __name__ == "__main__"` blocks and platform-conditional branches only).

### README badges audit (P9)

The README CI badge URL targets a private GitHub repo (`Rethunk-AI/buckler`). For non-org-member viewers, the badge will 404. Resolution (Q3): if the repo will go public on tag, leave the badge; if it stays private long-term, swap for a Shields.io static badge or a self-hosted alternative.

### CHANGELOG / version coherence (P9)

`__version__ = "0.1.0"` in `src/buckler/__init__.py` but `CHANGELOG.md` only has `[Unreleased]`, no `[0.1.0]` section. Either tag `0.1.0` (and move "Unreleased" entries under it) or set `__version__ = "0.1.0.dev0"` so `--version` output reflects the unreleased state. Resolution (Q4): wait for `parser-bypass-hardening` to land, then tag `0.1.0` as the first public release.

### Cursor adapter `workspace_roots` dedupe (P9)

`src/buckler/adapters/cursor.py:73-77` builds `workspace_roots` from `workspace_root` OR `cwd`. When both are present and distinct (e.g. multi-root workspace), `cwd` is silently dropped despite the field being plural. Fix: if both are present and distinct, include both in the array (preserving order: `workspace_root` first, then `cwd`).

## Out of scope

- Anything that changes external behavior (parser semantics, deny-rule shape, hook contract, exit codes).
- Bigger refactors (splitting `core.py` into modules, moving the audit-log into a separate package, replacing `argparse` with `click`, etc.).
- New features or new packs.
- Performance work.
- Anything covered by the other six specs.

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Misnamed `test_evaluate_rule_priority_tie_higher_severity_wins`: **delete** (the line-263 sibling already covers the actual semantics) or **rewrite** to genuinely tie two rules. Proposal: **delete**. | **Open** |
| Q2 | Audit-log concurrency: ship `flock` now or document serial-invocation assumption and defer? Proposal: **document and defer** — no observed race; locking adds Windows complexity. | **Open** |
| Q3 | README badge for a private repo: **leave** (assuming public-on-tag) or **swap** for self-hosted? Proposal: **leave** if the repo will go public when 0.1.0 ships; **swap** if not. Operator answer required. | **Open** |
| Q4 | CHANGELOG / version coherence: tag `0.1.0` now, set `0.1.0.dev0` placeholder, or stay `0.1.0` + Unreleased forever? Proposal: **`0.1.0.dev0`** until `parser-bypass-hardening` lands, then tag `0.1.0`. | **Open** |
| Q5 | Should the typed `HookDefinition` `TypedDict` use `total=False` (allow optional keys like `matchers`) or `total=True` with `NotRequired[…]` annotations (Python 3.11+)? Proposal: **`NotRequired`** — clearer at the use site, matches `requires-python = ">=3.11"`. | **Open** |
| Q6 | Cursor `workspace_roots` ordering when both `workspace_root` and `cwd` differ: `[workspace_root, cwd]` or `[cwd, workspace_root]`? Proposal: **`[workspace_root, cwd]`** — workspace is the broader context. | **Open** |

## Acceptance

- A1. `tests/test_core.py:222` resolved per Q1.
- A2. `Path(source).read_text(encoding="utf-8")` in `cli.py:32`.
- A3. `_apply_template` switched to a single-pass substitution mechanism (no double-substitution risk).
- A4. Audit-log behavior documented per Q2 (no code change unless Q2 flips).
- A5. `_HOOK_DEFINITIONS` typed via `TypedDict`; mypy strict still passes.
- A6. `--driver` `choices` built from a registry; `cursor` remains default.
- A7. `_is_windows` tightened per the spec; new parametrize row for the `COMSPEC`-on-Linux case.
- A8. `CONTRIBUTING.md` documents the `--cov-fail-under=100` gate and `pragma: no cover` convention.
- A9. README badge per Q3.
- A10. Version / CHANGELOG resolved per Q4.
- A11. Cursor adapter `workspace_roots` dedupes per Q6.
- A12. 100% coverage maintained.
- A13. All 11 items above land as one PR with one commit per item (or per logical pair where it makes sense).
- A14. Q-table ratified.
