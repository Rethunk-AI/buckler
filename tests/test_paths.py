"""Tests for buckler.paths — canonical path resolution."""

from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

import pytest


class TestPaths:
    def test_buckler_data_home_override(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """BUCKLER_DATA_HOME overrides every other path source."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path / "custom"))
        from buckler import paths

        assert paths.data_dir() == tmp_path / "custom"

    def test_xdg_vars_respected(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """XDG_DATA/CONFIG/STATE_HOME are all honoured as fallbacks (Unix layout)."""
        monkeypatch.delenv("BUCKLER_DATA_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_CONFIG_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_STATE_HOME", raising=False)
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
        monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.data_dir() == tmp_path / "data" / "buckler"
            assert paths.config_dir() == tmp_path / "cfg" / "buckler"
            assert paths.state_dir() == tmp_path / "state" / "buckler"

    def test_windows_paths_use_appdata(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """On Windows, LOCALAPPDATA/APPDATA env vars drive all three dir functions."""
        monkeypatch.delenv("BUCKLER_DATA_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_CONFIG_HOME", raising=False)
        monkeypatch.delenv("BUCKLER_STATE_HOME", raising=False)
        monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "local"))
        monkeypatch.setenv("APPDATA", str(tmp_path / "roaming"))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.data_dir() == tmp_path / "local" / "Buckler"
            assert paths.config_dir() == tmp_path / "roaming" / "Buckler"
            assert paths.state_dir() == tmp_path / "local" / "Buckler" / "state"

    def test_current_dir_unix_follows_symlink(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """Unix: current_dir() resolves the current symlink to the installed version."""
        ver_dir = tmp_path / "versions" / "0.1.0"
        ver_dir.mkdir(parents=True)
        (tmp_path / "current").symlink_to(ver_dir)
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.current_dir() == ver_dir.resolve()

    def test_current_dir_unix_returns_none_when_absent(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """Unix: current_dir() returns None when no symlink exists (dev environment)."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.current_dir() is None

    def test_current_dir_windows_reads_json(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Windows: current_dir() reads current.json and returns the path it contains."""
        ver_dir = tmp_path / "versions" / "0.1.0"
        ver_dir.mkdir(parents=True)
        (tmp_path / "current.json").write_text(json.dumps({"path": str(ver_dir)}))
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.current_dir() == ver_dir

    def test_current_dir_windows_error_recovery(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        """Windows: bad/missing JSON in current.json returns None rather than raising."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.current_dir() is None

            (tmp_path / "current.json").write_text("not json")
            assert paths.current_dir() is None

            (tmp_path / "current.json").write_text(json.dumps({"version": "0.1.0"}))
            assert paths.current_dir() is None

    def test_packs_dir_prefers_installed_location(self, tmp_path: Path):
        """packs_dir() returns <current>/packs when an installed version is active."""
        ver_dir = tmp_path / "versions" / "0.1.0"
        (ver_dir / "packs").mkdir(parents=True)
        with mock.patch("buckler.paths.current_dir", return_value=ver_dir):
            from buckler import paths

            assert paths.packs_dir() == ver_dir / "packs"

    def test_audit_log_is_inside_state_dir(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """audit_log() must be a child of state_dir() named audit.log."""
        monkeypatch.setenv("BUCKLER_STATE_HOME", str(tmp_path))
        from buckler import paths

        assert paths.audit_log() == tmp_path / "audit.log"

    def test_cursor_hooks_json_path(self):
        """cursor_hooks_json() must point at ~/.cursor/hooks.json."""
        from buckler import paths

        assert paths.cursor_hooks_json() == Path.home() / ".cursor" / "hooks.json"

    def test_current_dir_windows_no_file(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """Windows: current_dir() returns None when current.json is absent."""
        monkeypatch.setenv("BUCKLER_DATA_HOME", str(tmp_path))
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.current_dir() is None

    def test_project_venv_python_unix(self, tmp_path: Path):
        py = tmp_path / ".venv" / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.write_text("")
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.project_venv_python(tmp_path) == py

    def test_project_venv_python_windows(self, tmp_path: Path):
        py = tmp_path / ".venv" / "Scripts" / "python.exe"
        py.parent.mkdir(parents=True)
        py.write_text("")
        with mock.patch("buckler.paths._is_windows", return_value=True):
            from buckler import paths

            assert paths.project_venv_python(tmp_path) == py

    def test_project_venv_python_missing(self, tmp_path: Path):
        with mock.patch("buckler.paths._is_windows", return_value=False):
            from buckler import paths

            assert paths.project_venv_python(tmp_path) is None

    def test_is_windows_comspec_on_linux_is_false(self, monkeypatch: pytest.MonkeyPatch):
        """Linux (or any non-Windows POSIX) must not treat COMSPEC alone as Windows."""
        monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
        monkeypatch.setenv("OSTYPE", "linux-gnu")
        with mock.patch("buckler.paths.platform.system", return_value="Linux"):
            from buckler.paths import _is_windows

            assert _is_windows() is False

    def test_is_windows_true_when_platform_name_is_windows(self):
        with mock.patch("buckler.paths.platform.system", return_value="Windows"):
            from buckler.paths import _is_windows

            assert _is_windows() is True

    @pytest.mark.parametrize("otype", ["msys", "cygwin"])
    def test_is_windows_msys_cygwin_uses_comspec_when_not_windows_platform(
        self, monkeypatch: pytest.MonkeyPatch, otype: str
    ):
        """Git Bash / Cygwin: treat as Windows layout when COMSPEC is set (path resolution)."""
        monkeypatch.setenv("OSTYPE", otype)
        monkeypatch.setenv("COMSPEC", r"C:\Windows\System32\cmd.exe")
        with mock.patch("buckler.paths.platform.system", return_value="Linux"):
            from buckler.paths import _is_windows

            assert _is_windows() is True
