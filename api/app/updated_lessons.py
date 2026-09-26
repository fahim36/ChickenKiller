"""What a new Syllabus version means for one Learner's progress (#13): their Updated Lessons, the
Updated Lessons' new Questions that come in their Review, the Lessons they reached past a removed
Completed Lesson, and the Completed Lessons no longer in the Syllabus.

Nothing is copied or rewritten when a version is imported. Progress is keyed by permanent IDs
(`progress`), so it all carries over as it is, and everything here is worked out when read by
comparing the current version with the ones the Learner completed Lessons in:

- **Changed**: a Completed Lesson is changed when its fingerprint in the current version
  differs from the one in the version it was completed in (`CompletedLesson.syllabus_version`,
  the version current when their Lesson Quiz started). The fingerprint is `content-diff`'s
  rule, the Lesson's own fields and its Week, plus the Questions tagged to it when the version
  was imported (`Lesson.question_ids`). So a Lesson changed and then changed back is not
  Updated, and a Learner who completed a Lesson on the new version already is not behind on
  it. A Lesson whose fingerprint is unknown (imported before fingerprints) is taken as
  unchanged.
- **Updated Lessons** are those changed Completed Lessons, plus Lessons behind the Learner that
  aren't Completed (new ones a version added there): `unlocking.lesson_states` decides from
  `Standing`. An Updated Lesson stays Updated; it never locks anything.
- **New Questions** of an Updated Lesson are the Questions the Question Bank tags to it now
  that the version the Learner completed it in didn't: all of them, for a Lesson that isn't
  Completed. The bank is the Stack's, not a version's (ADR-0004), so this counts a Question
  re-tagged to the Lesson, or added to the bank since the import, and drops one re-tagged
  away. A Retired Question is never owed. Each one waits in the Learner's Review until they
  answer it anywhere, right or wrong (`updated_question_ids`), so a re-tagged Question they
  already answered under its old Lesson isn't owed; a wrong answer makes it a Missed
  Question, which Review asks first anyway.
- **Removed Lessons** drop out of the path. A Completed one stays in the Learner's history
  (`removed_completed_lessons`), and the Learner has still reached the Lesson that followed it
  in the last version that had it (`Standing.reached_ids`), so their Unlocked Lesson is the
  next surviving Lesson after it. When nothing after it survived, the reached Lesson is the one
  after the last surviving Lesson before it. Its Questions stay in the Question Bank: a
  Syllabus Update that removes a Lesson retires them, re-tags them to another Lesson, or tags
  them to none. No Lesson Quiz draws them then, but a Missed Question among them stays in
  Review until it leaves the usual way, unless it is retired.
"""

from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import unlocking
from app.content.versions import version_key
from app.models import Answer, CompletedLesson, Lesson, Question, Stack, Syllabus
from app.unlocking import LessonState


@dataclass(frozen=True)
class Standing:
    """A Learner's progress on a Stack, measured against its current Syllabus."""

    lesson_ids: list[str]
    """The current Syllabus's Lessons, in order; empty without a current Syllabus."""
    completed: dict[str, str]
    """Every Completed Lesson (any version, removed ones too) with the version it was completed
    in."""
    changed_ids: set[str]
    """Completed Lessons of the current Syllabus that changed since they were completed."""
    reached_ids: set[str]
    """Lessons of the current Syllabus the Learner reached past a removed Completed Lesson."""

    def states(self) -> dict[str, LessonState]:
        """Each current Lesson's state for the Learner (`unlocking.lesson_states`)."""
        return unlocking.lesson_states(
            self.lesson_ids,
            self.completed.keys(),
            changed_ids=self.changed_ids,
            reached_ids=self.reached_ids,
        )


@dataclass(frozen=True)
class RemovedLesson:
    """A Completed Lesson that the current Syllabus no longer has."""

    id: str
    title: str
    """Its title in the version it was completed in."""
    completed_at: datetime
    syllabus_version: str
    """The version it was completed in."""


def standing(session: Session, learner_id: int, stack_id: str) -> Standing:
    """The Learner's `Standing` on the Stack's current Syllabus."""
    current = session.execute(
        select(Lesson.id, Lesson.content_hash)
        .join(Stack, Stack.current_syllabus_pk == Lesson.syllabus_pk)
        .where(Stack.id == stack_id)
        .order_by(Lesson.position)
    ).all()
    lesson_ids = [lesson_id for lesson_id, _ in current]
    fingerprint_now = dict(current)
    completed = _completed(session, learner_id, stack_id)

    fingerprint_then = _fingerprints(session, stack_id, completed)
    changed = {
        lesson_id
        for lesson_id in completed.keys() & fingerprint_now.keys()
        if fingerprint_now[lesson_id] is not None
        and fingerprint_then.get(lesson_id) is not None
        and fingerprint_now[lesson_id] != fingerprint_then[lesson_id]
    }
    removed = [lesson_id for lesson_id in completed if lesson_id not in fingerprint_now]
    reached = {
        r for lesson_id in removed if (r := _reached(session, stack_id, lesson_id, lesson_ids))
    }
    return Standing(lesson_ids, completed, changed, reached)


def lesson_states(session: Session, learner_id: int, stack_id: str) -> dict[str, LessonState]:
    """Each Lesson of the current Syllabus with its state for the Learner, in order."""
    return standing(session, learner_id, stack_id).states()


def updated_question_ids(session: Session, learner_id: int, stack_id: str) -> list[str]:
    """The new Questions of the Learner's Updated Lessons that they haven't answered yet, in
    Syllabus order (Lesson, then Question Bank order). They are the Question Bank's Questions
    tagged to each Lesson now, leaving out Retired Questions and the ones tagged to it in the
    version the Learner completed it in. Review asks them after the Missed Questions."""
    learner_standing = standing(session, learner_id, stack_id)
    states = learner_standing.states()
    updated = [
        lesson_id for lesson_id in learner_standing.lesson_ids if states[lesson_id] == "updated"
    ]
    if not updated:
        return []
    tagged: dict[str, list[str]] = {lesson_id: [] for lesson_id in updated}
    for question_id, lesson_id in session.execute(
        select(Question.id, Question.lesson_id)
        .where(
            Question.stack_id == stack_id,
            Question.lesson_id.in_(updated),
            Question.retired_reason.is_(None),
        )
        .order_by(Question.position)
    ):
        assert lesson_id is not None  # tagged to one of `updated`
        tagged[lesson_id].append(question_id)
    bank = [(question_id, lesson_id) for lesson_id, ids in tagged.items() for question_id in ids]
    had = _questions_then(
        session,
        stack_id,
        {
            lesson_id: learner_standing.completed[lesson_id]
            for lesson_id in updated
            if lesson_id in learner_standing.completed
        },
    )
    answered = set(
        session.scalars(
            select(Answer.question_id).where(
                Answer.learner_id == learner_id,
                Answer.stack_id == stack_id,
                Answer.question_id.in_([question_id for question_id, _ in bank]),
            )
        )
    )
    return [
        question_id
        for question_id, lesson_id in bank
        if question_id not in had.get(lesson_id, set()) and question_id not in answered
    ]


def removed_completed_lessons(
    session: Session, learner_id: int, stack_id: str
) -> list[RemovedLesson]:
    """The Learner's Completed Lessons that the current Syllabus no longer has, first completed
    first: their history."""
    current = (
        select(Lesson.id)
        .join(Stack, Stack.current_syllabus_pk == Lesson.syllabus_pk)
        .where(Stack.id == stack_id)
    )
    rows = session.execute(
        select(CompletedLesson, Lesson.title)
        .join(
            Syllabus,
            (Syllabus.stack_id == CompletedLesson.stack_id)
            & (Syllabus.version == CompletedLesson.syllabus_version),
        )
        .join(
            Lesson,
            (Lesson.syllabus_pk == Syllabus.pk) & (Lesson.id == CompletedLesson.lesson_id),
        )
        .where(
            CompletedLesson.learner_id == learner_id,
            CompletedLesson.stack_id == stack_id,
            CompletedLesson.lesson_id.not_in(current),
        )
        .order_by(CompletedLesson.completed_at, CompletedLesson.lesson_id)
    ).all()
    return [
        RemovedLesson(c.lesson_id, title, c.completed_at, c.syllabus_version) for c, title in rows
    ]


def _completed(session: Session, learner_id: int, stack_id: str) -> dict[str, str]:
    rows = session.execute(
        select(CompletedLesson.lesson_id, CompletedLesson.syllabus_version).where(
            CompletedLesson.learner_id == learner_id, CompletedLesson.stack_id == stack_id
        )
    ).all()
    return dict(rows)


def _fingerprints(
    session: Session, stack_id: str, completed: dict[str, str]
) -> dict[str, str | None]:
    """Each Completed Lesson's fingerprint in the version it was completed in."""
    if not completed:
        return {}
    rows = session.execute(
        select(Lesson.id, Syllabus.version, Lesson.content_hash)
        .join(Syllabus, Syllabus.pk == Lesson.syllabus_pk)
        .where(
            Syllabus.stack_id == stack_id,
            Syllabus.version.in_(set(completed.values())),
            Lesson.id.in_(completed.keys()),
        )
    ).all()
    return {
        lesson_id: fingerprint
        for lesson_id, version, fingerprint in rows
        if completed[lesson_id] == version
    }


def _questions_then(
    session: Session, stack_id: str, completed: dict[str, str]
) -> dict[str, set[str]]:
    """The Question IDs tagged to each Lesson in the version it was completed in."""
    if not completed:
        return {}
    rows = session.execute(
        select(Lesson.id, Syllabus.version, Lesson.question_ids)
        .join(Syllabus, Syllabus.pk == Lesson.syllabus_pk)
        .where(
            Syllabus.stack_id == stack_id,
            Syllabus.version.in_(set(completed.values())),
            Lesson.id.in_(completed.keys()),
        )
    ).all()
    return {
        lesson_id: set(question_ids)
        for lesson_id, version, question_ids in rows
        if completed[lesson_id] == version
    }


def _reached(
    session: Session, stack_id: str, removed_id: str, lesson_ids: Collection[str]
) -> str | None:
    """The current Lesson a Learner who completed `removed_id` has reached: the first Lesson
    after it, in the last version that had it, still in the Syllabus; or else the Lesson after
    the last surviving one before it."""
    had_it = session.scalars(
        select(Syllabus.version)
        .join(Lesson, Lesson.syllabus_pk == Syllabus.pk)
        .where(Syllabus.stack_id == stack_id, Lesson.id == removed_id)
    ).all()
    if not had_it:
        return None
    last = max(had_it, key=version_key)
    order = session.scalars(
        select(Lesson.id)
        .join(Syllabus, Syllabus.pk == Lesson.syllabus_pk)
        .where(Syllabus.stack_id == stack_id, Syllabus.version == last)
        .order_by(Lesson.position)
    ).all()
    at = order.index(removed_id)
    surviving = set(lesson_ids)
    after = next((x for x in order[at + 1 :] if x in surviving), None)
    if after is not None:
        return after
    before = next((x for x in reversed(order[:at]) if x in surviving), None)
    if before is None:
        return None
    current = list(lesson_ids)
    i = current.index(before) + 1
    return current[i] if i < len(current) else None
