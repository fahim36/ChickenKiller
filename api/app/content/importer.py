"""Load a checked Stack version folder into the database.

    content-import <folder> [<folder> ...]   (a Stack version folder, or a content root)

Each Stack version is imported once, as its own set of rows:

- Importing a folder that is already imported changes nothing.
- Importing different content under a version that already exists is refused: Learner progress
  is only safe if a published version never changes underneath it. Publish a new version instead.
- The newest version of a Stack (versions sort by date) becomes its current Syllabus.

Carrying Learner progress over to a new version is the version-import ticket (#13).
"""

import argparse
import hashlib
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content import format as fmt
from app.content.check import load_checked_folder, version_folders
from app.content.loader import ContentError, ContentFolder, Problem
from app.models import (
    Concept,
    Lesson,
    LessonMaterial,
    Material,
    Milestone,
    MilestoneMaterial,
    Question,
    QuestionMaterial,
    Stack,
    Syllabus,
    Week,
)


@dataclass(frozen=True)
class ImportResult:
    stack_id: str
    version: str
    status: Literal["imported", "unchanged"]
    is_current: bool

    def __str__(self) -> str:
        return f"{self.stack_id} {self.version}: {self.status}" + (
            " (current)" if self.is_current else ""
        )


def import_folder(session: Session, path: Path) -> ImportResult:
    """Check and import one Stack version folder. Flushes; the caller commits."""
    return import_content(session, load_checked_folder(path))


def import_content(session: Session, content: ContentFolder) -> ImportResult:
    syllabus = content.syllabus
    content_hash = _content_hash(content)

    existing = session.scalar(
        select(Syllabus).where(
            Syllabus.stack_id == syllabus.stack.id, Syllabus.version == syllabus.version
        )
    )
    if existing is not None:
        if existing.content_hash != content_hash:
            raise ContentError(
                [
                    Problem(
                        "error",
                        str(content.path),
                        f"{syllabus.stack.id} {syllabus.version}",
                        "already imported with different content; "
                        "publish the change as a new version instead",
                    )
                ]
            )
        return ImportResult(
            syllabus.stack.id, syllabus.version, "unchanged", _is_current(session, existing)
        )

    stack = session.get(Stack, syllabus.stack.id)
    if stack is None:
        stack = Stack(
            id=syllabus.stack.id, name=syllabus.stack.name, summary=syllabus.stack.summary
        )
        session.add(stack)

    row = Syllabus(
        stack=stack,
        version=syllabus.version,
        schema_version=syllabus.schema_version,
        content_hash=content_hash,
    )
    session.add(row)
    session.flush()
    _add_content(session, row.pk, content)

    current = stack.current_syllabus
    if current is None or syllabus.version > current.version:
        stack.current_syllabus = row
        stack.name = syllabus.stack.name
        stack.summary = syllabus.stack.summary
    session.flush()
    return ImportResult(syllabus.stack.id, syllabus.version, "imported", _is_current(session, row))


def _is_current(session: Session, row: Syllabus) -> bool:
    stack = session.get(Stack, row.stack_id)
    return stack is not None and stack.current_syllabus_pk == row.pk


def _content_hash(content: ContentFolder) -> str:
    digest = hashlib.sha256(content.syllabus.model_dump_json().encode())
    for bank in sorted(content.banks.values(), key=lambda b: b.lesson_id):
        digest.update(bank.model_dump_json().encode())
    return digest.hexdigest()


def _add_content(session: Session, syllabus_pk: int, content: ContentFolder) -> None:
    syllabus = content.syllabus
    materials = {
        m.id: Material(
            syllabus_pk=syllabus_pk,
            id=m.id,
            title=m.title,
            url=m.url,
            type=m.type.value,
            subject=m.subject,
        )
        for m in syllabus.materials
    }
    session.add_all(materials.values())

    lessons: dict[str, Lesson] = {}
    for week_position, week in enumerate(syllabus.weeks):
        week_row = Week(
            syllabus_pk=syllabus_pk,
            id=week.id,
            position=week_position,
            number=week.number,
            title=week.title,
            goal=week.goal,
            deliverable=week.deliverable,
            interview_checks=list(week.interview_checks),
        )
        for lesson in week.lessons:
            lessons[lesson.id] = Lesson(
                syllabus_pk=syllabus_pk,
                week=week_row,
                id=lesson.id,
                position=len(lessons),
                title=lesson.title,
                topics=list(lesson.topics),
                exercise=lesson.exercise,
                minutes=lesson.minutes,
                material_links=[
                    LessonMaterial(material=materials[ref], position=i)
                    for i, ref in enumerate(lesson.materials)
                ],
            )
        session.add_all(
            Milestone(
                syllabus_pk=syllabus_pk,
                week=week_row,
                id=milestone.id,
                position=position,
                title=milestone.title,
                kind=milestone.kind,
                minutes=milestone.minutes,
                material_links=[
                    MilestoneMaterial(material=materials[ref], position=i)
                    for i, ref in enumerate(milestone.materials)
                ],
            )
            for position, milestone in enumerate(week.milestones)
        )
    session.add_all(lessons.values())

    for bank in content.banks.values():
        _add_question_bank(session, syllabus_pk, lessons[bank.lesson_id], bank, materials)


def _add_question_bank(
    session: Session,
    syllabus_pk: int,
    lesson: Lesson,
    bank: fmt.QuestionBank,
    materials: dict[str, Material],
) -> None:
    concepts = {
        c.id: Concept(syllabus_pk=syllabus_pk, lesson=lesson, id=c.id, name=c.name)
        for c in bank.concepts
    }
    session.add_all(concepts.values())
    for position, question in enumerate(bank.questions):
        row = Question(
            syllabus_pk=syllabus_pk,
            lesson=lesson,
            concept=concepts[question.concept],
            id=question.id,
            position=position,
            type=question.type,
            prompt=question.prompt,
            explanation=question.explanation,
            material_links=[
                QuestionMaterial(material=materials[ref], position=i)
                for i, ref in enumerate(question.materials)
            ],
        )
        if isinstance(question, fmt.MultipleChoiceQuestion):
            row.choices = [choice.model_dump() for choice in question.choices]
            row.answer = question.answer
        else:
            row.model_answer = question.model_answer.model_dump()
        session.add(row)


def main(argv: list[str] | None = None) -> int:
    from app.db import SessionLocal

    parser = argparse.ArgumentParser(description="Import Stack version folders into the database.")
    parser.add_argument("folders", nargs="+", type=Path)
    args = parser.parse_args(argv)

    folders = version_folders(args.folders)
    if not folders:
        print("no Stack version folders found")
        return 1

    with SessionLocal() as session:
        for folder in folders:
            try:
                result = import_folder(session, folder)
            except ContentError as e:
                session.rollback()
                for p in e.problems:
                    print(p)
                print(f"{folder}: import refused")
                return 1
            session.commit()
            print(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
