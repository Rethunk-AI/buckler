# Plan — pack-gh-coverage

## Overview

Ship a dedicated **`agent-gh`** builtin pack for destructive GitHub CLI commands, narrow **`agent-git`** to git-only messaging and nudges, and extend **`buckler.core`** so composite `gh` subcommands and `gh api` DELETE patterns match reliably.

## Preconditions

- Ratified Q1–Q5 (two-pack split, baseline DELETE API, identity key deletes in `agent-gh`, `pr close` flag-only, `repo archive` deny).

## Approach

- Add `packs/agent-gh.yaml` (deny rules, post-tool nudge, duplicate bypass).
- Update `packs/agent-git.yaml` pack description + `nudge-mcp-available` (git only).
- Implement `gh` parsing and `gh_api_delete` in `core.py`; document in `docs/rule-schema.md`.
- Add `docs/agent-gh.md`; update `docs/agent-git.md`, operator docs, `SECURITY`, `CHANGELOG`.
- Add `tests/test_agent_gh.py` and core parser tests.

## Verification

- `uv run pytest` at 100% coverage; `python -m buckler validate`.

## Out of scope reminder

No `hub`/`glab`; no strict-tier `gh` rules in this spec.
