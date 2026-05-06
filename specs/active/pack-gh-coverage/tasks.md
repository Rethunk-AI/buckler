# Tasks — pack-gh-coverage

Status: DRAFT 060431ZMAY26

## P0

- [ ] [HUMAN] Ratify Q1–Q5 (extend vs rename, DELETE tier, identity subcommands, `--delete-branch` match, archive skip).
- [ ] Execute chosen branch fully — YAML + docs + tests; no half-rename / half-extend (A1).
- [ ] **If extend:** Add deny rules for listed destructive `gh` patterns; `pre_shell_exec` + `pre_shell_tool`; verify deny outcomes (A2).
- [ ] Confirm read-only `gh` commands remain allow (A3).
- [ ] Confirm `gh pr close` without `--delete-branch` allow (A4).
- [ ] Update `docs/agent-git.md` matrix and `HUMANS.md` pack table (A5).
- [ ] Expand `tests/test_agent_git.py` (or successor) per path (A6).
- [ ] Maintain 100% coverage (A7).
- [ ] Ratify Q-table (A8).

## P1

- [ ] Add evaluate smoke examples to contributor docs or spec appendix if helpful.

## P2

- [ ] Track `gh repo archive` separately if users request it (Q5).
