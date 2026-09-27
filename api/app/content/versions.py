"""Syllabus version names, and the order they sort in.

A version is the date it was made, `vYYYY-MM-DD`. A second version made on the same day adds a
number: `v2026-09-26.1`, then `.2`, and so on. Versions sort by date, then by that number, so
`v2026-09-26` < `v2026-09-26.1` < `v2026-09-26.2` < `v2026-09-26.10` < `v2026-09-27`. Compare
versions with `version_key`, never as strings (`".10" < ".2"` as strings).
"""

import re
from collections.abc import Iterable
from datetime import date
from pathlib import Path

VERSION_PATTERN = r"^v\d{4}-\d{2}-\d{2}(\.[1-9]\d*)?$"
_VERSION = re.compile(r"^v(\d{4}-\d{2}-\d{2})(?:\.([1-9]\d*))?$")

VersionKey = tuple[date, int]


def version_key(version: str) -> VersionKey:
    """The sort key of a version name. Raises `ValueError` if it isn't one."""
    match = _VERSION.match(version)
    if match is None:
        raise ValueError(f"not a version name: {version!r} (expected vYYYY-MM-DD or vYYYY-MM-DD.N)")
    try:
        day = date.fromisoformat(match[1])
    except ValueError:
        raise ValueError(f"not a real date: {version!r}") from None
    return day, int(match[2] or 0)


def is_version(name: str) -> bool:
    try:
        version_key(name)
    except ValueError:
        return False
    return True


def validate_version(version: str) -> str:
    version_key(version)
    return version


def next_version(existing: Iterable[str], today: date) -> str:
    """The name for a new version made `today`: after every existing version."""
    keys = [version_key(v) for v in existing]
    if not keys or max(keys) < (today, 0):
        return f"v{today.isoformat()}"
    latest_day, latest_number = max(keys)
    return f"v{latest_day.isoformat()}.{latest_number + 1}"


def stack_versions(stack_dir: Path) -> list[Path]:
    """The version folders of one Stack (`content/<stack-id>/`) that hold a `syllabus.json`,
    oldest first."""
    if not stack_dir.is_dir():
        return []
    folders = [
        p
        for p in stack_dir.iterdir()
        if p.is_dir() and is_version(p.name) and (p / "syllabus.json").is_file()
    ]
    return sorted(folders, key=lambda p: version_key(p.name))


def earlier_versions(folder: Path) -> list[Path]:
    """The versions of the same Stack that sort before `folder` (named for its version), oldest
    first. Empty if `folder`'s name isn't a version."""
    if not is_version(folder.name):
        return []
    key = version_key(folder.name)
    return [p for p in stack_versions(folder.parent) if version_key(p.name) < key]
