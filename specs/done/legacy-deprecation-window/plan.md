# Plan — legacy-deprecation-window

## Overview

Decide whether `rethunk-mcp-nudge.py` migration scaffolding (`_purge_legacy`, `--purge-legacy`, `docs/migration.md`, pack copy, `HUMANS.md`) stays for a deprecation window or is removed before first public tag. Q1 is the gate; implementation diverges into “shipped externally” vs “internal only” branches per `spec.md`.

## Preconditions

- Operator answers Q1 with evidence (public install path vs internal-only).
- Run `greenfield-scrub` on current tree to baseline HIGH findings.

## Approach

### If Q1 = shipped externally

- Add deprecation horizon per Q2/Q3 (e.g. removal in 0.3.0, warn-then-delete for `--purge-legacy`).
- Banner strings in `setup.sh` (stderr when `--purge-legacy`), `docs/migration.md`, and `packs/agent-git.yaml` per spec.
- `CHANGELOG.md` `[Unreleased]` deprecation notes.

### If Q1 = internal only

- Remove `_purge_legacy` and `--purge-legacy` path from `scripts/setup.sh` and help text.
- Remove or relocate `docs/migration.md` per Q4 (delete vs `docs/deprecated/...`).
- Strip migration prose from `packs/agent-git.yaml`, `HUMANS.md`, `README.md` Documentation table.
- Re-run `greenfield-scrub`; confirm HIGH clean or document intentional leftovers.

### Either path

- Do not rename `RETHUNK_ALLOW_SHELL` or org branding (explicit out of scope).

### CI / tooling (Q5)

- After tree is stable, add `greenfield-scrub --fail-on HIGH` to CI or record explicit deferral with rationale.

## Dependencies

- May interact with release tagging (`code-quality-sweep` Q4) — coordinate messaging only; no code coupling required.

## Risks

- Removing install paths may break users still on legacy scripts — mitigated by Q1 answer and deprecation timeline.
- Partial edits to `setup.sh` can break shellcheck — keep `shellcheck` green (`ci-hygiene`).

## Verification

- `bash scripts/setup.sh` help paths still coherent; `shellcheck` clean.
- `greenfield-scrub` report matches acceptance.
- Docs and pack language consistent everywhere (no half-removal).

## Out of scope reminder

Env rename, org rename, and unrelated migration guides stay out.
