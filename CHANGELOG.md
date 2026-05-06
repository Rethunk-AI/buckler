# Changelog

All notable changes to Buckler are documented here. The format follows the spirit of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [Unreleased]

## [0.1.0] — 2026-05-06

First public release.

### Added

- New **`agent-gh`** builtin pack (`packs/agent-gh.yaml`) for destructive `gh` subcommands; `agent-git` post-tool nudge is now **git-only** (see `docs/agent-gh.md`).
- **`gh` shell segment parsing** in `buckler.core` (composite subcommands like `repo delete`, `pr close`; `gh_api_delete` match for `gh api` + `-X DELETE` / `--method DELETE`).
- **Agent-git parser hardening** — segment on `&`, `|`, newlines; recurse `bash -c` / `sh -c` / `dash -c`, `$(…)`, and backticks (depth cap); strip `VAR=value` and `env` prefixes; heuristic `xargs git …` expansion; fail-closed on parse/depth errors while preserving env-only bypass (`RETHUNK_ALLOW_SHELL=1`). See `specs/done/parser-bypass-hardening/`.
- `unknown_harness_event` policy trigger for unrecognized Cursor hook events (matches no shipped rules; default allow).
- `POLICY_TRIGGERS` in `buckler` package metadata for a single canonical trigger set.
- Audit log writes to `paths.audit_log()` when `audit_log = true` in `config.toml` (one line per `evaluate()` decision).

### Changed

- `evaluate()` validates `policy_io_version` and `trigger` before loading packs; mismatches raise `PolicyError`.
- Cursor adapter rejects a non-null `policy_io_version` on stdin when it does not match the supported contract.
- Cursor adapter maps unknown `hook_event_name` values to `unknown_harness_event` instead of `post_tool_success`.
- `hooks.json` merge prefers `.venv/Scripts/python.exe` on Windows and `.venv/bin/python` elsewhere.
- Release workflow runs the same ruff, format, and mypy gates as CI before publishing.
- Project version is read from `src/buckler/__init__.py` via Hatch (`dynamic = ["version"]`).

### Fixed

- `load_config()` no longer catches bare `Exception`; only expected I/O and TOML errors fall back to defaults.
- Removed unused `tomllib` conditional dependency (Python 3.11+ only).

[0.1.0]: https://github.com/Rethunk-AI/buckler/releases/tag/v0.1.0
