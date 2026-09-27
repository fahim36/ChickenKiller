"""Version names: `vYYYY-MM-DD`, plus `.N` for a second (third, ...) version on the same day."""

from pathlib import Path
from typing import Any

import pytest

from app.content.check import check_folder, version_folders
from tests.conftest import ContentFactory


@pytest.mark.parametrize("version", ["v2026-01-01.1", "v2026-01-01.2", "v2026-01-01.10"])
def test_a_version_may_carry_a_same_day_number(make_content: ContentFactory, version: str) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = version

    assert [p for p in check_folder(make_content(edit)) if p.level == "error"] == []


def test_version_folders_under_a_content_root_come_oldest_first(tmp_path: Path) -> None:
    for name in ["v2026-01-01.10", "v2026-01-02", "v2026-01-01.2", "v2026-01-01"]:
        (tmp_path / "mini-stack" / name).mkdir(parents=True)
        (tmp_path / "mini-stack" / name / "syllabus.json").write_text("{}", encoding="utf-8")

    assert [p.name for p in version_folders([tmp_path])] == [
        "v2026-01-01",
        "v2026-01-01.2",
        "v2026-01-01.10",
        "v2026-01-02",
    ]


@pytest.mark.parametrize(
    "version", ["v2026-01-01.0", "v2026-01-01.01", "v2026-1-01", "v2026-01-01-2", "v2026-13-01"]
)
def test_a_malformed_version_is_refused(make_content: ContentFactory, version: str) -> None:
    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["version"] = version

    [problem] = [p for p in check_folder(make_content(edit)) if p.level == "error"]
    assert problem.item == "version"
