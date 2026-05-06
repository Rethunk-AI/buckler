# Spec — pack-gh-coverage

| | |
|---|---|
| Status | DONE 051400ZMAY26 — `agent-gh` pack + `gh` parser; `agent-git` git-only nudge; docs/tests. |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. The pack is named `agent-git`, the pack docstring at `packs/agent-git.yaml:5` self-describes as covering "git **and gh**", and the `nudge-mcp-available` rule matches both `git` and `gh` programs. But there is no deny rule for any `gh` subcommand — `gh repo delete user/repo` and `gh release delete v1.0.0` both evaluate to `allow` today. |

## Why

The pack as shipped today protects against destructive `git` commands and *advertises* protection against destructive `gh` commands. An operator reading the pack name and the docstring at face value gets exposed: the agent can wipe a GitHub repo, delete a release tag, force-close a PR with `--delete-branch`, or issue arbitrary `gh api -X DELETE` calls without any rule firing. The asymmetry is worse than a missing feature — it actively misinforms the operator about the gatehouse's coverage.

## In scope (as ratified)

- **`agent-git`**: Git rules only; description and post-tool nudge no longer imply `gh` coverage.
- **`agent-gh`** (new builtin `packs/agent-gh.yaml`): Baseline deny rules for destructive `gh` patterns; own post-tool nudge; duplicate `bypass-allow` so disabling `agent-git` alone still honors `RETHUNK_ALLOW_SHELL=1` for `gh`.
- **`buckler.core`**: Composite `gh` subcommand parsing (`repo delete`, `release delete-asset`, `pr close`, …) and `gh_api_delete` shell-segment field for `gh api` + `-X DELETE` / `--method DELETE`.
- **Docs**: `docs/agent-gh.md`, `docs/agent-git.md`, `HUMANS.md`, `README.md`, `AGENTS.md`, `ARCHITECTURE.md`, `docs/rule-schema.md`, `SECURITY.md`, `CHANGELOG.md`.
- **Tests**: `tests/test_agent_gh.py` + core parser coverage.

## Out of scope

- Other shell wrappers around GitHub (`hub`, `glab`, `bitbucket-cli`).
- Read-only `gh` commands remain allow.
- Strict-tier `gh` rules (future spec).

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Single-pack extend vs rename vs **split packs**. | **Ratified 051400ZMAY26** — **two packs**: `agent-git` (git) + **`agent-gh`** (`gh`), easier to maintain. |
| Q2 | `gh api` DELETE baseline vs strict. | **Ratified 051400ZMAY26** — **baseline** |
| Q3 | SSH/GPG key deletes in this pack vs future `agent-identity`. | **Ratified 051400ZMAY26** — **in `agent-gh`** |
| Q4 | `gh pr close` match flag vs bare subcommand. | **Ratified 051400ZMAY26** — **`--delete-branch` only** |
| Q5 | `gh repo archive` cover vs skip. | **Ratified 051400ZMAY26** — **baseline deny** |

## Acceptance

- A1. Two-pack split shipped end-to-end (`agent-git` + `agent-gh`); no stale “git+gh” branding on `agent-git`.
- A2. Destructive patterns deny under `pre_shell_exec` and `pre_shell_tool`: `gh repo delete`, `gh repo archive`, `gh release delete`, `gh release delete-asset`, `gh pr close --delete-branch`, `gh api` DELETE, `gh secret remove`, `gh ssh-key delete`, `gh gpg-key delete`.
- A3. Read-only `gh` commands remain allow.
- A4. `gh pr close 42` (no flag) remains allow.
- A5. Docs and `HUMANS.md` pack table list both packs.
- A6. `tests/test_agent_gh.py` covers deny/allow/bypass/nudge rows.
- A7. 100% coverage maintained.
- A8. Q-table ratified.
