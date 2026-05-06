"""Canonical path resolution for Buckler.

Resolution order (highest → lowest priority):
  1. BUCKLER_* environment overrides
  2. XDG_* variables (Unix) / Windows Known Folder env vars (Git Bash)
  3. XDG defaults: ~/.local/share, ~/.config, ~/.local/state
"""

from __future__ import annotations

import json
import os
import platform
from pathlib import Path


def _env_or(*names: str, default: Path) -> Path:
    """Return the path from the first non-empty env var, or the default."""
    for name in names:
        val = os.environ.get(name, "").strip()
        if val:
            return Path(val)
    return default


def _home() -> Path:
    return Path.home()


def _is_windows() -> bool:
    return platform.system() == "Windows" or bool(os.environ.get("COMSPEC"))


def data_dir() -> Path:
    """Root for installed Buckler versions and builtin packs."""
    if _is_windows():
        default = Path(os.environ.get("LOCALAPPDATA", _home() / "AppData" / "Local")) / "Buckler"
    else:
        default = _env_or("XDG_DATA_HOME", default=_home() / ".local" / "share") / "buckler"
    return _env_or("BUCKLER_DATA_HOME", default=default)


def config_dir() -> Path:
    """Root for user config and rules.d overlays."""
    if _is_windows():
        default = Path(os.environ.get("APPDATA", _home() / "AppData" / "Roaming")) / "Buckler"
    else:
        default = _env_or("XDG_CONFIG_HOME", default=_home() / ".config") / "buckler"
    return _env_or("BUCKLER_CONFIG_HOME", default=default)


def state_dir() -> Path:
    """Root for audit log and runtime state."""
    if _is_windows():
        default = (
            Path(os.environ.get("LOCALAPPDATA", _home() / "AppData" / "Local"))
            / "Buckler"
            / "state"
        )
    else:
        default = _env_or("XDG_STATE_HOME", default=_home() / ".local" / "state") / "buckler"
    return _env_or("BUCKLER_STATE_HOME", default=default)


def current_dir() -> Path | None:
    """Resolve the 'current' version pointer.

    Unix: data_dir()/current symlink → versions/<ver>/
    Windows: data_dir()/current.json → {"path": "C:\\..."}
    Returns None if not installed.
    """
    base = data_dir()
    if _is_windows():
        current_json = base / "current.json"
        if current_json.exists():
            try:
                info = json.loads(current_json.read_text())
                return Path(info["path"])
            except (KeyError, json.JSONDecodeError, OSError):
                return None
        return None
    link = base / "current"
    if link.exists() or link.is_symlink():
        return link.resolve()
    return None


def packs_dir() -> Path:
    """Directory for builtin packs shipped with Buckler."""
    cur = current_dir()
    if cur is not None:
        return cur / "packs"
    # Development fallback: packs/ relative to this file's package root
    return Path(__file__).parent.parent.parent / "packs"


def user_rules_dir() -> Path:
    """User rule overlay directory ($XDG_CONFIG_HOME/buckler/rules.d/)."""
    return config_dir() / "rules.d"


def config_file() -> Path:
    """Main operator config file."""
    return config_dir() / "config.toml"


def audit_log() -> Path:
    """Audit log path."""
    return state_dir() / "audit.log"


def cursor_hooks_json() -> Path:
    """Cursor's global hooks.json path."""
    return _home() / ".cursor" / "hooks.json"


def project_venv_python(project_root: Path) -> Path | None:
    """Return the interpreter inside ``project_root/.venv`` if it exists."""
    if _is_windows():
        candidate = project_root / ".venv" / "Scripts" / "python.exe"
    else:
        candidate = project_root / ".venv" / "bin" / "python"
    return candidate if candidate.exists() else None
