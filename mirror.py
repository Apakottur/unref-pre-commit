"""
Mirror each release of unref on PyPI that is newer than the one this repository names.

Each release is a commit that sets the version in `pyproject.toml`, `uv.lock` and the README, tagged with the version.
Run with `uv run mirror.py`, and push the commits and the tags.
"""

import re
import time
import tomllib
from pathlib import Path

import httpx
import shpyx
from packaging.requirements import Requirement
from packaging.version import Version

_ROOT = Path(__file__).parent
# Each file, with the pattern of the version in it. The part before the version is kept.
_FILES = {
    "pyproject.toml": r'("unref==)[0-9.]+',
    "README.md": r'(rev: v|rev = "v)[0-9.]+',
}
# PyPI's JSON API can name a release before the simple index that `uv lock` reads, which is cached for up to 10
# minutes. `uv lock` is retried for longer than that.
_LOCK_ATTEMPTS = 48
_LOCK_DELAY_SECONDS = 15


def _released_versions() -> list[Version]:
    """The versions of unref on PyPI, oldest first, without pre-releases and yanked releases."""
    response = httpx.get("https://pypi.org/pypi/unref/json", timeout=30)
    response.raise_for_status()
    versions = [
        Version(version)
        for version, files in response.json()["releases"].items()
        if files and not all(file["yanked"] for file in files)
    ]
    return sorted(version for version in versions if not version.is_prerelease)


def _current_version() -> Version:
    """The version of unref that `pyproject.toml` names."""
    with (_ROOT / "pyproject.toml").open("rb") as stream:
        dependencies = tomllib.load(stream)["project"]["dependencies"]
    requirement = next(Requirement(dependency) for dependency in dependencies if dependency.startswith("unref"))
    (specifier,) = requirement.specifier
    assert specifier.operator == "==", f"The version of unref should be exact, not `{requirement}`."
    return Version(specifier.version)


def _set_version(version: Version) -> None:
    for path, pattern in _FILES.items():
        file = _ROOT / path
        text, count = re.subn(pattern, rf"\g<1>{version}", file.read_text())
        assert count, f"No version of unref found in {path}."
        file.write_text(text)


def _lock(version: Version) -> None:
    for attempt in range(1, _LOCK_ATTEMPTS + 1):
        try:
            # Without the refresh, uv could reuse its own cache of the index from the attempt before.
            shpyx.run(["uv", "lock", "--refresh-package", "unref"], exec_dir=_ROOT)
            return
        except shpyx.ShpyxVerificationError as error:
            if attempt == _LOCK_ATTEMPTS:
                raise
            print(
                f"Attempt {attempt} of {_LOCK_ATTEMPTS} to lock unref {version} failed:\n{error.result.stderr}",
                flush=True,
            )
            time.sleep(_LOCK_DELAY_SECONDS)


def main() -> None:
    current = _current_version()
    for version in _released_versions():
        if version <= current:
            continue
        _set_version(version)
        _lock(version)
        shpyx.run(["git", "add", *_FILES, "uv.lock"], exec_dir=_ROOT)
        shpyx.run(["git", "commit", "--message", f"Mirror unref {version}"], exec_dir=_ROOT)
        shpyx.run(["git", "tag", f"v{version}"], exec_dir=_ROOT)
        print(f"Mirrored unref {version}.")


if __name__ == "__main__":
    main()
