# Spec — parser-bypass-hardening

| | |
|---|---|
| Status | DONE 051500ZMAY26 — core segmentation/expansion + redteam tests + SECURITY/CHANGELOG. |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. |

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | When recursive `bash -c "…"` parse fails (unclosed quote, bad shlex), default decision for the wrapped portion is **deny** (matches `failClosed: true` posture; safer than allow). | **Ratified 051500ZMAY26** — **deny**; env-only bypass (`RETHUNK_ALLOW_SHELL=1`) still applies. |
| Q2 | `git commit-graph write`: keep exact-match and **fix the doc**. | **Ratified 051500ZMAY26** — **doc fix** (already in `docs/agent-git.md` + redteam test). |
| Q3 | Env-var prefix / `env` wrapper: treat as wrapped command for matching. | **Ratified 051500ZMAY26** — **unwrap** via `_strip_env_prefix_tokens` in `_parse_segment_tokens`. |
| Q4 | Recursion depth bound. Proposal: **3 levels**; beyond that, deny. | **Ratified 051500ZMAY26** — **depth 3** |
| Q5 | Pipeline / multi-segment: **deny if any expanded segment matches a deny rule**. | **Ratified 051500ZMAY26** — **deny-any** |

## Acceptance

All A1–A9 satisfied in implementation: `src/buckler/core.py`, `tests/test_agent_git_redteam.py`, `tests/test_core.py`, `SECURITY.md`, `CHANGELOG.md`.
