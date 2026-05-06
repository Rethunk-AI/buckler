# Spec — legacy-deprecation-window

| | |
|---|---|
| Status | DONE 060611ZMAY26 — Remove rethunk-mcp-nudge migration scaffolding: purge-legacy path, docs, pack/HUMANS/README/skill copy; Q-table ratified; no greenfield HIGH CI gate (CONTRIBUTING note). |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. `greenfield-scrub` reports 17 high-severity legacy markers, all referencing the predecessor `rethunk-mcp-nudge.py`. The pre-1.0 repo carries an entire `_purge_legacy` codepath in `setup.sh`, a `--purge-legacy` install flag, the full `docs/migration.md`, a "ports and supersedes" sentence in `packs/agent-git.yaml`, and several mentions in `HUMANS.md`. The repo isn't even tagged 0.1.0 yet. |

## Why

If `rethunk-mcp-nudge.py` was a shipped predecessor with installed external users, the migration scaffolding is correct and should stay for at least one release after Buckler 0.1.0 ships. If it was an internal-only experiment (or a personal dotfiles script), the scaffolding is dead weight: it doubles the code paths in `setup.sh`, raises the conceptual surface in HUMANS.md ("what's `rethunk-mcp-nudge.py`?"), and pre-commits us to maintaining a migration guide for a tool the public never saw.

The `greenfield-scrub` flagging it at HIGH is the trigger: this is exactly the kind of "kept just in case" ballast a pre-1.0 project should make a calendar decision on, not carry indefinitely. Either commit to the migration window with a dated removal, or rip it out before the first public tag.

## In scope

### Decision

Q1 below. The answer drives the rest of the spec.

### If "shipped externally" path

- Pin a deletion DTG / version in `CHANGELOG.md`: e.g. an `[Unreleased] / Deprecated` section that promises "removed in 0.3.0" (or whatever Q2 ratifies).
- Add a `# DEPRECATED — removed in <ver>` banner to:
  - `cmd_install` block in `setup.sh` when `--purge-legacy` is passed (print to stderr).
  - The top of `docs/migration.md`.
  - The `packs/agent-git.yaml` description ("Ports and supersedes the rethunk-mcp-nudge.py legacy hook" → add "(deprecated; removed in <ver>)" or rewrite).
- Decide and ratify (Q3) whether `--purge-legacy` becomes a no-op-with-warning for one minor release before hard removal.

### If "internal only" path

- Delete `_purge_legacy` from `setup.sh` (lines 176–198) and the `--purge-legacy` arg parsing in `cmd_install` (lines 202–230).
- Strip the `--purge-legacy` line from the help block in `setup.sh:313`.
- Remove `docs/migration.md` outright (or move under `docs/deprecated/migration-rethunk-mcp-nudge.md` as a historical record — Q4).
- Strip the "Ports and supersedes the rethunk-mcp-nudge.py legacy hook" sentence from `packs/agent-git.yaml:6`.
- Remove the `### Migrate from rethunk-mcp-nudge.py` subsection from `HUMANS.md:82–88`.
- Remove the migration row from `README.md` Documentation table.
- Confirm `greenfield-scrub --severity HIGH` reports 0 hits on the resulting tree (or only hits that are intentional and tracked here).

### Either path

- The `RETHUNK_ALLOW_SHELL` env var name stays as-is (it's the bypass contract; renaming is a separate breaking change tracked elsewhere).
- The `Rethunk-AI` org name stays everywhere (org name, not legacy artifact).

## Out of scope

- Renaming `RETHUNK_ALLOW_SHELL` to `BUCKLER_ALLOW_SHELL`. Different scope, different blast radius (operator-facing env var change).
- Moving the org from `Rethunk-AI` to anything else.
- Migration guides for any future predecessor tools (none exist).
- `greenfield-scrub` doc-only legacy hits in `docs/contracts/policy-io.md` and `ARCHITECTURE.md` — those are descriptive ("backward-compatible extension"), not deadwood; they are flagged but should remain.

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Was `rethunk-mcp-nudge.py` shipped to external users (i.e. installed via a public README or dotfiles repo someone else's machines run)? **Operator answer required.** | **Ratified 060800ZMAY26** — **No.** Never shipped; operators who still have local hooks remove them manually; migration code deleted from this repo. |
| Q2 | If Q1 = yes: deprecation horizon. Proposal: **one minor release** — keep the migration code through 0.2.x, remove in 0.3.0. Justification: small user base, low cost to wait one cycle. | **Ratified 060800ZMAY26** — **N/A** (Q1 = no). |
| Q3 | If Q1 = yes: should `--purge-legacy` become a no-op-with-warning before hard deletion, or removed cleanly at the deletion version? Proposal: **warn-then-delete** for one minor release (warns in 0.2.x, removed in 0.3.0). | **Ratified 060800ZMAY26** — **N/A** (Q1 = no). |
| Q4 | If Q1 = no: delete `docs/migration.md` outright, or move under `docs/deprecated/`? Proposal: **delete** — no public history to preserve. | **Ratified 060800ZMAY26** — **Delete** `docs/migration.md`. |
| Q5 | After resolution, run `greenfield-scrub` again and decide whether to add a `--fail-on HIGH` gate to CI. Proposal: **yes** — once HIGH is intentional, gate against accidental reintroduction. | **Ratified 060800ZMAY26** — **No CI gate.** Rationale in `CONTRIBUTING.md` (ad-hoc scrub; contract docs may still match scrub heuristics). |

## Acceptance

- A1. Q1 answered explicitly.
- A2. Q1 = yes path: `CHANGELOG.md` has a dated deprecation entry; deprecation banners present in `setup.sh`, `docs/migration.md`, and `packs/agent-git.yaml`.
- A3. Q1 = no path: `_purge_legacy`, `--purge-legacy`, `docs/migration.md`, the migration sentence in `packs/agent-git.yaml`, and the `HUMANS.md` "Migrate from `rethunk-mcp-nudge.py`" subsection are all removed; `greenfield-scrub --severity HIGH` reports 0 hits (or only intentional, documented ones).
- A4. `README.md` Documentation table reflects the post-resolution state.
- A5. CI shellcheck still clean (no orphaned references in `setup.sh`).
- A6. Per Q5: `greenfield-scrub --fail-on HIGH` either added to CI or explicitly deferred.
- A7. Q-table ratified.
