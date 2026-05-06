"""Tests for buckler.pack_loader — YAML pack loading and config resolution."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest


class TestPackLoaderValidation:
    """pack_loader silently skips invalid rules — verify each validation path."""

    def _load_with_pack(self, tmp_path: Path, yaml_text: str):
        (tmp_path / "p.yaml").write_text(yaml_text)
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "rd"),
        ):
            from buckler.pack_loader import load_packs

            return load_packs()

    def test_missing_id_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - trigger: pre_shell_exec\n    action: deny\n",
        )
        assert not any(r.get("id") == "" for r in rules)

    def test_missing_trigger_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path, "pack: t\nversion: '1'\nrules:\n  - id: r1\n    action: deny\n"
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_trigger_value_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: bad_trigger\n    action: deny\n",
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_missing_action_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path, "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n"
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_action_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n    action: explode\n",
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_invalid_tier_skipped(self, tmp_path: Path):
        rules = self._load_with_pack(
            tmp_path,
            "pack: t\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n    action: deny\n    tier: extreme\n",
        )
        assert not any(r["id"] == "r1" for r in rules)

    def test_malformed_yaml_skipped(self, tmp_path: Path):
        """A pack file with invalid YAML is skipped; the rest of load_packs() succeeds."""
        self._load_with_pack(tmp_path, "pack: test\n  bad: [unclosed")  # must not raise

    def test_user_rules_loaded(self, tmp_path: Path):
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "my.yaml").write_text(
            "pack: my\nversion: '1'\nrules:\n"
            "  - id: allow-all\n    trigger: pre_shell_exec\n    action: allow\n    priority: 5\n"
        )
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "empty"),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d),
        ):
            from buckler.pack_loader import load_packs

            assert any(r["id"] == "allow-all" for r in load_packs())

    def test_user_rules_bad_yaml_skipped(self, tmp_path: Path):
        """Malformed YAML in rules.d is skipped without aborting load."""
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "bad.yaml").write_text("pack: bad\n  invalid: [unclosed")
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "empty"),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d),
        ):
            from buckler.pack_loader import load_packs

            load_packs()  # must not raise


class TestLoadConfig:
    def test_defaults_when_file_missing(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path / "nonexistent"))
        from buckler.pack_loader import load_config

        assert load_config()["core"]["tier"] == "baseline"

    def test_reads_tier_from_toml(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_text('[core]\ntier = "strict"\n')
        from buckler.pack_loader import load_config

        assert load_config()["core"]["tier"] == "strict"

    def test_falls_back_to_defaults_on_parse_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
    ):
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_bytes(b"\xff\xfe bad toml \x00")
        from buckler.pack_loader import load_config

        assert load_config()["core"]["tier"] == "baseline"


class TestPackLoaderRemainingBranches:
    def test_invalid_tier_value(self, tmp_path: Path):
        """A rule with an invalid tier value is skipped with a warning."""
        (tmp_path / "bad_tier.yaml").write_text(
            "pack: test\nversion: '1'\nrules:\n"
            "  - id: r1\n    trigger: pre_shell_exec\n    action: deny\n    tier: extreme\n"
        )
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "nope"),
        ):
            from buckler.pack_loader import load_packs

            assert not any(r["id"] == "r1" for r in load_packs())

    def test_missing_action(self, tmp_path: Path):
        """A rule missing 'action' is skipped."""
        (tmp_path / "no_action.yaml").write_text(
            "pack: test\nversion: '1'\nrules:\n  - id: r1\n    trigger: pre_shell_exec\n"
        )
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=tmp_path / "nope"),
        ):
            from buckler.pack_loader import load_packs

            assert not any(r["id"] == "r1" for r in load_packs())

    def test_user_rules_dir_yaml_error(self, tmp_path: Path):
        """A malformed YAML in user rules.d is skipped gracefully."""
        rules_d = tmp_path / "rules.d"
        rules_d.mkdir()
        (rules_d / "bad.yaml").write_text("pack: bad\n  invalid: [unclosed")
        with (
            mock.patch("buckler.pack_loader.paths.packs_dir", return_value=tmp_path / "no_packs"),
            mock.patch("buckler.pack_loader.paths.user_rules_dir", return_value=rules_d),
        ):
            from buckler.pack_loader import load_packs

            load_packs()  # must not raise

    def test_load_config_parse_error(self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
        """load_config() falls back to defaults when config.toml has a parse error."""
        monkeypatch.setenv("BUCKLER_CONFIG_HOME", str(tmp_path))
        (tmp_path / "config.toml").write_bytes(b"\xff\xfe bad toml content \x00")
        from buckler.pack_loader import load_config

        assert load_config()["core"]["tier"] == "baseline"


class TestValidatePackFiles:
    def test_validate_ok_empty_pack_tree(self, tmp_path: Path):
        packs = tmp_path / "packs"
        rules = tmp_path / "rules.d"
        packs.mkdir()
        rules.mkdir()
        from buckler.pack_loader import validate_pack_files

        assert validate_pack_files(packs_dir=packs, user_rules_dir=rules) == []

    def test_validate_reports_unknown_trigger(self, tmp_path: Path):
        packs = tmp_path / "packs"
        packs.mkdir()
        (packs / "bad.yaml").write_text(
            "pack: x\nversion: '1'\nrules:\n  - id: r1\n    trigger: nada\n    action: deny\n"
        )
        rules = tmp_path / "rules.d"
        rules.mkdir()
        from buckler.pack_loader import validate_pack_files

        errs = validate_pack_files(packs_dir=packs, user_rules_dir=rules)
        assert errs
        assert any("unknown trigger" in e for e in errs)

    def test_validate_rules_must_be_list(self, tmp_path: Path):
        packs = tmp_path / "packs"
        packs.mkdir()
        (packs / "bad.yaml").write_text("pack: x\nversion: '1'\nrules: notalist\n")
        rules = tmp_path / "rules.d"
        rules.mkdir()
        from buckler.pack_loader import validate_pack_files

        errs = validate_pack_files(packs_dir=packs, user_rules_dir=rules)
        assert any("rules' must be a list" in e for e in errs)
