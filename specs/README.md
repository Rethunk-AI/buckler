# Specs

## Active

*In-flight specifications (DRAFT through BLOCKED) under `specs/active/`. Claim, block, unblock, park, and close via [`@rethunk/citadel-sdd`](https://github.com/Rethunk-AI/citadel-sdd).*

| Slug | State | DTG | Owner |
|------|-------|-----|-------|
| code-quality-sweep | DRAFT | 060431ZMAY26 | Bastion (J-3) |
| legacy-deprecation-window | DRAFT | 060431ZMAY26 | Bastion (J-3) |

## Done

*Completed work (**DONE**) after `spec_close`; directories live under `specs/done/`. Lifecycle semantics and tools: [`@rethunk/citadel-sdd`](https://github.com/Rethunk-AI/citadel-sdd).*

| Slug | DTG | Note |
|------|-----|------|
| docs-and-runbooks | 060500ZMAY26 | SECURITY known-parser bypasses table + threat cross-link; HUMANS audit log operations; docs/troubleshooting.md; README/AGENTS/cursor-skill links; Q-table ratified; doc-audit clean. |
| ci-hygiene | 060455ZMAY26 | Python matrix (ubuntu 3.11–3.13, mac/win 3.13), setup.sh shellcheck SC2034 fix via BUCKLER_HOOK_PREFIX, coherence test, CONTRIBUTING CI docs, deliberate shellcheck CI red proof (run 25417202183). |
| hooks-cross-platform-quoting | 051500ZMAY26 | POSIX `shlex.quote` for hook interpreter paths; newline rejection; cursor adapter docs. |
| pack-gh-coverage | 051500ZMAY26 | `agent-gh` pack + `agent-git` split; `gh` subcommand parsing and deny coverage. |
| parser-bypass-hardening | 051500ZMAY26 | Segmentation/expansion hardening, redteam tests, SECURITY/CHANGELOG; Q-table ratified. |

## Parked

*Deliberately not pursued (**PARKED**); superseded or withdrawn specs under `specs/parked/`. Use `spec_park` from [`@rethunk/citadel-sdd`](https://github.com/Rethunk-AI/citadel-sdd).*

| Slug | DTG | Note |
|------|-----|------|
| _(none)_ | | |




