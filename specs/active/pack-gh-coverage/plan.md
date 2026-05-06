# Plan — pack-gh-coverage

## Overview

Either extend `packs/agent-git.yaml` with baseline deny rules for destructive `gh` invocations, or rename/narrow the pack and docs to git-only so branding matches reality. Q1 chooses the branch; YAML, docs (`docs/agent-git.md`, `HUMANS.md`, `AGENTS.md` if needed), and tests must match end-to-end.

## Preconditions

- [HUMAN] Ratify Q1 (extend vs rename) and Q2–Q5 for rule scope and matcher behavior.

## Approach

### Extend path

- Add deny rules mirroring existing `git` deny structure for listed `gh` patterns; ensure composite subcommands (`release delete`, etc.) match existing matcher capabilities.
- Update baseline matrix in `docs/agent-git.md` and pack table in `HUMANS.md`.
- Expand `tests/test_agent_git.py` with parametrized evaluate tests for each rule + allow cases.

### Rename path

- Rename pack file and references (`pack_override`, builtins index); update docs filenames and canon tables; `CHANGELOG` breaking note.
- Remove `gh` from `nudge-mcp-available` per spec.
- Tests assert `gh` commands are not covered as advertised.

### Either path

- Run `python -m buckler evaluate` smoke for each cited command line.

## Dependencies

- Rule matcher features must already support composite subcommands — confirm in `buckler.core` before authoring YAML.

## Risks

- False positives on creative but benign `gh api` usage — tune matchers if needed within baseline posture (Q2).

## Verification

- Full test suite; coverage 100%.
- Manual `buckler evaluate` samples from spec table.

## Out of scope reminder

No `hub`/`glab`; no strict-tier expansion; no split `agent-gh` pack.
