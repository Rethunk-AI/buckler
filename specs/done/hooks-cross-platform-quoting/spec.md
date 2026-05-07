# Spec — hooks-cross-platform-quoting

| | |
|---|---|
| Status | DONE 051200ZMAY26 — POSIX `shlex.quote` for interpreter path in hooks.json; newline/CR refusal; tests + cursor/paths docs. |
| Authored | 060431ZMAY26 |
| Owner | Bastion (J-3) |
| Carry-forward from | 2026-05-05 P1–P10 review of buckler. `_buckler_command` in `src/buckler/hooks.py:48` builds the `hooks.json` `command` field by direct f-string concatenation of an unquoted `Path` and the literal `" -m buckler --driver cursor"`. Any whitespace in the venv-Python path silently breaks Cursor's command parsing. |

## Why

The default Windows install path for an installed Buckler venv is `C:\Users\<First Last>\AppData\Local\Buckler\versions\<ver>\.venv\Scripts\python.exe`. Many real-world Windows usernames contain spaces (`Damon Blais`, `John Smith`, etc.). On macOS, paths under `~/Library/Application Support` and the default `~/Pictures/Profile` setup also contain spaces. On Linux, less common but possible.

Today, the generated `hooks.json` command field becomes:

```
C:\Users\Damon Blais\AppData\Local\Buckler\...\python.exe -m buckler --driver cursor
```

Cursor parses that as `argv[0] = "C:\Users\Damon"`, hits "program not found," and **silently disables Buckler**. The hook fires, returns nothing useful, fail-closed never triggers because the hook itself fails to launch — the user gets no audit trail and no UI nudge. From the operator's perspective, deny rules just don't work and there's no obvious diagnostic.

CI doesn't catch this because every GitHub Actions runner uses space-free paths. The Windows test in `tests/test_hooks.py` exercises the venv-detection path but never builds a `hooks.json` command from a path containing spaces.

## In scope

### Quoting in `_buckler_command`

- On **all** platforms (Linux, macOS, Windows / Git Bash): wrap the interpreter path with **`shlex.quote(str(path))`** before concatenating the fixed tail. No separate `cmd.exe` / `list2cmdline` branch — Buckler assumes bash / Git Bash parses the hook command string on Windows.
- The `-m buckler --driver cursor` portion stays **bare** — those tokens have no whitespace (Q2).

### Tests

- New parametrize rows in `tests/test_hooks.py::TestHooks`:
  - Paths with spaces (Unix-style and `C:/Users/...` forms) — `shlex.split(..., posix=True)` recovers `argv[0]`.
  - Edge: path containing a single quote (Linux) or a literal `"` (Windows) — assert the round-trip survives.
- An end-to-end test that writes a generated `hooks.json` and asserts the `command` field parses with `shlex.split(..., posix=True)` and recovers the original interpreter path as `argv[0]`.

### Documentation

- `docs/adapters/cursor.md` "hooks.json wiring" section: the `command` field is a shell command string, not an argv array; Buckler applies POSIX `shlex.quote` to the interpreter path. Operators editing `hooks.json` by hand must do the same.
- `docs/paths.md` documents that `hooks.json` interpreter paths are POSIX-quoted and may appear in native or `as_posix()` form from `pathlib`.

## Out of scope

- Cursor's own command-string parsing quirks beyond the host shell's standard quoting. If Cursor adds a structured `argv` field for `command` in a future schema, switch to that and drop the string-quoting; until then, host-shell quoting is the contract.
- Other adapters (the planned Claude Code adapter inherits the same risk and should reuse the same helper, but that lives in the Claude Code adapter spec — out of scope here).
- Re-quoting the `setup.sh` Bash side; that script just shells out to `python -m buckler.hooks merge`, so all quoting concentrates in `_buckler_command`.
- Audit-logging of the generated command (separate concern; lives in `code-quality-sweep`).

## Decision log

| Q | Proposal | Status |
|---|----------|--------|
| Q1 | Windows quoting model: Buckler targets **Git Bash** on Windows. Proposal: use POSIX **`shlex.quote`** for the interpreter path on **all** platforms so the `hooks.json` `command` string parses under bash / Git Bash. | **Ratified 051200ZMAY26** — **POSIX `shlex.quote` everywhere** |
| Q2 | Should the `-m buckler --driver cursor` portion also be quoted, or left bare? Proposal: **bare** — these are fixed tokens with no whitespace, and quoting them adds noise that humans editing `hooks.json` will trip on. | **Ratified 051200ZMAY26** — **bare** |
| Q3 | When `venv_python` is `None` and we fall back to `sys.executable`, apply the same quoting? Proposal: **yes, unconditionally**. The fallback path also encounters spaces. | **Ratified 051200ZMAY26** — **yes** |
| Q4 | If a user's path contains a literal newline (rare but legal on Unix), refuse to write `hooks.json` rather than try to escape — `\n` in a `hooks.json` command field is broken regardless. Proposal: **refuse with a clear error message**. | **Ratified 051200ZMAY26** — **refuse** (also **CR**); `ValueError` |

## Acceptance

- A1. `_buckler_command(Path("/home/joe smith/.../python"))` returns a string that, when parsed by `shlex.split`, yields `argv[0] == "/home/joe smith/.../python"`.
- A2. `_buckler_command(Path("C:/Users/Damon Blais/.../python.exe"))` returns a string that, when parsed by `shlex.split(..., posix=True)` (Git Bash / bash posture), yields `argv[0] == "C:/Users/Damon Blais/.../python.exe"` (path string equality; drive-letter form preserved as passed in).
- A3. Test fixture covers paths with spaces (Unix-style and `C:/...` forms) and embedded quotes; same code path for Linux/macOS/Windows strings.
- A4. End-to-end test writes a `hooks.json` and re-parses the generated command field round-trip.
- A5. `docs/adapters/cursor.md` documents the quoting contract.
- A6. `docs/paths.md` reference is removed or made accurate (whichever fits the implementation).
- A7. 100% coverage maintained.
- A8. Q-table ratified.
