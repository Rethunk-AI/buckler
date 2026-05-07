# Specs

## Active

*In-flight specifications (DRAFT through BLOCKED) under `specs/active/`. Claim, block, unblock, park, and close via [`@rethunk/citadel-sdd`](https://github.com/Rethunk-AI/citadel-sdd).*

| Slug | State | DTG | Owner |
|------|-------|-----|-------|
| _(none)_ | | | |

## Done

*Completed work (**DONE**) after `spec_close`; directories live under `specs/done/`. Lifecycle semantics and tools: [`@rethunk/citadel-sdd`](https://github.com/Rethunk-AI/citadel-sdd).*

| Slug | DTG | Note |
|------|-----|------|
| docs-polish | 071637ZMAY26 | SECURITY.md threat/bypass table consistency (set-url tier, parser-bypass spec link); HUMANS.md troubleshooting cross-link; cursor-skill agent-gh doc row; .cursor/ gitignored; docs-and-runbooks P1+P2 and pack-gh-coverage P2 closed. |
| code-quality-sweep | 060616ZMAY26 | Code quality sweep: template format_map, utf-8 CLI IO, TypedDict hooks, adapter registry, paths Windows heuristic, workspace_roots pair, HUMANS audit note, CONTRIBUTING coverage, CHANGELOG 0.1.0; misnamed test removed; 100% coverage. |
| legacy-deprecation-window | 060611ZMAY26 | Remove rethunk-mcp-nudge migration scaffolding: purge-legacy path, docs, pack/HUMANS/README/skill copy; Q-table ratified; no greenfield HIGH CI gate (CONTRIBUTING note). |
| docs-and-runbooks | 060500ZMAY26 | SECURITY known-parser bypasses table + threat cross-link; HUMANS audit log operations; docs/troubleshooting.md; README/AGENTS/cursor-skill links; Q-table ratified; doc-audit clean. |
| ci-hygiene | 060455ZMAY26 | Python matrix (ubuntu 3.11–3.13, mac/win 3.13), setup.sh shellcheck SC2034 fix via BUCKLER_HOOK_PREFIX, coherence test, CONTRIBUTING CI docs, deliberate shellcheck CI red proof (run 25417202183). |
| parser-bypass-hardening | 051500ZMAY26 | core segmentation/expansion + redteam tests + SECURITY/CHANGELOG. |
| pack-gh-coverage | 051400ZMAY26 | `agent-gh` pack + `gh` parser; `agent-git` git-only nudge; docs/tests. |
| hooks-cross-platform-quoting | 051200ZMAY26 | POSIX `shlex.quote` for interpreter path in hooks.json; newline/CR refusal; tests + cursor/paths docs. |

## Parked

*Deliberately not pursued (**PARKED**); superseded or withdrawn specs under `specs/parked/`. Use `spec_park` from [`@rethunk/citadel-sdd`](https://github.com/Rethunk-AI/citadel-sdd).*

| Slug | DTG | Note |
|------|-----|------|
| _(none)_ | | |
