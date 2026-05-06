# Spec — pack-gh-coverage

| | |
|---|---|
| Status | DRAFT 060431ZMAY26 |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. The pack is named `agent-git`, the pack docstring at `packs/agent-git.yaml:5` self-describes as covering "git **and gh**", and the `nudge-mcp-available` rule matches both `git` and `gh` programs. But there is no deny rule for any `gh` subcommand — `gh repo delete user/repo` and `gh release delete v1.0.0` both evaluate to `allow` today. |

## Why

The pack as shipped today protects against destructive `git` commands and *advertises* protection against destructive `gh` commands. An operator reading the pack name and the docstring at face value gets exposed: the agent can wipe a GitHub repo, delete a release tag, force-close a PR with `--delete-branch`, or issue arbitrary `gh api -X DELETE` calls without any rule firing. The asymmetry is worse than a missing feature — it actively misinforms the operator about the gatehouse's coverage.

The fix is a one-time decision plus rule plumbing. Either narrow the brand to git-only (rename pack, rewrite docstring, drop `gh` mentions everywhere), or extend the rule set to actually cover destructive `gh` subcommands. Both are tractable; the question is which posture the project wants to take.

## In scope

### Decision-driven branch

Q1 below ratifies the path. Whichever path is chosen, both the YAML and the docs must match — no half-rename.

### If "extend" path is chosen

Add baseline-tier deny rules in `packs/agent-git.yaml` for:

| `gh` subcommand pattern | Rationale |
|---|---|
| `gh repo delete <name>` | Deletes the repo and all issues / PRs / releases. Irreversible. |
| `gh release delete <tag>` | Deletes a release; can break consumers depending on the tarball. |
| `gh release delete-asset <tag> <asset>` | Same family as above. |
| `gh pr close <n> --delete-branch` | The `--delete-branch` flag deletes the source branch on remote. Closing without it is not destructive. |
| `gh api -X DELETE …` / `gh api --method DELETE …` | Generic DELETE escape hatch — covers anything not modeled above. |
| `gh secret remove <name>` | Removes a repo / org / env secret. |
| `gh ssh-key delete <id>` | Removes an SSH key from the user account. |
| `gh gpg-key delete <id>` | Removes a GPG key from the user account. |

Rule shape mirrors `deny-git-remote-remove` (priority 100, baseline tier, both `pre_shell_exec` and `pre_shell_tool` triggers). The `subcommand` matcher needs the same composite-subcommand support already used for `git remote remove` (e.g. `release delete-asset`).

### If "rename" path is chosen

- Rename the pack file from `packs/agent-git.yaml` to `packs/git-only.yaml` (or similar).
- Strip the "and gh" sentence from the pack docstring.
- Strip the `- program: gh` row from `nudge-mcp-available`'s match config.
- Update `docs/agent-git.md` → `docs/git-only.md`; update `HUMANS.md` pack table; update `AGENTS.md` contract canon.
- Add a CHANGELOG note documenting the breaking pack-name change for any user with `pack_override:` in their `config.toml`.

### Either path

- Update `tests/test_agent_git.py` (or rename to match) with parametrize rows per `gh` deny rule (extend path) or with assertions that no rule matches `gh` programs (rename path).
- Update `docs/agent-git.md` "Baseline rule matrix" table.
- `python -m buckler evaluate` smoke for every row from this spec.

## Out of scope

- Other shell wrappers around GitHub (`hub`, `glab`, `bitbucket-cli`). If the project wants those, they're a follow-up.
- Read-only `gh` commands (`gh repo view`, `gh pr list`, `gh issue list`). These remain allow.
- Adding `gh` subcommands to the strict tier. If extend wins, baseline covers the destructive set; strict-tier additions can be a separate scope.
- A new `agent-gh` pack split from `agent-git`. Both paths above keep one pack; splitting later is cheap and reversible.

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Rename the pack to git-only OR extend coverage to `gh`? Proposal: **extend** — keeps the existing `pack_override` keys stable, matches operator expectations from the pack name, and the rules are mechanical. | **Open** |
| Q2 | Should `gh api -X DELETE` (and `--method DELETE`) be a baseline deny or a strict-tier deny? Proposal: **baseline** — DELETE is unambiguous; the false-positive rate on destructive `gh api` calls is essentially zero. | **Open** |
| Q3 | `gh ssh-key delete` / `gh gpg-key delete` affect identity, not the repo. Cover here or split to a future `agent-identity` pack? Proposal: **cover here** — pack catalog is small; splitting later is cheap. | **Open** |
| Q4 | `gh pr close` without `--delete-branch` is not destructive. Should the deny match the flag, or the bare subcommand? Proposal: **match the flag** so `gh pr close 42` (clean close) stays allow. | **Open** |
| Q5 | `gh repo archive` is destructive-in-spirit (project becomes read-only) but reversible. Cover or skip? Proposal: **skip** — reversibility makes it nudge-worthy at most; track separately if requested. | **Open** |

## Acceptance

- A1. Q1 path executed end-to-end (no half-rename, no half-extend).
- A2. If extend: `gh repo delete`, `gh release delete`, `gh release delete-asset`, `gh pr close --delete-branch`, `gh api -X DELETE`, `gh secret remove`, `gh ssh-key delete`, `gh gpg-key delete` all evaluate to deny under both `pre_shell_exec` and `pre_shell_tool`.
- A3. Read-only `gh` commands (`gh repo view`, `gh pr list`, `gh issue list`, `gh release list`) remain allow.
- A4. `gh pr close 42` (without `--delete-branch`) remains allow per Q4.
- A5. `docs/agent-git.md` matrix and `HUMANS.md` pack table reflect the chosen path.
- A6. `tests/test_agent_git.py` parametrize cases cover the rules added or the absence-of-coverage assertions.
- A7. 100% coverage maintained.
- A8. Q-table ratified.
