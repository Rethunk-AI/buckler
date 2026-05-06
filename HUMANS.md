# HUMANS.md — Buckler Operator Guide

## Install

### Prerequisites

| Platform | Requirements |
|----------|-------------|
| Linux | `bash`, `curl`, `uv`, `cosign` |
| macOS | `bash`, `curl`, `uv`, `cosign` (Homebrew: `brew install uv cosign`) |
| Windows | Git Bash (Git for Windows), `uv`, `cosign` |

Install `uv`: https://docs.astral.sh/uv/getting-started/installation/
Install `cosign`: https://docs.sigstore.dev/cosign/system_config/installation/

### One-liner (Linux / macOS / Git Bash)

```bash
curl -fsSL https://github.com/Rethunk-AI/buckler/releases/latest/download/setup.sh | bash -s install
```

### Verify before run (recommended)

```bash
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/setup.sh
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/buckler-latest.tar.gz
curl -fsSLO https://github.com/Rethunk-AI/buckler/releases/latest/download/buckler-latest.tar.gz.bundle

cosign verify-blob buckler-latest.tar.gz \
  --bundle buckler-latest.tar.gz.bundle \
  --certificate-identity-regexp "https://github.com/Rethunk-AI/buckler/.github/workflows/release.yml" \
  --certificate-oidc-issuer "https://token.actions.githubusercontent.com"

bash setup.sh install
```

### What the installer does

1. Verifies the Cosign bundle for the release tarball.
2. Unpacks the tarball to `~/.local/share/buckler/versions/<version>/`.
3. Creates (or updates) `~/.local/share/buckler/current` symlink (Unix) / `current.json` (Windows).
4. Runs `uv sync --frozen` inside the unpacked tree to materialize the venv.
5. Merges Buckler hook entries into `~/.cursor/hooks.json` (idempotent).

### Paths

| Platform | Data | Config | State |
|----------|------|--------|-------|
| Linux / macOS | `$XDG_DATA_HOME/buckler` → `~/.local/share/buckler` | `$XDG_CONFIG_HOME/buckler` → `~/.config/buckler` | `$XDG_STATE_HOME/buckler` → `~/.local/state/buckler` |
| Windows (Git Bash) | `$LOCALAPPDATA/Buckler` | `$APPDATA/Buckler` | `$LOCALAPPDATA/Buckler/state` |

Override any path with `BUCKLER_DATA_HOME`, `BUCKLER_CONFIG_HOME`, `BUCKLER_STATE_HOME`.

Full path contract: [docs/paths.md](docs/paths.md).

---

## Update

```bash
bash setup.sh update
```

Downloads the latest release, verifies the Cosign signature, refreshes the `current` symlink, re-runs `uv sync --frozen`, and re-merges `hooks.json`.

---

## Uninstall

```bash
bash setup.sh uninstall
```

Removes Buckler's entries from `~/.cursor/hooks.json` and the installed data directory. Configuration (`~/.config/buckler/`) is preserved by default.

```bash
bash setup.sh uninstall --purge-config
```

Also removes configuration and user rules.

### Migrate from `rethunk-mcp-nudge.py`

```bash
bash setup.sh install --purge-legacy
```

This removes the legacy `rethunk-mcp-nudge.py` hook entries from `~/.cursor/hooks.json`. The `agent-git` pack supersedes all nudge rules from the old script.

---

## Packs

Packs are YAML files that define policy rules. Buckler discovers packs in this order (later files override earlier rules of equal priority):

1. **Builtin packs** — shipped with Buckler in `~/.local/share/buckler/current/packs/`.
2. **User rules** — `~/.config/buckler/rules.d/*.yaml` (or Windows equivalent), loaded in alphabetical order.

### Enabled packs (default)

| Pack | File | Enabled |
|------|------|---------|
| `agent-git` | `packs/agent-git.yaml` | Yes |

To disable a builtin pack, add a user rule file with `pack_override: { agent-git: { enabled: false } }` (see [docs/rule-schema.md](docs/rule-schema.md)).

### Writing user rules

User rules use the same schema as builtin packs. Place files in `~/.config/buckler/rules.d/` with a `.yaml` extension.

```yaml
pack: my-rules
version: "1"
rules:
  - id: deny-rm-rf
    trigger: [pre_shell_exec, pre_shell_tool]
    match:
      shell_segments:
        - program: rm
          flags_any: ["-rf", "-fr", "--recursive"]
    action: deny
    priority: 200
    user_message: "rm -rf is blocked by your local Buckler rules."
    agent_message: "BLOCKED: rm -rf. Use safer file removal instead."
```

Full schema: [docs/rule-schema.md](docs/rule-schema.md).

---

## Bypass

To let a single command through without uninstalling Buckler:

```bash
RETHUNK_ALLOW_SHELL=1 git commit -m "emergency bypass"
```

Buckler checks for `RETHUNK_ALLOW_SHELL=1` in the shell environment and returns `allow` without evaluating rules.

**This bypass is logged** to `~/.local/state/buckler/audit.log` (if audit logging is enabled in your config).

---

## Configuration

The main config file lives at `~/.config/buckler/config.toml` (created on first run with defaults).

```toml
[core]
# Policy tier: "baseline" (default) or "strict"
tier = "baseline"

# Log bypass events and rule decisions
audit_log = false

[packs]
# Disable a builtin pack
# agent-git = { enabled = false }
```

---

## Troubleshooting

### Hook not firing

1. Confirm Buckler entries exist in `~/.cursor/hooks.json`:
   ```bash
   python -m buckler.hooks status
   ```
2. Confirm the venv is intact:
   ```bash
   ~/.local/share/buckler/current/.venv/bin/python -m buckler --version
   ```
3. Re-run the installer to repair:
   ```bash
   bash setup.sh install
   ```

### `cosign` not found

Install cosign: https://docs.sigstore.dev/cosign/system_config/installation/

On macOS: `brew install cosign`
On Linux: `go install github.com/sigstore/cosign/v2/cmd/cosign@latest` or use the package for your distro.

### Windows: "bash not found"

Buckler requires Git Bash on Windows. Install [Git for Windows](https://git-scm.com/downloads/win), which includes Git Bash.

### Policy decision is wrong

Run Buckler's evaluate command against a crafted `PolicyInput` to debug:

```bash
echo '{"policy_io_version":"1","trigger":"pre_shell_exec","shell":{"command":"git commit -m test","cwd":"/tmp"}}' \
  | python -m buckler evaluate
```

See [docs/contracts/policy-io.md](docs/contracts/policy-io.md) for the full input/output schema.
