# Plan — code-quality-sweep

## Overview

One bundled PR of small, behavior-preserving hygiene fixes called out in the P1–P10 review: tests, encoding, template substitution, typing, CLI adapter registry, Windows path detection, coverage docs, README badge, version/CHANGELOG alignment, and Cursor `workspace_roots`. Each item is intended as its own conventional commit; no contract or parser semantics changes.

## Preconditions

- Branch from latest `main`; keep `--cov-fail-under=100` green after every commit.
- Order commits to reduce conflict risk (e.g. tests before refactors that touch same files).

## Approach

Work through the spec’s discrete items in dependency-safe order:

1. **Tests:** Remove or rewrite the misnamed `test_evaluate_rule_priority_tie_higher_severity_wins` per Q1; rely on the existing tie-breaker test at line 263 if deleting.

2. **CLI / IO:** `Path.read_text(encoding="utf-8")` in `src/buckler/cli.py`.

3. **Templates:** Replace naive `.replace()` chain in `_apply_template` with `str.format_map` and a safe defaulting dict (spec proposes `_DefaultDict(str)` pattern).

4. **Audit log:** Per Q2, document serial-invocation assumption in `HUMANS.md` unless Q2 flips to locking.

5. **Typing:** Introduce `HookDefinition` `TypedDict` with `NotRequired[...]` per Q5; annotate `_HOOK_DEFINITIONS`.

6. **CLI drivers:** Build `--driver` choices from adapter registry (`buckler.adapters.__all__` or equivalent); default stays `cursor`.

7. **Paths:** Tighten `_is_windows` in `src/buckler/paths.py` per spec; add parametrize case for Linux + `COMSPEC` set.

8. **Docs:** `CONTRIBUTING.md` Testing section — coverage gate and `pragma: no cover` convention.

9. **README:** Badge strategy per Q3 (leave vs static badge).

10. **Versioning:** Resolve `__version__` / `CHANGELOG.md` per Q4 (`0.1.0.dev0` until parser spec lands, etc.).

11. **Cursor adapter:** Fix `workspace_roots` to include both `workspace_root` and `cwd` when distinct, order `[workspace_root, cwd]` per Q6.

## Dependencies

- Version/CHANGELOG coherence may wait on `parser-bypass-hardening` per Q4 — note in commit message if so.

## Risks

- `format_map` must preserve behavior for missing keys (placeholders stay).
- TypedDict changes may require adjusting tests or call sites if shapes drift.

## Verification

- `uv run pytest` with coverage at 100%.
- `uv run mypy` (or project-standard type check) clean.

## Out of scope reminder

No user-visible behavior change beyond fixes explicitly listed; no new packs or parser changes.
