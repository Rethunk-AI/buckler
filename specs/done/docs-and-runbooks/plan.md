# Plan — docs-and-runbooks

## Overview

Documentation-only spec: align `SECURITY.md` with real parser bypass posture; add operator guidance for audit log lifecycle and forwarding; add `docs/troubleshooting.md` and wire cross-links (`README.md`, `AGENTS.md`, `cursor-skill/buckler/SKILL.md`). No code changes.

## Preconditions

- Confirm Q1 path: `docs/troubleshooting.md` (not root `TROUBLESHOOTING.md`) per governance.
- Coordinate wording with `parser-bypass-hardening` / `hooks-cross-platform-quoting` so links stay accurate when those specs ship.

## Approach

### SECURITY.md

Insert “Known parser bypasses (status)” between threat table and “V1 scope”. Rows reference open vs closed state and link to `parser-bypass-hardening`. Cross-link existing “Agent bypasses the hook” row to this subsection.

### HUMANS.md

New “Audit log operations” after Configuration: append-only contract, rotation (`logrotate` example), SIEM forwarding minimal example, redaction expectations — per Q2/Q3 proposals.

### docs/troubleshooting.md

Author five sections in spec order: hook didn’t fire; allowed vs expected deny; wrong policy; Windows hook exit (link `hooks-cross-platform-quoting`); audit log not written.

### Cross-links

- `README.md` Documentation table row.
- `AGENTS.md` canon pointers table.
- `cursor-skill/buckler/SKILL.md` Key documents — per Q5, add now.

## Dependencies

- Content references `parser-bypass-hardening` — keep language status-aware (“as of …”) until that spec closes.

## Risks

- Drift between SECURITY rows and actual parser after releases — mitigate via CHANGELOG + spec links.

## Verification

- Run `doc-audit` skill or project doc lint if available; manual read for tier violations.
- Link check (relative paths) for new troubleshooting doc.

## Out of scope reminder

No code, no new env vars like `BUCKLER_DEBUG` until implemented elsewhere.
