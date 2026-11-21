# /// script
# requires-python = ">=3.12"
# dependencies = [
#   "httpx==0.28.1",
#   "packaging==26.3",
# ]
# ///
"""
Point the hook at the latest release of unref on PyPI, if it is newer than the one this repository names.

Run with `uv run --no-project mirror.py`. The version is set in `pyproject.toml` and the README. In a workflow, it is
also written to the `version` output, once it changes.
"""

import os
import re
import tomllib
from pathlib import Path

import httpx
from packaging.requirements import Requirement
from packaging.version import Version

_ROOT = Path(__file__).parent
# Each file, with the pattern of the version in it. The part before the version is kept.
_FILES = {
    "pyproject.toml": r'("unref==)[0-9.]+',
    "README.md": r"(rev: v)[0-9.]+",
}


def _latest_version() -> Version:
    """The latest version of unref on PyPI, without pre-releases and yanked releases."""
    response = httpx.get("https://pypi.org/pypi/unref/json", timeout=30)
    response.raise_for_status()
    versions = [
        Version(version)
        for version, files in response.json()["releases"].items()
        if files and not all(file["yanked"] for file in files)
    ]
    return max(version for version in versions if not version.is_prerelease)


def _current_version() -> Version:
    """The version of unref that `pyproject.toml` names."""
    with (_ROOT / "pyproject.toml").open("rb") as stream:
        dependencies = tomllib.load(stream)["project"]["dependencies"]
    requirement = next(Requirement(dependency) for dependency in dependencies if dependency.startswith("unref"))
    (specifier,) = requirement.specifier
    assert specifier.operator == "==", f"The version of unref should be exact, not `{requirement}`."
    return Version(specifier.version)


def main() -> None:
    current, latest = _current_version(), _latest_version()
    if latest <= current:
        print(f"unref {current} is the latest release.")
        return
    for path, pattern in _FILES.items():
        file = _ROOT / path
        text, count = re.subn(pattern, rf"\g<1>{latest}", file.read_text())
        assert count, f"No version of unref found in {path}."
        file.write_text(text)
    print(f"Set the version of unref to {latest}.")
    if output := os.environ.get("GITHUB_OUTPUT"):
        with Path(output).open("a") as stream:
            stream.write(f"version={latest}\n")


if __name__ == "__main__":
    main()
