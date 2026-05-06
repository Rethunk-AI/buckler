# Tasks — legacy-deprecation-window

Status: DONE 060611ZMAY26 — Remove rethunk-mcp-nudge migration scaffolding: purge-legacy path, docs, pack/HUMANS/README/skill copy; Q-table ratified; no greenfield HIGH CI gate (CONTRIBUTING note).

## P0

- [x] [HUMAN] Answer Q1: was `rethunk-mcp-nudge.py` shipped to external users?
- [x] If Q1 = yes: add `CHANGELOG` deprecation entry; banners in `setup.sh`, `docs/migration.md`, `packs/agent-git.yaml`; ratify Q2/Q3 warn-then-remove timeline (A2). *(Skipped — Q1 = no.)*
- [x] If Q1 = no: remove `_purge_legacy`, `--purge-legacy`, migration doc, pack sentence, `HUMANS.md` subsection; update `README.md` Documentation table; handle `docs/migration.md` per Q4 (A3).
- [x] Run `greenfield-scrub --severity HIGH` and reconcile until acceptance A3/A6 criteria met. *(No `greenfield-scrub` in dev env; verified via ripgrep: no `rethunk-mcp-nudge` / `purge-legacy` outside this spec’s historical text.)*
- [x] Ensure CI shellcheck still passes on `setup.sh` (A5).
- [x] Add `greenfield-scrub --fail-on HIGH` to CI or explicitly defer with documented rationale per Q5 (A6).
- [x] Ratify Q-table (A7).

## P1

- [x] Search repo for stray `rethunk-mcp-nudge` references outside intentional docs.
- [x] If deprecation path: communicate operator-facing timeline in `HUMANS.md` / `CHANGELOG` consistently. *(N/A — Q1 = no.)*

## P2

- [ ] Consider lightweight release checklist item “migration scaffolding review” for future tools.
