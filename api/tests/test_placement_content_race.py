"""Placement refreshes content loaded before the import/selection locking boundary."""

import json
import shutil

from sqlalchemy import Engine, delete, select
from sqlalchemy.orm import Session

from app import placements
from app.content.importer import import_folder
from app.models import PlacementCoverage, Stack
from tests.conftest import ContentFactory, changelog_entry, make_changelog
from tests.test_placement_coverage import fixture_plan


def test_cached_stack_cannot_select_preimport_plan(
    engine: Engine, make_content: ContentFactory
) -> None:
    old_path, _ = fixture_plan(make_content)
    new_path = old_path.parent / "v2026-01-02.1"
    shutil.copytree(old_path, new_path)
    file = new_path / "syllabus.json"
    document = json.loads(file.read_text(encoding="utf-8"))
    document["version"] = new_path.name
    document["weeks"][0]["lessons"][0]["topics"] = ["Changed teaching"]
    file.write_text(json.dumps(document), encoding="utf-8")
    (new_path / "changelog.json").write_text(
        json.dumps(
            make_changelog(
                new_path.name, old_path.name, changelog_entry("lesson", "w01-l01", "changed")
            )
        ),
        encoding="utf-8",
    )
    try:
        with Session(engine) as seed:
            import_folder(seed, old_path)
            seed.commit()
        with Session(engine, expire_on_commit=False) as cached:
            stack = cached.get_one(Stack, "mini-stack")
            old_pk = stack.current_syllabus_pk
            cached.commit()  # leave dependency-loaded identity cached across importer commit
            with Session(engine) as importer:
                import_folder(importer, new_path)
                importer.commit()
            placements.lock(cached, 12345, "mini-stack")
            current = placements.current_plan(cached, "mini-stack", "w01")
            assert current is not None and current.syllabus_pk != old_pk
            previous = cached.scalar(
                select(PlacementCoverage).where(PlacementCoverage.syllabus_pk == old_pk)
            )
            assert previous is not None and current.teaching_revision != previous.teaching_revision
    finally:
        with Session(engine) as cleanup:
            cleanup.execute(delete(Stack).where(Stack.id == "mini-stack"))
            cleanup.commit()
