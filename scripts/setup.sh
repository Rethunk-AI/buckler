#!/usr/bin/env bash
# Buckler setup script — install | update | uninstall
# Supports Linux, macOS, and Windows (Git Bash).
# Usage:
#   bash setup.sh install [--purge-legacy]
#   bash setup.sh update
#   bash setup.sh uninstall [--purge-config]
set -euo pipefail

# ── Constants ────────────────────────────────────────────────────────────────
BUCKLER_REPO="Rethunk-AI/buckler"
BUCKLER_RELEASE_BASE="https://github.com/${BUCKLER_REPO}/releases"
BUCKLER_HOOK_PREFIX="buckler:"
# Deliberate shellcheck failure to prove CI gate (remove after red run).
SHELLCHECK_PROOF_SC2034=1
SCRIPT_VERSION="0.1.0"

# ── Utilities ────────────────────────────────────────────────────────────────
_info()  { printf '\033[0;34m[buckler]\033[0m %s\n' "$*"; }
_ok()    { printf '\033[0;32m[buckler]\033[0m %s\n' "$*"; }
_warn()  { printf '\033[0;33m[buckler]\033[0m WARNING: %s\n' "$*" >&2; }
_die()   { printf '\033[0;31m[buckler]\033[0m ERROR: %s\n' "$*" >&2; exit 1; }

_require() {
    command -v "$1" >/dev/null 2>&1 || _die "'$1' is required but not found. $2"
}

_is_windows() {
    [[ "${OSTYPE:-}" == "msys" ]] || [[ "${OSTYPE:-}" == "cygwin" ]] || \
    [[ -n "${COMSPEC:-}" ]]
}

# ── Path resolution (mirrors buckler.paths) ───────────────────────────────────
_data_dir() {
    if _is_windows; then
        echo "${BUCKLER_DATA_HOME:-${LOCALAPPDATA:-$HOME/AppData/Local}/Buckler}"
    else
        local xdg="${XDG_DATA_HOME:-$HOME/.local/share}"
        echo "${BUCKLER_DATA_HOME:-$xdg/buckler}"
    fi
}

_config_dir() {
    if _is_windows; then
        echo "${BUCKLER_CONFIG_HOME:-${APPDATA:-$HOME/AppData/Roaming}/Buckler}"
    else
        local xdg="${XDG_CONFIG_HOME:-$HOME/.config}"
        echo "${BUCKLER_CONFIG_HOME:-$xdg/buckler}"
    fi
}

_cursor_hooks_json() {
    echo "$HOME/.cursor/hooks.json"
}

_versions_dir() { echo "$(_data_dir)/versions"; }
_current_link()  { echo "$(_data_dir)/current"; }

# ── Version resolution ────────────────────────────────────────────────────────
_latest_version() {
    local url="${BUCKLER_RELEASE_BASE}/latest"
    local redirect
    redirect=$(curl -fsSLI -o /dev/null -w '%{url_effective}' "$url" 2>/dev/null)
    basename "$redirect"
}

_current_version() {
    local cur
    cur="$(_current_link)"
    if _is_windows; then
        local json="${cur}.json"
        [[ -f "$json" ]] && python3 -c "import json,sys; print(json.load(open('$json'))['version'])" 2>/dev/null || echo ""
    else
        [[ -L "$cur" ]] && basename "$(readlink -f "$cur")" || echo ""
    fi
}

# ── Download and verify ───────────────────────────────────────────────────────
_download_release() {
    local version="$1"
    local dest_dir="$2"
    local tarball="buckler-${version}.tar.gz"
    local bundle="${tarball}.bundle"
    local base_url="${BUCKLER_RELEASE_BASE}/download/${version}"

    _info "Downloading Buckler ${version}..."
    mkdir -p "$dest_dir"
    curl -fsSL "${base_url}/${tarball}" -o "${dest_dir}/${tarball}"
    curl -fsSL "${base_url}/${bundle}" -o "${dest_dir}/${bundle}"

    _info "Verifying Cosign signature..."
    cosign verify-blob "${dest_dir}/${tarball}" \
        --bundle "${dest_dir}/${bundle}" \
        --certificate-identity-regexp "https://github.com/${BUCKLER_REPO}/.github/workflows/release.yml" \
        --certificate-oidc-issuer "https://token.actions.githubusercontent.com" \
        || _die "Cosign verification failed. Do not proceed."
    _ok "Signature verified."

    _info "Extracting..."
    local install_dir
    install_dir="$(_versions_dir)/${version}"
    mkdir -p "$install_dir"
    tar -xzf "${dest_dir}/${tarball}" -C "$install_dir" --strip-components=1
    rm -f "${dest_dir}/${tarball}" "${dest_dir}/${bundle}"
    echo "$install_dir"
}

# ── Venv setup ────────────────────────────────────────────────────────────────
_setup_venv() {
    local install_dir="$1"
    _info "Setting up Python environment (uv sync --frozen)..."
    (cd "$install_dir" && uv sync --frozen) \
        || _die "uv sync --frozen failed in ${install_dir}"
}

# ── Current pointer ───────────────────────────────────────────────────────────
_set_current() {
    local version="$1"
    local install_dir
    install_dir="$(_versions_dir)/${version}"
    local cur
    cur="$(_current_link)"

    if _is_windows; then
        # Write current.json (no symlinks on Windows without elevated perms)
        python3 -c "
import json, pathlib
d = {'version': '${version}', 'path': str(pathlib.Path('${install_dir}').resolve())}
pathlib.Path('${cur}.json').write_text(json.dumps(d))
"
    else
        ln -sfn "$install_dir" "$cur"
    fi
    _ok "Current set to ${version}"
}

# ── hooks.json merge ──────────────────────────────────────────────────────────
_venv_python() {
    local cur
    cur="$(_current_link)"
    if _is_windows; then
        local json="${cur}.json"
        if [[ -f "$json" ]]; then
            python3 -c "import json,pathlib; p=pathlib.Path(json.load(open('$json'))['path'])/'.venv/Scripts/python.exe'; print(p)"
        fi
    else
        echo "${cur}/.venv/bin/python"
    fi
}

_merge_hooks() {
    local py
    py="$(_venv_python)"
    if [[ -z "$py" ]] || [[ ! -f "$py" ]]; then
        _warn "Cannot find Buckler venv Python; hooks.json merge skipped."
        return
    fi
    _info "Merging Buckler entries into hooks.json..."
    "$py" -m buckler.hooks merge --venv-python "$py" \
        --hooks-json "$(_cursor_hooks_json)" \
        || _warn "hooks.json merge failed; run manually: $py -m buckler.hooks merge"
    _ok "hooks.json updated."
}

_strip_hooks() {
    local py
    py="$(_venv_python)"
    if [[ -z "$py" ]] || [[ ! -f "$py" ]]; then
        _warn "Cannot find Buckler venv Python; will attempt hooks.json strip with system Python."
        py="python3"
    fi
    _info "Removing Buckler entries from hooks.json..."
    "$py" -m buckler.hooks strip \
        --hooks-json "$(_cursor_hooks_json)" 2>/dev/null \
        || _warn "Could not strip hooks.json automatically. Remove '${BUCKLER_HOOK_PREFIX}'* entries manually."
}

# ── Legacy migration ───────────────────────────────────────────────────────────
_purge_legacy() {
    local hooks_json
    hooks_json="$(_cursor_hooks_json)"
    [[ -f "$hooks_json" ]] || return 0
    _info "Removing legacy rethunk-mcp-nudge.py hook entries (active hook prefix: ${BUCKLER_HOOK_PREFIX})..."
    python3 - "$hooks_json" <<'PYEOF'
import json, sys
path = sys.argv[1]
with open(path) as f:
    data = json.load(f)
hooks = data.get("hooks", [])
before = len(hooks)
hooks = [h for h in hooks if "rethunk-mcp-nudge" not in str(h.get("command", ""))]
removed = before - len(hooks)
data["hooks"] = hooks
with open(path, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
if removed:
    print(f"[buckler] Removed {removed} legacy rethunk-mcp-nudge entries.")
PYEOF
}

# ── Subcommands ───────────────────────────────────────────────────────────────
cmd_install() {
    local purge_legacy=0
    for arg in "$@"; do
        [[ "$arg" == "--purge-legacy" ]] && purge_legacy=1
    done

    _require curl "Install curl from your package manager."
    _require uv "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    _require cosign "Install cosign: https://docs.sigstore.dev/cosign/system_config/installation/"
    _require python3 "Python 3 is required."

    if _is_windows; then
        command -v bash >/dev/null 2>&1 || _die "Git Bash is required on Windows. Install Git for Windows."
    fi

    local version
    version="${BUCKLER_VERSION:-$(_latest_version)}"
    [[ -n "$version" ]] || _die "Could not determine latest version."

    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT

    local install_dir
    install_dir="$(_download_release "$version" "$tmp_dir")"
    _setup_venv "$install_dir"
    _set_current "$version"
    _merge_hooks

    [[ "$purge_legacy" -eq 1 ]] && _purge_legacy

    _ok "Buckler ${version} installed. Restart Cursor to activate."
    _info "Verify: $(_venv_python) -m buckler --version"
}

cmd_update() {
    _require curl "Install curl."
    _require uv "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
    _require cosign "Install cosign."

    local current
    current="$(_current_version)"
    local latest
    latest="${BUCKLER_VERSION:-$(_latest_version)}"

    if [[ -n "$current" ]] && [[ "$current" == "$latest" ]]; then
        _ok "Already at latest version: ${latest}"
        exit 0
    fi

    _info "Updating ${current:-<none>} → ${latest}..."

    local tmp_dir
    tmp_dir="$(mktemp -d)"
    trap 'rm -rf "$tmp_dir"' EXIT

    local install_dir
    install_dir="$(_download_release "$latest" "$tmp_dir")"
    _setup_venv "$install_dir"
    _set_current "$latest"
    _merge_hooks

    _ok "Buckler updated to ${latest}. Restart Cursor."
}

cmd_uninstall() {
    local purge_config=0
    for arg in "$@"; do
        [[ "$arg" == "--purge-config" ]] && purge_config=1
    done

    _strip_hooks

    local versions_dir
    versions_dir="$(_versions_dir)"
    if [[ -d "$versions_dir" ]]; then
        _info "Removing installed versions from ${versions_dir}..."
        rm -rf "$versions_dir"
    fi

    local cur
    cur="$(_current_link)"
    [[ -L "$cur" ]] && rm -f "$cur"
    [[ -f "${cur}.json" ]] && rm -f "${cur}.json"

    if [[ "$purge_config" -eq 1 ]]; then
        local cfg
        cfg="$(_config_dir)"
        if [[ -d "$cfg" ]]; then
            _info "Removing config directory: ${cfg}"
            rm -rf "$cfg"
        fi
    fi

    _ok "Buckler uninstalled."
    [[ "$purge_config" -eq 0 ]] && \
        _info "Config preserved at $(_config_dir). Re-run with --purge-config to also remove it."
}

# ── Entry point ───────────────────────────────────────────────────────────────
main() {
    local cmd="${1:-}"
    shift || true

    case "$cmd" in
        install)   cmd_install "$@" ;;
        update)    cmd_update "$@" ;;
        uninstall) cmd_uninstall "$@" ;;
        --version|-V) echo "buckler setup.sh ${SCRIPT_VERSION}"; exit 0 ;;
        *)
            printf 'Usage: bash setup.sh <install|update|uninstall> [options]\n\n'
            printf 'Options:\n'
            printf '  install   --purge-legacy    Remove legacy rethunk-mcp-nudge.py hook entries\n'
            printf '  uninstall --purge-config    Also remove $XDG_CONFIG_HOME/buckler/\n\n'
            printf 'Environment:\n'
            printf '  BUCKLER_VERSION    Pin a specific release tag (default: latest)\n'
            printf '  BUCKLER_DATA_HOME  Override data directory\n'
            printf '  BUCKLER_CONFIG_HOME Override config directory\n'
            exit 1
            ;;
    esac
}

main "$@"
