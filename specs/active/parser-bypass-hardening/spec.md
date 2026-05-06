# Spec — parser-bypass-hardening

| | |
|---|---|
| Status | DRAFT 060431ZMAY26 |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. Live `python -m buckler evaluate` runs prove that the `agent-git` deny rules can be bypassed by every common shell construct that isn't `&&` / `||` / `;`-separated, and the `git commit-graph` claim in `docs/agent-git.md` contradicts the exact-match implementation in `_match_shell_segments`. |

## Why

The pack's brand promise is to make it safe to give an AI agent shell access. Today, a capable agent that has read `packs/agent-git.yaml` (or just guessed at the parser shape) can defeat **every** baseline deny rule with constructs the parser doesn't see:

| Bypass (confirmed live) | Current decision | Why it slips through |
|------|---------|----------------------|
| `git status & git commit -m foo` | ALLOW | `&` is not in `_SEGMENT_BOUNDARY` |
| `git status \| xargs git commit -m foo` | ALLOW | `\|` (pipe) is not segmented |
| `$(git commit -m foo)` | ALLOW | Command substitution not recursed |
| `` `git commit -m foo` `` | ALLOW | Backtick substitution not recursed |
| `bash -c "git commit -m foo"` | ALLOW | Acknowledged in `SECURITY.md` as "phase 2" |
| `sh -c "git commit -m foo"` | ALLOW | Same family, not called out |
| `FOO=bar git commit -m foo` | ALLOW | First token isn't `git` — it's the env-var assignment |
| `env GIT_AUTHOR_DATE=now git commit -m foo` | ALLOW | First token is `env` |

The current `SECURITY.md` threat-model table only enumerates the threats that *are* covered. Operators reading it get a false sense of safety, and Buckler's positioning as "the gatehouse" makes that gap a credibility risk, not just a feature gap.

This spec also carries a tightly-coupled documentation bug: `docs/agent-git.md` claims `git commit-graph write` is "Blocked... intentional conservative match" but `_match_shell_segments` does **exact** string equality (`core.py:208`), so `commit-graph != commit` and the command is in fact allowed. Either the matcher should match `startswith("commit")` or the doc must be corrected. Since `commit-graph` is benign plumbing, the safer fix is to keep exact-match and fix the doc — but the decision should be ratified explicitly before the parser hardening lands so the same review pass settles both.

## In scope

### Pre-shlex segmentation

- Extend `_SEGMENT_BOUNDARY` (or add a separate splitter that runs before shlex) to additionally split on:
  - `&` (background) — but **not** when followed by another `&` (which is `&&`, already handled).
  - `|` (pipe) — but **not** when followed by another `|`.
  - Bare `\n` (newline) — multi-line shell scripts passed as a single payload.
- All splits must respect single- and double-quoted strings (same posture as the existing `&&` / `||` / `;` parser at `core.py:77`).

### Wrapper unwrapping

- In `_parse_segment`, before identifying `program`:
  - Skip leading `KEY=VALUE` env-var assignments (`shlex` tokens matching `^[A-Za-z_][A-Za-z0-9_]*=`).
  - Skip a leading `env [-i] [-u VAR ...] [KEY=VALUE...]` invocation; the next non-flag, non-assignment token becomes `program`.
- After unwrapping, the matching pipeline continues as today (so `FOO=bar git commit` matches `deny-git-commit`).

### Shell substring recursion

- When a parsed segment's program is `bash` or `sh` and the next argument is `-c <STR>`, extract `<STR>`, re-segment it, and evaluate each inner segment against the same rule set. Treat the outer command as denied if any inner segment denies.
- When a segment contains a `$(...)` or backtick `` `...` `` substring, extract the inner command and evaluate it the same way. Nesting depth is bounded (see Q4).

### `git commit-graph` correctness

- Decide and align (Q2): either change `_match_shell_segments` to allow `subcommand: commit` to match `commit-graph` (and any future `commit-*`), or correct the doc claim. Either way, ship a fixture that asserts the documented behavior so the doc and the code can never drift apart again.

### Test coverage

- New `tests/test_agent_git_redteam.py` with one `pytest.mark.parametrize` row per bypass listed in the table above plus the documented benign cases (`git log --grep=commit`, `git branch commit-review`, `cat .git/COMMIT_EDITMSG`).
- Maintain `--cov-fail-under=100`.
- Existing `tests/test_agent_git.py` and `tests/test_core.py` keep their current contracts.

### `SECURITY.md` update

- Replace the single line `bash -c string recursion in pack parser (phase 2)` with a "Known parser bypasses" subsection that references this spec; once the spec closes, the subsection moves to a "Resolved" tier in `CHANGELOG.md` and the `SECURITY.md` row reads `closed in <version>`.

## Out of scope

- A full POSIX shell parser. The goal is defense against the bypass tricks an AI agent is likely to reach for; not a `bash -n` substitute.
- Quoting analysis beyond shlex (e.g. ANSI-C `$'…'` escapes, here-docs, here-strings). Flag if proven exploitable in test, otherwise track as future work.
- Runtime sandboxing, seccomp, or any kernel-level interception.
- Other packs or other adapters — `agent-git` parser only.
- New rules for additional commands (covered by `pack-gh-coverage` and `legacy-deprecation-window`).

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | When recursive `bash -c "…"` parse fails (unclosed quote, bad shlex), default decision for the wrapped portion is **deny** (matches `failClosed: true` posture; safer than allow). | **Open** |
| Q2 | `git commit-graph write`: keep exact-match in `_match_shell_segments` and **fix the doc** (commit-graph is benign plumbing). Alternative: change to startswith and document the broader sweep. | **Open** |
| Q3 | Env-var prefix `FOO=bar git push --force …`: treat as the wrapped command for matching purposes (so it denies). Alternative: deny any segment that uses an env-var prefix on a `git` invocation, period. | **Open** |
| Q4 | Recursion depth bound for `$(…)` / `` `…` `` / `bash -c` nesting. Proposal: **3 levels**; beyond that, deny (recursion-bomb defense). | **Open** |
| Q5 | Pipe `\|` segmentation — when one segment is benign and one is denied, the OR semantics already fire deny. Confirm this is the intended behavior versus "allow the whole pipeline if any segment is benign." Proposal: **deny if any segment matches a deny rule** (current OR behavior). | **Open** |

## Acceptance

- A1. New segmentation handles `&`, `|`, bare `\n` while still respecting quotes.
- A2. `_parse_segment` strips env-var assignment prefixes and the `env` wrapper.
- A3. `bash -c <STR>` / `sh -c <STR>` / `$(...)` / `` `...` `` payloads are re-evaluated against the rule set up to the depth bound from Q4.
- A4. `tests/test_agent_git_redteam.py` covers one row per bypass in the table above; each evaluates to deny (or whatever Q1–Q5 ratify) for the bypass attempts and allow for the documented benign cases.
- A5. `git commit-graph write` test asserts the post-Q2 ratified behavior.
- A6. `SECURITY.md` has a "Known parser bypasses" subsection that lists every still-open bypass with a reference here; closed bypasses are recorded in `CHANGELOG.md`.
- A7. 100% coverage maintained (`--cov-fail-under=100`).
- A8. `python -m buckler evaluate` smoke for each example payload from the carry-forward table behaves per the ratified Q-table.
- A9. Q-table ratified.
