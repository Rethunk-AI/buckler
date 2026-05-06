"""CI workflow ↔ pyproject classifier coherence (see specs/active/ci-hygiene)."""

from __future__ import annotations

import re
import tomllib
from pathlib import Path

import yaml

_REPO_ROOT = Path(__file__).resolve().parents[1]
_CI_YML = _REPO_ROOT / ".github" / "workflows" / "ci.yml"
_PYPROJECT = _REPO_ROOT / "pyproject.toml"


def _minor_python_classifiers(pyproject: Path) -> set[str]:
    data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
    classifiers: list[str] = data["project"]["classifiers"]
    minors: set[str] = set()
    pat = re.compile(r"^Programming Language :: Python :: (\d+\.\d+)$")
    for c in classifiers:
        m = pat.match(c)
        if m:
            minors.add(m.group(1))
    return minors


def _test_job_python_versions(ci_yml: Path) -> set[str]:
    doc = yaml.safe_load(ci_yml.read_text(encoding="utf-8"))
    matrix = doc["jobs"]["test"]["strategy"]["matrix"]
    include = matrix["include"]
    return {row["python-version"] for row in include}


def test_ci_python_versions_match_classifier_minors() -> None:
    """Every Programming Language :: Python :: X.Y classifier has a test cell; every matrix Python is declared."""
    minors = _minor_python_classifiers(_PYPROJECT)
    ci_versions = _test_job_python_versions(_CI_YML)
    assert minors == ci_versions, (
        f"classifier minors {sorted(minors)} must equal ci.yml test matrix python-version "
        f"set {sorted(ci_versions)}"
    )


def test_ubuntu_rows_cover_all_classifier_minors() -> None:
    """Full minor-version coverage is exercised on Linux (macOS/Windows carry a single representative cell)."""
    doc = yaml.safe_load(_CI_YML.read_text(encoding="utf-8"))
    include = doc["jobs"]["test"]["strategy"]["matrix"]["include"]
    minors = _minor_python_classifiers(_PYPROJECT)
    ubuntu = {
        row["python-version"]
        for row in include
        if row["os"] == "ubuntu-latest"
    }
    assert minors <= ubuntu, (
        "each classifier minor must appear on at least one ubuntu-latest matrix row "
        f"(have {sorted(ubuntu)}, need {sorted(minors)})"
    )
