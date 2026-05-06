"""Pack discovery and loading.

Packs are YAML files defining policy rules. Buckler loads them in this order
(later rules with equal priority override earlier ones):

  1. Builtin packs from paths.packs_dir() (sorted by filename)
  2. User rules from paths.user_rules_dir()/*.yaml (sorted alphabetically)
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from buckler import paths

log = logging.getLogger(__name__)

_VALID_TRIGGERS = frozenset(
    ["pre_shell_tool", "pre_shell_exec", "post_tool_success", "post_tool_failure"]
)
_VALID_ACTIONS = frozenset(["allow", "deny", "ask", "nudge"])
_VALID_TIERS = frozenset(["baseline", "strict"])


class PackLoadError(Exception):
    pass


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        with path.open() as f:
            return yaml.safe_load(f) or {}
    except (yaml.YAMLError, OSError) as e:
        raise PackLoadError(f"Failed to load pack {path}: {e}") from e


def _normalize_rule(rule: dict[str, Any], pack_id: str, source: str) -> dict[str, Any]:
    """Validate and normalize a single rule dict."""
    if "id" not in rule:
        raise PackLoadError(f"Rule in pack '{pack_id}' ({source}) missing 'id'")
    if "trigger" not in rule:
        raise PackLoadError(f"Rule '{rule['id']}' in pack '{pack_id}' missing 'trigger'")
    if "action" not in rule:
        raise PackLoadError(f"Rule '{rule['id']}' in pack '{pack_id}' missing 'action'")

    triggers = rule["trigger"] if isinstance(rule["trigger"], list) else [rule["trigger"]]
    for t in triggers:
        if t not in _VALID_TRIGGERS:
            raise PackLoadError(f"Rule '{rule['id']}': unknown trigger '{t}'")

    action = rule["action"]
    if action not in _VALID_ACTIONS:
        raise PackLoadError(f"Rule '{rule['id']}': unknown action '{action}'")

    tier = rule.get("tier", "baseline")
    if tier not in _VALID_TIERS:
        raise PackLoadError(f"Rule '{rule['id']}': unknown tier '{tier}'")

    return {
        "id": rule["id"],
        "pack": pack_id,
        "source": source,
        "trigger": triggers,
        "match": rule.get("match", {}),
        "action": action,
        "priority": int(rule.get("priority", 50)),
        "tier": tier,
        "user_message": rule.get("user_message"),
        "agent_message": rule.get("agent_message"),
        "additional_context": rule.get("additional_context"),
        "enabled": rule.get("enabled", True),
    }


def _load_pack_file(path: Path) -> list[dict[str, Any]]:
    data = _load_yaml(path)
    pack_id = data.get("pack", path.stem)
    rules_raw = data.get("rules", [])
    rules = []
    for r in rules_raw:
        try:
            normalized = _normalize_rule(r, pack_id, str(path))
            if normalized["enabled"]:
                rules.append(normalized)
        except PackLoadError as e:
            log.warning("Skipping rule: %s", e)
    return rules


def load_packs(tier: str = "baseline") -> list[dict[str, Any]]:
    """Load all enabled rules from builtin packs + user rules.d, filtered by tier."""
    all_rules: list[dict[str, Any]] = []

    builtin_dir = paths.packs_dir()
    if builtin_dir.exists():
        for pack_file in sorted(builtin_dir.glob("*.yaml")):
            try:
                all_rules.extend(_load_pack_file(pack_file))
            except PackLoadError as e:
                log.warning("Pack load error: %s", e)

    user_dir = paths.user_rules_dir()
    if user_dir.exists():
        for pack_file in sorted(user_dir.glob("*.yaml")):
            try:
                all_rules.extend(_load_pack_file(pack_file))
            except PackLoadError as e:
                log.warning("User rule load error: %s", e)

    if tier == "baseline":
        all_rules = [r for r in all_rules if r["tier"] == "baseline"]

    all_rules.sort(key=lambda r: (-r["priority"], r["action"]))
    return all_rules


def load_config() -> dict[str, Any]:
    """Load operator config from config.toml, returning defaults if missing."""
    cfg_file = paths.config_file()
    defaults: dict[str, Any] = {"core": {"tier": "baseline", "audit_log": False}}
    if not cfg_file.exists():
        return defaults
    try:
        import tomllib  # type: ignore[import]
    except ImportError:
        try:
            import tomllib  # type: ignore[no-redef]
        except ImportError:
            log.warning("tomllib not available; using default config")
            return defaults
    try:
        with cfg_file.open("rb") as f:
            data = tomllib.load(f)
        merged = {**defaults}
        merged["core"].update(data.get("core", {}))
        return merged
    except Exception as e:
        log.warning("Failed to load config %s: %s", cfg_file, e)
        return defaults
