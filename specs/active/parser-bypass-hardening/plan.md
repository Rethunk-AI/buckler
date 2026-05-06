# Plan — parser-bypass-hardening

## Overview

Harden `_segment_command` / `_parse_segment` / matching in `src/buckler/core.py` so common shell bypasses (`&`, `|`, newlines, env prefixes, `env`, `bash -c`, command substitution) are evaluated under the same deny rules. Align `docs/agent-git.md` with `git commit-graph` behavior per Q2. Update `SECURITY.md` known-bypass tracking; add redteam tests in `tests/test_agent_git_redteam.py`.

## Preconditions

- Ratify Q1–Q5 (parse failure posture, commit-graph doc vs matcher, env-prefix semantics, recursion depth, pipe deny semantics).

## Approach

### Segmentation

- Extend boundary logic beyond `&&`/`||`/`;` to include `&`, `|`, and bare newlines without breaking `&&` detection — respect quotes like existing splitter.

### Segment preprocessing

- Strip leading `VAR=value` assignments and unwrap leading `env` invocations before program identification.

### Recursion

- Implement bounded recursion for `bash -c`/`sh -c` string bodies and `$(...)` / backticks per Q4; on unparseable inner shell per Q1, bias deny.

### Documentation and tests

- Fix `git commit-graph` doc/matcher mismatch per Q2 with locked fixture.
- Author redteam parametrized tests for each bypass row and benign cases.
- Refresh `SECURITY.md` subsection; mirror resolved items to `CHANGELOG.md` when shipping.

## Dependencies

- `docs-and-runbooks` and downstream operator docs should reference this spec until closed.

## Risks

- Over-deny on rare valid pipelines — mitigated by tests for benign cases and Q5 confirmation.
- Performance on pathological nesting — depth bound per Q4.

## Verification

- `pytest` at 100% coverage; manual `python -m buckler evaluate` on table payloads.
- No regressions in `tests/test_core.py` / `tests/test_agent_git.py` contracts.

## Out of scope reminder

Full POSIX shell, seccomp, other packs — excluded.
