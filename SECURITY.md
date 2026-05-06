# Security

## Threat model

Buckler protects against **unintended agentic shell actions**. Its threat model covers:

| Threat | Mitigation |
|--------|-----------|
| Agent runs destructive `gh` commands (`repo delete`, `api` DELETE, …) | `agent-gh` pack denies baseline destructive subcommands |
| Agent force-pushes or deletes remote branches | Deny rules on `--force`, `-f`, `--delete`, `--mirror`, `:branch` push |
| Agent removes or rewrites a remote | Deny rules on `git remote remove`, configurable on `set-url` |
| Agent bypasses the hook (shell escape) | `failClosed: true` on critical hooks; see [Known parser bypasses (status)](#known-parser-bypasses-status) (not all shell-escape families are closed yet) |
| Tampered release artifact | Cosign keyless verification in `setup.sh` before any extraction |
| Malicious user rules | Rules run in the same process as Buckler; no sandbox. User rules are trusted. |

### Known parser bypasses (status)

The `agent-git` pack's shell parser is **not** a full POSIX `bash` implementation. The table below lists **unmitigated** bypass classes that an agent can use today; see the remediation spec for the full matrix and test plan. When a class is fixed in a release, the row is marked **closed** with that version and a matching entry is added to `CHANGELOG.md`.

| Bypass class | Status | Remediation / tracking |
|--------------|--------|------------------------|
| `&` (background) — e.g. `git status & git commit` | open | [specs/active/parser-bypass-hardening/spec.md](specs/active/parser-bypass-hardening/spec.md) |
| Shell pipe between commands (see remediation spec for examples) | open | [specs/active/parser-bypass-hardening/spec.md](specs/active/parser-bypass-hardening/spec.md) |
| Command substitution `$(…)` and backticks | open | same |
| `bash -c` / `sh -c` string not recursed | open | same (see also threat row above) |
| Env prefix / `env` — e.g. `FOO=bar git commit`, `env … git commit` | open | same |

### V1 scope (local-only)

Buckler v1 is a **local tool** — it does not contact any remote service at runtime. Policy evaluation is offline. The only network access is during `setup.sh install/update` to download releases from GitHub.

### Bypass

`RETHUNK_ALLOW_SHELL=1` bypasses all rules. This is intentional for emergency use. With audit logging enabled, bypasses are recorded to `~/.local/state/buckler/audit.log`.

---

## Release verification (Cosign keyless)

Every release tarball is signed via [Sigstore](https://sigstore.dev) keyless signing in GitHub Actions. The signing identity is the OIDC token of the release workflow.

### Verify on Linux / macOS / Git Bash

```bash
# Download artifacts
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/buckler-latest.tar.gz
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/buckler-latest.tar.gz.bundle

# Verify (cosign must be installed)
cosign verify-blob buckler-latest.tar.gz \
  --bundle buckler-latest.tar.gz.bundle \
  --certificate-identity-regexp "https://github.com/Rethunk-AI/buckler/.github/workflows/release.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"
```

A successful verification prints `Verified OK`. Do not proceed if verification fails.

---

## Vulnerability reporting

Please **do not** open a public GitHub issue for security vulnerabilities.

Report privately via GitHub Security Advisories:
https://github.com/Rethunk-AI/buckler/security/advisories/new

Or email the maintainers directly (see the org contact in the GitHub profile).

We aim to respond within **72 hours** and publish a fix within **7 days** for critical issues.
