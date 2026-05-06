"""Tests for buckler.hooks — idempotent hooks.json management."""

from __future__ import annotations

import json
import shlex
import sys
from pathlib import Path
from unittest import mock

import pytest

PYTHON = sys.executable


class TestHooks:
    def test_merge_creates_all_three_entries(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge

        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        names = [h["name"] for h in json.loads(hooks_json.read_text())["hooks"]]
        assert {"buckler:pre-shell-exec", "buckler:pre-shell-tool", "buckler:post-tool"} <= set(
            names
        )

    def test_merge_is_idempotent(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge

        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        buckler = [
            h
            for h in json.loads(hooks_json.read_text())["hooks"]
            if h["name"].startswith("buckler:")
        ]
        assert len(buckler) == 3

    def test_merge_preserves_existing_hooks(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": [{"name": "other-tool", "event": "x"}]}))
        from buckler.hooks import merge

        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        names = [h["name"] for h in json.loads(hooks_json.read_text())["hooks"]]
        assert "other-tool" in names and "buckler:pre-shell-exec" in names

    def test_strip_removes_buckler_preserves_others(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            json.dumps(
                {
                    "hooks": [
                        {
                            "name": "buckler:pre-shell-exec",
                            "event": "beforeShellExecution",
                            "command": "x",
                        },
                        {"name": "other-tool", "event": "postToolUse"},
                    ]
                }
            )
        )
        from buckler.hooks import strip

        strip(hooks_path=hooks_json)
        names = [h["name"] for h in json.loads(hooks_json.read_text())["hooks"]]
        assert "other-tool" in names and "buckler:pre-shell-exec" not in names

    def test_merge_dry_run_prints_without_writing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge

        merge(hooks_path=hooks_json, venv_python=Path(PYTHON), dry_run=True)
        out = capsys.readouterr().out
        assert any(h["name"].startswith("buckler:") for h in json.loads(out)["hooks"])
        assert not hooks_json.exists()

    def test_strip_dry_run_reports_without_writing(
        self, tmp_path: Path, capsys: pytest.CaptureFixture
    ):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            json.dumps(
                {
                    "hooks": [
                        {
                            "name": "buckler:pre-shell-exec",
                            "event": "beforeShellExecution",
                            "command": "x",
                        }
                    ]
                }
            )
        )
        from buckler.hooks import strip

        strip(hooks_path=hooks_json, dry_run=True)
        assert "Would remove" in capsys.readouterr().out
        assert len(json.loads(hooks_json.read_text())["hooks"]) == 1

    def test_status_lists_installed_hooks(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge, status

        merge(hooks_path=hooks_json, venv_python=Path(PYTHON))
        status(hooks_path=hooks_json)
        assert "buckler:pre-shell-exec" in capsys.readouterr().out

    def test_status_reports_when_empty(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        from buckler.hooks import status

        status(hooks_path=hooks_json)
        assert "No Buckler hooks" in capsys.readouterr().out

    def test_merge_falls_back_when_no_venv_python(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import merge

        merge(hooks_path=hooks_json)
        assert any(
            h["name"].startswith("buckler:") for h in json.loads(hooks_json.read_text())["hooks"]
        )

    def test_read_hooks_json_returns_empty_on_bad_json(self, tmp_path: Path):
        bad = tmp_path / "hooks.json"
        bad.write_text("not json")
        from buckler.hooks import _read_hooks_json

        assert _read_hooks_json(bad) == {}

    @pytest.mark.parametrize(
        "interp",
        [
            Path("/home/joe smith/.local/share/buckler/.venv/bin/python"),
            Path("/home/joe's/.venv/bin/python"),
            Path("C:/Users/Damon Blais/AppData/Local/Buckler/.venv/Scripts/python.exe"),
            Path('C:/Users/x/weird"name/python.exe'),
        ],
    )
    def test_buckler_command_shlex_roundtrip_parametrize(self, interp: Path):
        from buckler.hooks import _buckler_command

        cmd = _buckler_command(venv_python=interp)
        argv = shlex.split(cmd, posix=True)
        assert argv[0] == str(interp)
        assert argv[1:] == ["-m", "buckler", "--driver", "cursor"]

    @pytest.mark.parametrize(
        "bad",
        ["/tmp/py\nthon", "/tmp/py\rthon", "C:/bad\r\n.exe"],
    )
    def test_buckler_command_rejects_line_break_in_path(self, bad: str):
        from buckler.hooks import _buckler_command

        with pytest.raises(ValueError, match="line break"):
            _buckler_command(venv_python=Path(bad))

    def test_merge_writes_command_roundtrip_via_shlex(self, tmp_path: Path):
        """hooks.json command field round-trips argv[0] through POSIX shlex (Git Bash posture)."""
        hooks_json = tmp_path / "hooks.json"
        interp = Path("/home/joe smith/.local/share/buckler/.venv/bin/python")
        from buckler.hooks import merge

        merge(hooks_path=hooks_json, venv_python=interp)
        data = json.loads(hooks_json.read_text())
        cmd = next(h["command"] for h in data["hooks"] if h["name"] == "buckler:pre-shell-exec")
        argv = shlex.split(cmd, posix=True)
        assert argv[0] == str(interp)
        assert argv[1:] == ["-m", "buckler", "--driver", "cursor"]


class TestHooksMainInProcess:
    def test_hooks_main_merge(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        from buckler.hooks import main

        with mock.patch(
            "sys.argv",
            [
                "buckler.hooks",
                "merge",
                "--hooks-json",
                str(hooks_json),
                "--venv-python",
                sys.executable,
            ],
        ):
            main()
        data = json.loads(hooks_json.read_text())
        assert any(h["name"].startswith("buckler:") for h in data["hooks"])

    def test_hooks_main_strip(self, tmp_path: Path):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(
            json.dumps(
                {
                    "hooks": [
                        {
                            "name": "buckler:pre-shell-exec",
                            "event": "beforeShellExecution",
                            "command": "x",
                        }
                    ]
                }
            )
        )
        from buckler.hooks import main

        with mock.patch("sys.argv", ["buckler.hooks", "strip", "--hooks-json", str(hooks_json)]):
            main()
        assert not any(
            h["name"].startswith("buckler:") for h in json.loads(hooks_json.read_text())["hooks"]
        )

    def test_hooks_main_status(self, tmp_path: Path, capsys: pytest.CaptureFixture):
        hooks_json = tmp_path / "hooks.json"
        hooks_json.write_text(json.dumps({"hooks": []}))
        from buckler.hooks import main

        with mock.patch("sys.argv", ["buckler.hooks", "status", "--hooks-json", str(hooks_json)]):
            main()
        assert "No Buckler hooks" in capsys.readouterr().out

    def test_hooks_main_no_subcommand(self, capsys: pytest.CaptureFixture):
        from buckler.hooks import main

        with mock.patch("sys.argv", ["buckler.hooks"]):
            main()
        combined = capsys.readouterr()
        assert "merge" in combined.out or "merge" in combined.err

    def test_buckler_command_with_venv_python(self, tmp_path: Path):
        """_buckler_command(venv_python) hits the explicit venv_python branch."""
        from buckler.hooks import _buckler_command

        result = _buckler_command(venv_python=Path(sys.executable))
        assert sys.executable in result
        assert "--driver cursor" in result

    def test_buckler_command_current_dir_with_venv(self, tmp_path: Path):
        """_buckler_command() with current_dir set and .venv/bin/python present."""
        py = tmp_path / ".venv" / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.write_text("#!/usr/bin/env python3")
        py.chmod(0o755)
        with mock.patch("buckler.hooks.paths.current_dir", return_value=tmp_path):
            from buckler.hooks import _buckler_command

            result = _buckler_command()
        assert str(py) in result

    def test_buckler_command_current_dir_windows_venv(self, tmp_path: Path):
        """_buckler_command() uses .venv/Scripts/python.exe when that layout exists."""
        py = tmp_path / ".venv" / "Scripts" / "python.exe"
        py.parent.mkdir(parents=True)
        py.touch()
        with (
            mock.patch("buckler.hooks.paths.current_dir", return_value=tmp_path),
            mock.patch("buckler.paths._is_windows", return_value=True),
        ):
            from buckler.hooks import _buckler_command

            result = _buckler_command()
        assert str(py).replace("\\", "/") in result.replace("\\", "/")

    def test_read_hooks_json_invalid_json(self, tmp_path: Path):
        """_read_hooks_json returns {} when file contains bad JSON."""
        bad = tmp_path / "hooks.json"
        bad.write_text("not json")
        from buckler.hooks import _read_hooks_json

        assert _read_hooks_json(bad) == {}
