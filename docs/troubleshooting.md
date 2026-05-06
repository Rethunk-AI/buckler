# Troubleshooting

Operator playbook for common Buckler issues. See also [HUMANS.md](../HUMANS.md), [SECURITY.md](../SECURITY.md), and the policy contract at [docs/contracts/policy-io.md](contracts/policy-io.md).

---

## Hook didn't fire at all

**Symptoms:** `git commit` (or another watched command) ran when you expected Buckler to intercept it; no new line in `~/.local/state/buckler/audit.log` (when audit logging is enabled).

**Checks:**

1. **Hooks wiring:** `python -m buckler.hooks status` — confirm Buckler entries exist under `~/.cursor/hooks.json`.
2. **Interpreter:** run Buckler from the installed venv (paths vary by OS):
   ```bash
   ~/.local/share/buckler/current/.venv/bin/python -m buckler --version
   ```
3. **Hook command resolves:** open `~/.cursor/hooks.json` and confirm the `buckler:` hook `command` points at a Python that exists.

---

## Hook fired but the command was allowed when I expected deny

**Goal:** reproduce the same decision offline.

1. **Capture the payload** Cursor sent to the hook (same JSON shape as `PolicyInput`). There is no built-in `BUCKLER_DEBUG` env var today — use a thin wrapper script around Buckler that logs stdin to a file, or copy the payload from Cursor logs if your harness exposes it.
2. **Replay:** pipe that JSON into evaluation:
   ```bash
   python -m buckler evaluate < payload.json
   ```
3. **Compare** the emitted decision to your expectation.

**Common cause:** parser bypass — the shell command was segmented or escaped in a way rules never see. See [SECURITY.md § Known parser bypasses](../SECURITY.md#known-parser-bypasses-status) and [specs/done/parser-bypass-hardening/spec.md](../specs/done/parser-bypass-hardening/spec.md).

---

## Policy decision is wrong

1. **`buckler validate`** — confirm pack YAML loads cleanly (bad YAML may be skipped at runtime with warnings only).
2. **User overrides:** inspect `~/.config/buckler/rules.d/` for a user rule that overrides a builtin or narrows scope differently than you expect.
3. **`config.toml`:** confirm `[core] tier` — `strict` promotes several nudges to denies compared to `baseline`.

---

## Windows: hook fires but immediately exits

Often path or quoting: Git Bash vs PowerShell, spaces in `hooks.json` command paths, or the hook binary not found. See [specs/active/hooks-cross-platform-quoting/spec.md](../specs/active/hooks-cross-platform-quoting/spec.md) for the cross-platform quoting posture.

---

## Audit log isn't being written

1. Set `audit_log = true` under `[core]` in `~/.config/buckler/config.toml`.
2. Confirm `~/.local/state/buckler/` (or your overridden state dir) exists and is writable.
3. Confirm the disk is not full — append-only logging fails closed if the OS cannot extend the file.

For retention and forwarding, see [HUMANS.md § Audit log operations](../HUMANS.md#audit-log-operations).
