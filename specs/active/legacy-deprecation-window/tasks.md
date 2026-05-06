# Tasks — legacy-deprecation-window

Status: DRAFT 060431ZMAY26

## P0

- [ ] [HUMAN] Answer Q1: was `rethunk-mcp-nudge.py` shipped to external users?
- [ ] If Q1 = yes: add `CHANGELOG` deprecation entry; banners in `setup.sh`, `docs/migration.md`, `packs/agent-git.yaml`; ratify Q2/Q3 warn-then-remove timeline (A2).
- [ ] If Q1 = no: remove `_purge_legacy`, `--purge-legacy`, migration doc, pack sentence, `HUMANS.md` subsection; update `README.md` Documentation table; handle `docs/migration.md` per Q4 (A3).
- [ ] Run `greenfield-scrub --severity HIGH` and reconcile until acceptance A3/A6 criteria met.
- [ ] Ensure CI shellcheck still passes on `setup.sh` (A5).
- [ ] Add `greenfield-scrub --fail-on HIGH` to CI or explicitly defer with documented rationale per Q5 (A6).
- [ ] Ratify Q-table (A7).

## P1

- [ ] Search repo for stray `rethunk-mcp-nudge` references outside intentional docs.
- [ ] If deprecation path: communicate operator-facing timeline in `HUMANS.md` / `CHANGELOG` consistently.

## P2

- [ ] Consider lightweight release checklist item “migration scaffolding review” for future tools.
