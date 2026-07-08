"""Guards against shipping wheels with missing bundled files.

Every non-Python file inside the package (SQL migrations, problem data,
company profiles, stylesheets) must be covered by a package-data glob in
pyproject.toml, or pip-installed copies of the app break at runtime.
"""

from __future__ import annotations

import fnmatch
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
PACKAGE_ROOT = REPO_ROOT / "codepractice"

BUNDLED_SUFFIXES = {".sql", ".json", ".tcss"}


def _package_data_globs() -> list[str]:
    with open(REPO_ROOT / "pyproject.toml", "rb") as f:
        config = tomllib.load(f)
    return config["tool"]["setuptools"]["package-data"]["codepractice"]


def _bundled_files() -> list[str]:
    return [
        str(p.relative_to(PACKAGE_ROOT))
        for p in PACKAGE_ROOT.rglob("*")
        if p.is_file() and p.suffix in BUNDLED_SUFFIXES and "__pycache__" not in p.parts
    ]


class TestPackageData:
    def test_every_bundled_file_is_covered_by_a_glob(self):
        globs = _package_data_globs()
        missing = [
            rel for rel in _bundled_files()
            if not any(fnmatch.fnmatch(rel, g) for g in globs)
        ]
        assert not missing, (
            f"Files not covered by [tool.setuptools.package-data]: {missing}. "
            "They will be missing from installed wheels."
        )

    def test_expected_bundles_exist(self):
        files = _bundled_files()
        assert any(f.startswith("db/migrations/") for f in files), "migrations missing"
        assert any(f.startswith("data/problems/") for f in files), "problem data missing"
        assert "data/companies.json" in files

    def test_migrations_present_and_sequential(self):
        migrations = sorted((PACKAGE_ROOT / "db" / "migrations").glob("*.sql"))
        assert len(migrations) >= 12
        numbers = [int(m.name.split("_")[0]) for m in migrations]
        assert numbers == list(range(1, len(migrations) + 1)), "migration numbering gap"
