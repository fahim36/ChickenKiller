"""Load a checked Stack version folder into the database.

Upserts by permanent id, so importing the same folder twice changes nothing. Handling of
Lessons removed or changed between versions comes with the version-import ticket (#13).

    content-import <folder>
"""

import argparse
import sys
from pathlib import Path

from sqlalchemy.orm import Session

from app.content.check import check_folder
from app.content.loader import load_folder
from app.models import Concept, Lesson, Material, Milestone, Question, Stack, Week


def import_folder(session: Session, path: Path) -> Stack:
    folder = load_folder(path)
    s = folder.syllabus

    for m in s["materials"]:
        session.merge(Material(**m))

    stack = session.merge(Stack(version=s["version"], **s["stack"]))
    for week in s["weeks"]:
        session.merge(
            Week(
                id=week["id"],
                stack_id=stack.id,
                number=week["number"],
                title=week["title"],
                goal=week["goal"],
                deliverable=week["deliverable"],
                interview_checks=week["interview_checks"],
            )
        )
        for position, lesson in enumerate(week["lessons"]):
            session.merge(
                Lesson(
                    id=lesson["id"],
                    week_id=week["id"],
                    position=position,
                    title=lesson["title"],
                    topics=lesson["topics"],
                    exercise=lesson["exercise"],
                    minutes=lesson["minutes"],
                    material_ids=lesson["materials"],
                )
            )
        for position, ms in enumerate(week["milestones"]):
            session.merge(
                Milestone(
                    id=ms["id"],
                    week_id=week["id"],
                    position=position,
                    title=ms["title"],
                    kind=ms["kind"],
                    minutes=ms["minutes"],
                    material_ids=ms["materials"],
                )
            )

    for bank in folder.banks.values():
        lesson_id = bank["lesson_id"]
        for c in bank["concepts"]:
            session.merge(Concept(id=c["id"], lesson_id=lesson_id, name=c["name"]))
        for position, q in enumerate(bank["questions"]):
            session.merge(
                Question(
                    id=q["id"],
                    lesson_id=lesson_id,
                    concept_id=q["concept"],
                    position=position,
                    type=q["type"],
                    prompt=q["prompt"],
                    choices=q.get("choices"),
                    answer=q.get("answer"),
                    model_answer=q.get("model_answer"),
                    explanation=q["explanation"],
                    material_ids=q["materials"],
                )
            )

    session.commit()
    return stack


def main(argv: list[str] | None = None) -> int:
    from app.db import Base, SessionLocal, engine

    parser = argparse.ArgumentParser(description="Import a Stack version folder.")
    parser.add_argument("folder", type=Path)
    args = parser.parse_args(argv)

    errors = [p for p in check_folder(args.folder) if p.level == "error"]
    if errors:
        for p in errors:
            print(p)
        print("Import refused: fix the content check errors first.")
        return 1

    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        stack = import_folder(session, args.folder)
        print(f"Imported {stack.name} {stack.version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
