"""Load checked Stack content into the database.

    content-import <folder> [<folder> ...]   (a Stack version folder, a Stack folder, or a
                                              content root)

Each Syllabus version is imported once, as its own set of rows:

- Importing a folder that is already imported changes nothing.
- Importing a different Syllabus under a version that already exists is refused: Learner progress
  is only safe if a published version never changes underneath it. Publish a new version instead.
- The newest version of a Stack (see `app.content.versions` for the order) becomes its current
  Syllabus.
- Each Lesson row stores the Questions tagged to it (not retired) and its fingerprint
  (`diff.lesson_fingerprints`), so a Learner's Completed Lesson can be compared with the version
  it was completed in (#13).

Every import also loads the Stack's Question Bank, which is not versioned (ADR-0004). It is only
ever added to, so re-running an import changes nothing:

- a new Concept or Question is added, with its Sources;
- a Question already imported may be retired or re-tagged to another Lesson, and nothing else:
  an edit to anything else is refused, like a changed version (retire it and add a new one);
- a Question missing from the files stays in the database (the content check refuses deleting
  one), and a retirement is never undone;
- each Question's Materials are linked to the Stack's current Syllabus, where they resolve.

Then it loads the Stack's Daily Challenges (`<stack>/challenges/`, #16), by the UTC Day of the
import: an Upcoming Challenge is added, updated, or removed if its file is gone; a released one
(its Day has begun: today or earlier) that differs from what is stored, or is gone, is
refused. Re-running an import changes nothing.

Learner progress needs no carrying over: it is keyed by permanent IDs, never by a version's rows,
so a new version leaves Completed Lessons, Missed Questions, Milestone ticks and answers as
they are. What a new version means for each Learner (Updated Lessons, removed Lessons, their
Unlocked Lesson) is worked out when read, in `app.updated_lessons`.
"""

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.content import format as fmt
from app.content.baseline import question_fields
from app.content.challenges import is_frozen
from app.content.check import load_checked_folder, utc_today, version_folders
from app.content.diff import lesson_fingerprints, lesson_questions
from app.content.loader import Bank, Challenges, ContentError, ContentFolder, Problem
from app.content.versions import version_key
from app.models import (
    Concept,
    DailyChallenge,
    Lesson,
    LessonMaterial,
    Material,
    Milestone,
    MilestoneMaterial,
    Question,
    QuestionMaterial,
    QuestionSource,
    Stack,
    Syllabus,
    Week,
)


@dataclass
class BankChanges:
    """What an import changed in a Stack's Question Bank."""

    added: list[str] = field(default_factory=list)
    retired: list[str] = field(default_factory=list)
    retagged: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.added or self.retired or self.retagged)

    def __str__(self) -> str:
        return (
            f"{len(self.added)} Questions added, {len(self.retired)} retired, "
            f"{len(self.retagged)} re-tagged"
        )


@dataclass
class ChallengeChanges:
    """What an import changed in a Stack's Daily Challenges, by number."""

    added: list[int] = field(default_factory=list)
    updated: list[int] = field(default_factory=list)
    removed: list[int] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.added or self.updated or self.removed)

    def __str__(self) -> str:
        return f"{len(self.added)} added, {len(self.updated)} updated, {len(self.removed)} removed"


@dataclass(frozen=True)
class ImportResult:
    stack_id: str
    version: str
    status: Literal["imported", "unchanged"]
    is_current: bool
    bank: BankChanges = field(default_factory=BankChanges)
    challenges: ChallengeChanges = field(default_factory=ChallengeChanges)

    def __str__(self) -> str:
        line = f"{self.stack_id} {self.version}: {self.status}" + (
            " (current)" if self.is_current else ""
        )
        line += f"; Question Bank: {self.bank}" if self.bank else ""
        return line + (f"; Daily Challenges: {self.challenges}" if self.challenges else "")


def import_folder(session: Session, path: Path, today: date | None = None) -> ImportResult:
    """Check and import one Stack version folder, and its Stack's Question Bank and Daily
    Challenges. `today` (UTC, by default the real one) decides which Challenges are released.
    Flushes; the caller commits."""
    today = today or utc_today()
    return import_content(session, load_checked_folder(path, today), today)


def import_content(
    session: Session, content: ContentFolder, today: date | None = None
) -> ImportResult:
    today = today or utc_today()
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
        bank = import_bank(session, syllabus.stack.id, content.bank)
        challenges = import_challenges(session, syllabus.stack.id, content.challenges, today)
        return ImportResult(
            syllabus.stack.id,
            syllabus.version,
            "unchanged",
            _is_current(session, existing),
            bank,
            challenges,
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
    if current is None or version_key(syllabus.version) > version_key(current.version):
        stack.current_syllabus = row
        stack.name = syllabus.stack.name
        stack.summary = syllabus.stack.summary
        stack.published = syllabus.stack.published
    session.flush()
    bank = import_bank(session, syllabus.stack.id, content.bank)
    challenges = import_challenges(session, syllabus.stack.id, content.challenges, today)
    return ImportResult(
        syllabus.stack.id,
        syllabus.version,
        "imported",
        _is_current(session, row),
        bank,
        challenges,
    )


def import_challenges(
    session: Session, stack_id: str, challenges: Challenges | None, today: date
) -> ChallengeChanges:
    """Load the Stack's Daily Challenges: add new ones, update or remove Upcoming ones. A
    released Challenge (its Day before `today`, UTC) that differs from what is stored, or is
    missing from the files, is refused, changing nothing. Run after `import_bank`, whose
    Questions they name. Flushes."""
    stored = {
        c.number: c
        for c in session.scalars(select(DailyChallenge).where(DailyChallenge.stack_id == stack_id))
    }
    incoming = {c.number: c for c in (challenges.challenges() if challenges else [])}
    changes = ChallengeChanges()
    refused: list[Problem] = []
    where = str(challenges.path) if challenges else stack_id
    for number, old in sorted(stored.items()):
        file = incoming.get(number)
        if file is not None and _challenge_hash(file) == old.content_hash:
            continue
        if is_frozen(old.day, today):
            change = "deleted" if file is None else "changed"
            refused.append(
                Problem(
                    "error",
                    where,
                    f"#{number}",
                    f"{change} since it was imported, but its Day ({old.day}) has begun: a "
                    "released Daily Challenge is frozen",
                )
            )
        elif file is None:
            session.delete(old)
            changes.removed.append(number)
    if refused:
        raise ContentError(refused)
    session.flush()  # a removed Challenge's Day may be taken by another one below

    for number, challenge in sorted(incoming.items()):
        content_hash = _challenge_hash(challenge)
        row = stored.get(number)
        if row is None:
            session.add(
                DailyChallenge(
                    stack_id=stack_id,
                    number=number,
                    day=challenge.date,
                    question_ids=list(challenge.questions),
                    content_hash=content_hash,
                )
            )
            changes.added.append(number)
        elif row.content_hash != content_hash:
            row.day = challenge.date
            row.question_ids = list(challenge.questions)
            row.content_hash = content_hash
            changes.updated.append(number)
    session.flush()
    return changes


def _challenge_hash(challenge: fmt.DailyChallenge) -> str:
    return hashlib.sha256(challenge.model_dump_json().encode()).hexdigest()


def import_bank(session: Session, stack_id: str, bank: Bank) -> BankChanges:
    """Load the Stack's Question Bank (see the module docstring), then link every Question's
    Materials to the current Syllabus. Raises ContentError, changing nothing, if a Question
    already imported was edited or un-retired. Flushes."""
    concepts = {
        c.id: c for c in session.scalars(select(Concept).where(Concept.stack_id == stack_id))
    }
    for _, concept in bank.concepts():
        known = concepts.get(concept.id)
        if known is None:
            concepts[concept.id] = Concept(stack_id=stack_id, id=concept.id, name=concept.name)
            session.add(concepts[concept.id])
        elif known.name != concept.name:
            known.name = concept.name  # a Concept's name is not part of any Question

    imported = {
        q.id: q
        for q in session.scalars(
            select(Question)
            .where(Question.stack_id == stack_id)
            .options(selectinload(Question.material_links))
        )
    }
    changes = BankChanges()
    refused: list[Problem] = []
    for position, (path, question) in enumerate(bank.questions()):
        content_hash = _question_hash(question)
        row = imported.get(question.id)
        if row is None:
            row = _new_question(stack_id, question, concepts[question.concept], content_hash)
            session.add(row)
            imported[question.id] = row
            changes.added.append(question.id)
        elif row.content_hash != content_hash:
            refused.append(
                Problem(
                    "error",
                    str(path),
                    question.id,
                    "already imported with different content: a Question is never edited; "
                    "retire it and add a new one",
                )
            )
            continue
        elif question.retired is None and row.retired:
            refused.append(
                Problem("error", str(path), question.id, "already retired: a retirement is final")
            )
            continue
        else:
            if row.lesson_id != question.lesson:
                row.lesson_id = question.lesson
                changes.retagged.append(question.id)
            if question.retired is not None and not row.retired:
                changes.retired.append(question.id)
        if question.retired is not None:
            row.retired_reason = question.retired.reason
            row.replaced_by = question.retired.replaced_by
            row.retired_on = question.retired.on
        row.position = position
    if refused:
        raise ContentError(refused)
    session.flush()
    _link_materials(session, stack_id, list(imported.values()))
    return changes


def _new_question(
    stack_id: str, question: fmt.Question, concept: Concept, content_hash: str
) -> Question:
    row = Question(
        stack_id=stack_id,
        id=question.id,
        lesson_id=question.lesson,
        concept=concept,
        type=question.type,
        prompt=question.prompt,
        explanation=question.explanation,
        material_ids=list(question.materials),
        content_hash=content_hash,
        material_links=[],
        sources=[
            QuestionSource(
                position=i,
                url=s.url,
                title=s.title,
                publisher=s.publisher,
                accessed=s.accessed,
                claim=s.claim,
            )
            for i, s in enumerate(question.sources)
        ],
    )
    if isinstance(question, fmt.MultipleChoiceQuestion):
        row.choices = [choice.model_dump() for choice in question.choices]
        row.answer = question.answer
    else:
        row.model_answer = question.model_answer.model_dump()
    return row


def _link_materials(session: Session, stack_id: str, questions: list[Question]) -> None:
    """Link each Question's Materials to their rows in the Stack's current Syllabus. A link
    already right is left alone, so an unchanged import writes nothing."""
    stack = session.get_one(Stack, stack_id)
    materials = {
        m.id: m
        for m in session.scalars(
            select(Material).where(Material.syllabus_pk == stack.current_syllabus_pk)
        )
    }
    for question in questions:
        wanted = [
            (materials[ref].pk, i)
            for i, ref in enumerate(question.material_ids)
            if ref in materials
        ]
        if [(link.material_pk, link.position) for link in question.material_links] == wanted:
            continue
        question.material_links = []
        session.flush()
        question.material_links = [
            QuestionMaterial(material=materials[ref], position=i)
            for i, ref in enumerate(question.material_ids)
            if ref in materials
        ]
    session.flush()


def _question_hash(question: fmt.Question) -> str:
    """Everything about a Question that never changes: all but its Lesson tag and retirement."""
    fields, _ = question_fields(question.model_dump(mode="json"))
    return hashlib.sha256(json.dumps(fields, sort_keys=True).encode()).hexdigest()


def _is_current(session: Session, row: Syllabus) -> bool:
    stack = session.get(Stack, row.stack_id)
    return stack is not None and stack.current_syllabus_pk == row.pk


def _content_hash(content: ContentFolder) -> str:
    # Fields left at their default are skipped, so adding an optional field to the format
    # doesn't change the hash of a version that is already imported. The Question Bank isn't
    # part of a version.
    return hashlib.sha256(
        content.syllabus.model_dump_json(exclude_defaults=True).encode()
    ).hexdigest()


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

    fingerprints = lesson_fingerprints(content)
    tagged = lesson_questions(content)
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
                content_hash=fingerprints[lesson.id],
                question_ids=tagged[lesson.id],
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


def main(argv: list[str] | None = None) -> int:
    from app.db import SessionLocal

    parser = argparse.ArgumentParser(description="Import Stack content into the database.")
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
