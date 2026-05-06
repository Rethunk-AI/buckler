# Path Resolution

`buckler.paths` is the canonical path resolver. `scripts/setup.sh` must match it.

## Resolution order

For each directory, Buckler checks (in order) and uses the first set variable:

1. `BUCKLER_*` environment overrides (highest priority)
2. XDG standard variables (Unix) / Windows Known Folder env vars (Git Bash)
3. XDG defaults (`~/.local/share`, `~/.config`, `~/.local/state`)

## Unix (Linux / macOS)

| Purpose | Env override | XDG variable | Default |
|---------|-------------|-------------|---------|
| Installed versions, packs | `BUCKLER_DATA_HOME` | `XDG_DATA_HOME` | `~/.local/share/buckler` |
| Config, user rules | `BUCKLER_CONFIG_HOME` | `XDG_CONFIG_HOME` | `~/.config/buckler` |
| Audit log, state | `BUCKLER_STATE_HOME` | `XDG_STATE_HOME` | `~/.local/state/buckler` |

## Windows (Git Bash)

Git Bash exposes Windows Known Folder paths as Unix-style env vars:

| Purpose | Env override | Windows env | Example path |
|---------|-------------|-------------|--------------|
| Installed versions, packs | `BUCKLER_DATA_HOME` | `$LOCALAPPDATA/Buckler` | `C:\Users\you\AppData\Local\Buckler` |
| Config, user rules | `BUCKLER_CONFIG_HOME` | `$APPDATA/Buckler` | `C:\Users\you\AppData\Roaming\Buckler` |
| Audit log, state | `BUCKLER_STATE_HOME` | `$LOCALAPPDATA/Buckler/state` | `C:\Users\you\AppData\Local\Buckler\state` |

`buckler.paths` normalizes Windows paths via `pathlib.Path` before writing to `hooks.json` (Cursor on Windows requires native backslash paths or forward-slash paths—we use `pathlib.Path.as_posix()` for `hooks.json` entries).

## Directory layout

```
$BUCKLER_DATA_HOME/
  versions/
    0.1.0/          # unpacked release tarball
      packs/
      src/
      .venv/
      ...
    0.2.0/
  current -> versions/0.2.0   # symlink (Unix) or current.json (Windows)

$BUCKLER_CONFIG_HOME/
  config.toml
  rules.d/
    my-rules.yaml   # user-defined packs (sorted alphabetically)

$BUCKLER_STATE_HOME/
  audit.log         # bypass events and rule decisions (optional)
```

## `current` pointer

- **Unix:** `$BUCKLER_DATA_HOME/current` is a symlink to `versions/<version>/`.
- **Windows:** `$BUCKLER_DATA_HOME/current.json` contains `{"version": "0.2.0", "path": "C:\\...\\versions\\0.2.0"}`.

`buckler.paths.current_dir()` resolves `current` transparently on both platforms.

## `hooks.json` location

Cursor's global `hooks.json` lives at:

| Platform | Path |
|----------|------|
| Linux | `~/.cursor/hooks.json` |
| macOS | `~/.cursor/hooks.json` |
| Windows | `%USERPROFILE%\.cursor\hooks.json` → `$HOME/.cursor/hooks.json` in Git Bash |

`buckler.hooks.merge()` writes absolute paths to `hooks.json`; on Windows it uses the native form (`cygpath -w` or `pathlib.PureWindowsPath` from `HOMEDRIVE`/`HOMEPATH`).
