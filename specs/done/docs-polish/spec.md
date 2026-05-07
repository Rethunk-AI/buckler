# Spec — docs-polish

| | |
|---|---|
| Status | DONE 071637ZMAY26 — SECURITY.md threat/bypass table consistency (set-url tier, parser-bypass spec link); HUMANS.md troubleshooting cross-link; cursor-skill agent-gh doc row; .cursor/ gitignored; docs-and-runbooks P1+P2 and pack-gh-coverage P2 closed. |
| Authored | 071633ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | Open P1 in `docs-and-runbooks` (SECURITY.md consistency pass, never closed); open P2 items in `docs-and-runbooks` (HUMANS.md troubleshooting cross-link) and `pack-gh-coverage` (cursor-skill → agent-gh cross-link); `.cursor/mcp.json` untracked with machine-specific absolute path. |

## Why

Four small gaps remained open after the previous doc sprint:

1. **SECURITY.md consistency** — The "Known parser bypasses" table has an ANSI-C `$'…'` / here-doc row that says "see spec out-of-scope" without a link, inconsistent with every other row that gives a direct spec link. The threat table row for `git remote set-url` says "configurable on `set-url`" which is vague; the pack actually denies it only in strict tier.

2. **HUMANS.md troubleshooting cross-link** — The Troubleshooting section in HUMANS.md ends without pointing to the richer `docs/troubleshooting.md` runbook. Operators who find HUMANS.md may not discover the full runbook.

3. **cursor-skill → `agent-gh` cross-link** — The `cursor-skill/buckler/SKILL.md` Key documents table links to `docs/agent-git.md` but not to `docs/agent-gh.md`, leaving the `agent-gh` pack invisible to agents running with the skill.

4. **`.cursor/mcp.json` untracked** — The `.cursor/` directory holds a developer-local MCP config with a machine-specific absolute path. It should be gitignored so contributors don't accidentally stage it.

## In scope

### SECURITY.md

- In the threat table: change "configurable on `set-url`" to "denied in strict tier for `remote set-url`" to match the actual pack behaviour.
- In "Known parser bypasses": update the ANSI-C / here-doc row's remediation cell from `"Future work (see spec out-of-scope); file an issue if exploitable in harness"` to `"Future work (tracked in [specs/done/parser-bypass-hardening/spec.md](specs/done/parser-bypass-hardening/spec.md) out-of-scope); file an issue if exploitable in harness"` — consistent link style with all other rows.

### HUMANS.md

- Add a final line to the Troubleshooting section: `> For a richer runbook (hook not firing, unexpected allow/deny, audit log, Windows quoting) see [docs/troubleshooting.md](docs/troubleshooting.md).`

### cursor-skill SKILL.md

- Add a `docs/agent-gh.md` row to the Key documents table (after the `docs/agent-git.md` row), pointing at the full `agent-gh` pack matrix.

### `.gitignore`

- Add a `.cursor/` entry so the developer-local MCP server config is not tracked.

## Out of scope

- Any changes to test files, pack YAML, or Python source code.
- `.cursor/mcp.json` documentation or sample/template — the file is purely developer-local; document MCP developer setup in CONTRIBUTING.md only if the user requests it.
- Closing P2 items in `ci-hygiene`, `parser-bypass-hardening`, `legacy-deprecation-window`, `hooks-cross-platform-quoting` (carry-forwards about future work, not actionable now).

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Should `.cursor/` be gitignored wholesale, or should `mcp.json` be moved to a sample? Since the file contains a machine-specific absolute path, gitignoring the whole directory is simplest; a sample adds noise without benefit. | **Ratified 071633ZMAY26** — gitignore whole directory |
| Q2 | Should HUMANS.md add a "See also" blockquote or a full paragraph? A single blockquote is the lightest touch; the full runbook lives in `docs/troubleshooting.md`. | **Ratified 071633ZMAY26** — blockquote |

## Acceptance

- A1. `.cursor/` added to `.gitignore`.
- A2. SECURITY.md threat table: "configurable on `set-url`" → "denied in strict tier for `remote set-url`".
- A3. SECURITY.md bypass table: ANSI-C row remediation cell links to `specs/done/parser-bypass-hardening/spec.md`.
- A4. HUMANS.md Troubleshooting section ends with a cross-link to `docs/troubleshooting.md`.
- A5. cursor-skill SKILL.md Key documents table includes `docs/agent-gh.md`.
- A6. `doc-audit` reports clean.
- A7. `docs-and-runbooks` P1 and P2 tasks checked; `pack-gh-coverage` P2 task checked.
