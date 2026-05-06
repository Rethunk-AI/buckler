# Spec — docs-and-runbooks

| | |
|---|---|
| Status | DRAFT 060431ZMAY26 |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. Three documentation gaps surfaced: (a) `SECURITY.md`'s threat-model table only enumerates *covered* threats, not the parser bypasses currently open; (b) `HUMANS.md` mentions the audit log but says nothing about rotation, max size, or SIEM forwarding; (c) the most common debugging case — "the hook fired but the command was allowed when I expected deny" — has a one-line answer in `HUMANS.md` that's easy to miss. |

## Why

`SECURITY.md` is the document an operator reads to decide whether Buckler can be trusted in a deployment. Today's table reads as exhaustive, but it doesn't include the parser bypass surfaces (covered for fix in `parser-bypass-hardening`). An operator deploying Buckler to a team of agents today walks away with a false picture of coverage.

The audit log is positioned as a compliance feature in `HUMANS.md` and `ARCHITECTURE.md`, but `HUMANS.md` doesn't tell the operator what to do once the file starts growing — append-only file, no rotation, no size cap. That's a footgun (disk fills, hooks start failing, fail-closed cancels every shell command, very bad day).

The troubleshooting flow is one of the most common operator questions for any policy/hook product: "I expected this to be blocked, why wasn't it?" The answer (run `python -m buckler evaluate` against the same payload, inspect the audit log, check `python -m buckler.hooks status`) is partially in `HUMANS.md` but scattered. A single runbook page, linked from `README.md`, closes the loop.

## In scope

### `SECURITY.md` updates

- New subsection "Known parser bypasses (status)" between the existing threat-model table and "V1 scope (local-only)".
- Each row enumerates one bypass surface, its current status (open / closed in `<ver>`), and links to the spec that closes it (`parser-bypass-hardening` for the current set).
- When `parser-bypass-hardening` ships and a bypass is closed, the row moves to a "Resolved" entry in `CHANGELOG.md` and the row in `SECURITY.md` reads `closed in <ver>`.
- The existing "Agent bypasses the hook (shell escape)" row in the threat-model table cross-references the new subsection instead of reading "phase 2."

### `HUMANS.md` audit-log operations

- Append a new "Audit log operations" subsection after the existing "Configuration" section.
- Cover, in this order:
  - **Append-only contract.** Buckler never rotates, truncates, or compresses the file. Operator-owned.
  - **Rotation.** One-line `logrotate(8)` snippet (Linux example) targeting `~/.local/state/buckler/audit.log`. macOS / Windows operators: explain that they need to roll their own (cron + `mv` + signal — Buckler reopens on next write because we always `open("a")`).
  - **Forwarding to a SIEM.** One minimal example (`tail -F audit.log | nc syslog 514`) plus a sentence pointing operators to whatever forwarder they already use (Vector, Fluent Bit, etc.). Don't lock in a stack.
  - **Redaction expectations.** The audit line includes the raw `command` repr — operators with secrets-in-shell concerns should sanitize at forwarder level. Buckler does not redact.

### New `docs/troubleshooting.md`

- Sections, in this order:
  - **Hook didn't fire at all.** Symptoms (`git commit` ran cleanly when it shouldn't have, no audit line). Diagnostics: `python -m buckler.hooks status`, `~/.local/share/buckler/current/.venv/bin/python -m buckler --version`, check `~/.cursor/hooks.json` for a `buckler:` entry whose `command` resolves.
  - **Hook fired but the command was allowed when I expected deny.** Diagnostics: copy the JSON Cursor sent (from a recent log or by adding a `BUCKLER_DEBUG=1` env hook — out of scope here, but mention the manual approach), pipe into `python -m buckler evaluate`, compare to expectation. Common cause: parser bypass — link to `parser-bypass-hardening` known-bypass list.
  - **Policy decision is wrong.** Diagnostics: `buckler validate` to confirm pack YAML is syntactically clean; check `~/.config/buckler/rules.d/` for a user rule overriding a builtin; check `config.toml` for an unintended `tier = "strict"`.
  - **Windows: hook fires but immediately exits.** Cross-link to `hooks-cross-platform-quoting` for the path-quoting cause.
  - **Audit log isn't being written.** Check `audit_log = true` in `config.toml`; check the state dir is writable; check disk isn't full.

### Cross-linking

- Add a row to `README.md` "Documentation" table pointing at `docs/troubleshooting.md`.
- The `cursor-skill/buckler/SKILL.md` agent skill gains a "Troubleshooting" pointer in its existing "Key documents" table.
- `AGENTS.md` "Canon pointers" table picks up the troubleshooting row too.

## Out of scope

- An operator-facing tutorial / quickstart video.
- A new API reference for `buckler.core.evaluate` (the contract docs at `docs/contracts/policy-io.md` already cover the JSON shape).
- Commercial-product runbooks (incident-response playbooks, on-call rotations, etc.) — out of scope for an OSS tool.
- Any code change. This spec is documentation-only. Functional fixes for the bypasses live in `parser-bypass-hardening`; cross-platform quoting fixes live in `hooks-cross-platform-quoting`.

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Should troubleshooting live at `docs/troubleshooting.md` (matches existing `docs/` convention) or `TROUBLESHOOTING.md` at root (matches `SECURITY.md`, `CONTRIBUTING.md`)? Proposal: **`docs/troubleshooting.md`** — keeps root tier-clean per `doc-audit` governance. | **Open** |
| Q2 | Audit-log rotation — should Buckler ship its own rotation later, or stay operator-owned forever? Proposal: **operator-owned** — matches the v1 "local tool only" framing in `SECURITY.md`; one less moving part. | **Open** |
| Q3 | SIEM forwarding example: UDP syslog (`nc syslog 514`) vs. modern (Vector / Fluent Bit). Proposal: **show the minimal logrotate snippet + one-line `tail -F` syslog example, link out** for the modern stack. Don't lock in. | **Open** |
| Q4 | Should the troubleshooting doc describe a `BUCKLER_DEBUG=1` env var to dump the raw Cursor JSON? Proposal: **defer** — no such env var exists today; would require a code change. Mention "manually capture the JSON by adding a wrapper hook" instead. | **Open** |
| Q5 | Cross-link from `cursor-skill/buckler/SKILL.md` (the agent skill) — add now or wait until the troubleshooting doc has lived a release? Proposal: **add now** so agents asked "buckler isn't blocking my commit" land on the troubleshooting page. | **Open** |

## Acceptance

- A1. `SECURITY.md` has a "Known parser bypasses (status)" subsection that reflects current state and links to the remediation spec.
- A2. `HUMANS.md` has an "Audit log operations" subsection covering append-only contract, rotation, forwarding, and redaction.
- A3. `docs/troubleshooting.md` exists with the five sections enumerated above.
- A4. `README.md` Documentation table links to `docs/troubleshooting.md`.
- A5. `cursor-skill/buckler/SKILL.md` Key documents table includes a troubleshooting row (per Q5 outcome).
- A6. `AGENTS.md` Canon pointers table includes troubleshooting.
- A7. `doc-audit` continues to return clean (no new tier-violation flags).
- A8. Q-table ratified.
