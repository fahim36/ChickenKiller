"""Database tables for imported Syllabus content.

Two kinds of identifier, kept apart on purpose:

- `id` (text) is always the **permanent ID** from the content files. It never changes across
  Syllabus versions, so anything about a Learner (progress, answers, Milestone ticks) stores
  permanent IDs such as `lesson_id` / `question_id`, never a `pk`.
- `pk` (integer) is a surrogate key for one row of one Syllabus version. Every imported version
  gets its own rows, so the same permanent ID appears once per version. `pk`s are internal and
  are never sent to the browser.

A Stack has many Syllabus versions and points at its current one.

People (`Learner`, `Invitation`) are not content: they have a plain integer `id`, which is also
internal and never sent to the browser. A Lesson Quiz attempt is named by the browser when it
submits, so its `id` is a random UUID instead.
"""

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
    text,
    true,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base

ID = String(80)
_SYLLABUS_FK = "syllabuses.pk"


def _syllabus_pk() -> Mapped[int]:
    return mapped_column(ForeignKey(_SYLLABUS_FK, ondelete="CASCADE"), index=True)


class Stack(Base):
    __tablename__ = "stacks"

    id: Mapped[str] = mapped_column(ID, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    summary: Mapped[str] = mapped_column(Text)
    published: Mapped[bool] = mapped_column(
        Boolean,
        server_default=true(),
        comment="Set by the current Syllabus. Only published Stacks can be chosen.",
    )
    current_syllabus_pk: Mapped[int | None] = mapped_column(
        ForeignKey(_SYLLABUS_FK, use_alter=True, ondelete="SET NULL")
    )

    current_syllabus: Mapped["Syllabus | None"] = relationship(
        foreign_keys=[current_syllabus_pk], post_update=True
    )


class Syllabus(Base):
    """One imported version of a Stack's Syllabus."""

    __tablename__ = "syllabuses"
    __table_args__ = (UniqueConstraint("stack_id", "version"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ForeignKey("stacks.id", ondelete="CASCADE"))
    version: Mapped[str] = mapped_column(String(20))
    schema_version: Mapped[int] = mapped_column(Integer)
    content_hash: Mapped[str] = mapped_column(String(64))
    imported_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    stack: Mapped[Stack] = relationship(foreign_keys=[stack_id])
    weeks: Mapped[list["Week"]] = relationship(order_by="Week.position", viewonly=True)


class Material(Base):
    __tablename__ = "materials"
    __table_args__ = (UniqueConstraint("syllabus_pk", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    syllabus_pk: Mapped[int] = _syllabus_pk()
    id: Mapped[str] = mapped_column(ID)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(Text)


class Week(Base):
    __tablename__ = "weeks"
    __table_args__ = (UniqueConstraint("syllabus_pk", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    syllabus_pk: Mapped[int] = _syllabus_pk()
    id: Mapped[str] = mapped_column(ID)
    position: Mapped[int] = mapped_column(Integer)
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    deliverable: Mapped[str] = mapped_column(Text)
    interview_checks: Mapped[list[str]] = mapped_column(JSONB)

    lessons: Mapped[list["Lesson"]] = relationship(
        order_by="Lesson.position", back_populates="week"
    )
    milestones: Mapped[list["Milestone"]] = relationship(
        order_by="Milestone.position", back_populates="week"
    )


class LessonMaterial(Base):
    __tablename__ = "lesson_materials"

    lesson_pk: Mapped[int] = mapped_column(
        ForeignKey("lessons.pk", ondelete="CASCADE"), primary_key=True
    )
    material_pk: Mapped[int] = mapped_column(
        ForeignKey("materials.pk", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer)

    material: Mapped[Material] = relationship(lazy="joined")


class Lesson(Base):
    __tablename__ = "lessons"
    __table_args__ = (UniqueConstraint("syllabus_pk", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    syllabus_pk: Mapped[int] = _syllabus_pk()
    week_pk: Mapped[int] = mapped_column(ForeignKey("weeks.pk", ondelete="CASCADE"))
    id: Mapped[str] = mapped_column(ID)
    position: Mapped[int] = mapped_column(
        Integer, comment="Order of the Lesson within the whole Syllabus, from 0."
    )
    title: Mapped[str] = mapped_column(Text)
    topics: Mapped[list[str]] = mapped_column(JSONB)
    exercise: Mapped[str | None] = mapped_column(Text)
    minutes: Mapped[int] = mapped_column(Integer)

    week: Mapped[Week] = relationship(back_populates="lessons")
    material_links: Mapped[list[LessonMaterial]] = relationship(
        order_by=LessonMaterial.position, cascade="all, delete-orphan"
    )

    @property
    def materials(self) -> list[Material]:
        return [link.material for link in self.material_links]


class MilestoneMaterial(Base):
    __tablename__ = "milestone_materials"

    milestone_pk: Mapped[int] = mapped_column(
        ForeignKey("milestones.pk", ondelete="CASCADE"), primary_key=True
    )
    material_pk: Mapped[int] = mapped_column(
        ForeignKey("materials.pk", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer)

    material: Mapped[Material] = relationship(lazy="joined")


class Milestone(Base):
    __tablename__ = "milestones"
    __table_args__ = (UniqueConstraint("syllabus_pk", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    syllabus_pk: Mapped[int] = _syllabus_pk()
    week_pk: Mapped[int] = mapped_column(ForeignKey("weeks.pk", ondelete="CASCADE"))
    id: Mapped[str] = mapped_column(ID)
    position: Mapped[int] = mapped_column(Integer, comment="Order within its Week, from 0.")
    title: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    minutes: Mapped[int] = mapped_column(Integer)

    week: Mapped[Week] = relationship(back_populates="milestones")
    material_links: Mapped[list[MilestoneMaterial]] = relationship(
        order_by=MilestoneMaterial.position, cascade="all, delete-orphan"
    )


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("syllabus_pk", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    syllabus_pk: Mapped[int] = _syllabus_pk()
    lesson_pk: Mapped[int] = mapped_column(ForeignKey("lessons.pk", ondelete="CASCADE"))
    id: Mapped[str] = mapped_column(ID)
    name: Mapped[str] = mapped_column(Text)

    lesson: Mapped[Lesson] = relationship()


class QuestionMaterial(Base):
    __tablename__ = "question_materials"

    question_pk: Mapped[int] = mapped_column(
        ForeignKey("questions.pk", ondelete="CASCADE"), primary_key=True
    )
    material_pk: Mapped[int] = mapped_column(
        ForeignKey("materials.pk", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer)

    material: Mapped[Material] = relationship(lazy="joined")


class Question(Base):
    """A Question of a Lesson's Question Bank, including its correct answer.

    `answer` / `model_answer` must never be sent to the browser before the Learner answers.
    """

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("syllabus_pk", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    syllabus_pk: Mapped[int] = _syllabus_pk()
    lesson_pk: Mapped[int] = mapped_column(ForeignKey("lessons.pk", ondelete="CASCADE"))
    concept_pk: Mapped[int] = mapped_column(ForeignKey("concepts.pk", ondelete="CASCADE"))
    id: Mapped[str] = mapped_column(ID)
    position: Mapped[int] = mapped_column(Integer, comment="Order within its Question Bank.")
    type: Mapped[str] = mapped_column(String(20), comment="multiple_choice or written")
    prompt: Mapped[str] = mapped_column(Text)
    choices: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    answer: Mapped[str | None] = mapped_column(String(1))
    model_answer: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    explanation: Mapped[str] = mapped_column(Text)

    lesson: Mapped[Lesson] = relationship()
    concept: Mapped[Concept] = relationship()
    material_links: Mapped[list[QuestionMaterial]] = relationship(
        order_by=QuestionMaterial.position, cascade="all, delete-orphan"
    )

    @property
    def materials(self) -> list[Material]:
        return [link.material for link in self.material_links]


# --- People ----------------------------------------------------------------------------------


class Learner(Base):
    """A person with an account, created on their first sign-in (app/learners.py).

    Sign-in itself is Clerk's (ADR-0002); `clerk_user_id` is the token's `sub`. Emails are stored
    lower-cased.
    """

    __tablename__ = "learners"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    clerk_user_id: Mapped[str] = mapped_column(String(64), unique=True)
    email: Mapped[str] = mapped_column(Text, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    # Both are set during onboarding (#4) and empty until then.
    active_stack_id: Mapped[str | None] = mapped_column(
        ForeignKey("stacks.id", ondelete="SET NULL")
    )
    time_zone: Mapped[str | None] = mapped_column(String(64), comment="An IANA name.")


class LearnerStack(Base):
    """One Learner on one Stack: created the first time that Stack becomes their Active Stack.

    A Learner's progress on a Stack hangs off this record, keyed by `(learner_id, stack_id)` and
    the content's permanent IDs. Switching the Active Stack never deletes it, so switching back
    resumes where the Learner left off.
    """

    __tablename__ = "learner_stacks"

    learner_id: Mapped[int] = mapped_column(
        ForeignKey("learners.id", ondelete="CASCADE"), primary_key=True
    )
    stack_id: Mapped[str] = mapped_column(
        ForeignKey("stacks.id", ondelete="CASCADE"), primary_key=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    stack: Mapped[Stack] = relationship(lazy="joined")


class Invitation(Base):
    """The Admin's invitation for one email address. Pending until that person first signs in."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, comment="Lower-cased.")
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


# --- Progress --------------------------------------------------------------------------------
# A Learner's progress on one Stack hangs off their `learner_stacks` record, and names content by
# permanent ID only, so it survives a new Syllabus version (#13). It is read and written through
# app/progress.py.


def _of_learner_stack() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["learner_id", "stack_id"],
        ["learner_stacks.learner_id", "learner_stacks.stack_id"],
        ondelete="CASCADE",
    )


class CompletedLesson(Base):
    """A Completed Lesson: its Lesson Quiz met the Pass Mark and every Retake was correct."""

    __tablename__ = "completed_lessons"
    __table_args__ = (_of_learner_stack(),)

    learner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ID, primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ID, primary_key=True, comment="Permanent ID.")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MilestoneTick(Base):
    """A Milestone the Learner ticked off. Unticking deletes the row. Ticks never affect
    unlocking."""

    __tablename__ = "milestone_ticks"
    __table_args__ = (_of_learner_stack(),)

    learner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ID, primary_key=True)
    milestone_id: Mapped[str] = mapped_column(ID, primary_key=True, comment="Permanent ID.")
    ticked_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class LessonQuizAttempt(Base):
    """One Lesson Quiz a Learner started: the Questions drawn for it, from the Syllabus version
    that was current when it started. Read and written through app/quizzes.py.

    - `id` is random, because the browser names the attempt when it submits.
    - The attempt is pinned to `syllabus_version`: its Questions are read and marked from that
      version even after a newer one is imported (#13).
    - A Learner has at most one unsubmitted attempt per Lesson, so starting again resumes it.
    """

    __tablename__ = "lesson_quiz_attempts"
    __table_args__ = (
        _of_learner_stack(),
        Index(
            "uq_lesson_quiz_attempts_one_open",
            "learner_id",
            "stack_id",
            "lesson_id",
            unique=True,
            postgresql_where=text("submitted_at IS NULL"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    learner_id: Mapped[int] = mapped_column(Integer)
    stack_id: Mapped[str] = mapped_column(ID)
    lesson_id: Mapped[str] = mapped_column(ID, comment="Permanent ID.")
    syllabus_version: Mapped[str] = mapped_column(
        String(20), comment="The version the Questions come from, pinned at start."
    )
    question_ids: Mapped[list[str]] = mapped_column(
        JSONB, comment="Permanent IDs of the Questions drawn, in the order they are asked."
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    correct_count: Mapped[int | None] = mapped_column(Integer, comment="Set on submission.")
    passed: Mapped[bool | None] = mapped_column(Boolean, comment="Set on submission.")


class Retake(Base):
    """The Retakes of one Missed Question of a passed Lesson Quiz attempt (#8). Read and written
    through app/retakes.py.

    Each Retake asks a sibling Question (same Concept, never the missed one) from the attempt's
    pinned Syllabus version. `asked_question_ids` lists the siblings asked so far, in order; the
    last is the one waiting for an answer. Each answer is an `Answer` with `context='retake'`.
    `done_at` is set by the first correct one; once every Retake of the attempt is done the
    Lesson is a Completed Lesson.
    """

    __tablename__ = "retakes"
    __table_args__ = (
        _of_learner_stack(),
        UniqueConstraint("lesson_quiz_attempt_id", "missed_question_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    learner_id: Mapped[int] = mapped_column(Integer)
    stack_id: Mapped[str] = mapped_column(ID)
    lesson_quiz_attempt_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("lesson_quiz_attempts.id", ondelete="CASCADE"), index=True
    )
    missed_question_id: Mapped[str] = mapped_column(ID, comment="Permanent ID.")
    asked_question_ids: Mapped[list[str]] = mapped_column(
        JSONB, comment="Permanent IDs of the siblings asked, in order; the last is waiting."
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    done_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When a Retake was answered correctly."
    )


class ReviewDay(Base):
    """One calendar day, in the Learner's time zone, on which the Learner used the app while
    studying this Stack. Written by the first request of that day (app/reviews.py), which is
    also when Round 1 of the day's Daily Review opens, if one is owed.

    A day with no Review Round owed nothing (the Learner had no Completed Lesson yet), so it
    neither extends nor breaks the Streak (#11).
    """

    __tablename__ = "review_days"
    __table_args__ = (_of_learner_stack(),)

    learner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ID, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True, comment="In the Learner's zone.")
    first_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewRound(Base):
    """One Review Round of a Learner's Daily Review on a Stack. Read and written through
    app/reviews.py; the timing and picking rules are app/review.py.

    - `number` is 1 to 3 within its day. Round 1 opens on the day's first use; Rounds 2 and 3
      four hours after the previous one is finished, with `opened_at` that time even when the
      row is written later (on the next request).
    - The round is pinned to `syllabus_version`, the version current when it opened: its
      Questions are read and marked from that version, like a Lesson Quiz attempt (#13).
    - Each Question is answered once, one at a time, as an `Answer` with
      `context='review_round'`. `finished_at` is set when the last one is answered.
    - Whether it is optional or pending follows from `opened_at` and the clock
      (`review.round_state`); it is never stored.
    """

    __tablename__ = "review_rounds"
    __table_args__ = (
        ForeignKeyConstraint(
            ["learner_id", "stack_id", "day"],
            ["review_days.learner_id", "review_days.stack_id", "review_days.day"],
            ondelete="CASCADE",
        ),
        UniqueConstraint("learner_id", "stack_id", "day", "number"),
        CheckConstraint("number BETWEEN 1 AND 3", name="number_in_day"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    learner_id: Mapped[int] = mapped_column(Integer)
    stack_id: Mapped[str] = mapped_column(ID)
    day: Mapped[date] = mapped_column(Date, comment="The review day, in the Learner's zone.")
    number: Mapped[int] = mapped_column(Integer, comment="1 to 3 within the day.")
    syllabus_version: Mapped[str] = mapped_column(
        String(20), comment="The version the Questions come from, pinned at opening."
    )
    question_ids: Mapped[list[str]] = mapped_column(
        JSONB, comment="Permanent IDs of the Questions, in the order they are asked."
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When the last Question was answered."
    )


class Answer(Base):
    """One answer a Learner gave to one Question, wherever it was asked.

    Missed Questions (`correct` is false) and the Daily Review are read from here (#8, #9), so a
    Question is named by permanent ID plus the Syllabus version it was asked from.
    `quizzes.missed_questions` is the reading of it the Daily Review uses.

    - `context` says where it was asked. Each context has its own nullable link column and a
      check constraint requires the matching one: `lesson_quiz` uses `lesson_quiz_attempt_id`,
      `retake` uses `retake_id`, `review_round` uses `review_round_id` (one answer per Question
      per round).
    - `response` is the choice ID or the written answer; null means left unanswered.
    - `correct` is null while a written answer waits for grading. (#7 grades before recording,
      and records nothing if grading fails, so a Lesson Quiz answer always has it.)
    - `feedback` is the grader's one line on a graded written answer (app/marking.py).
    """

    __tablename__ = "answers"
    __table_args__ = (
        _of_learner_stack(),
        UniqueConstraint("lesson_quiz_attempt_id", "question_id"),
        CheckConstraint(
            "context <> 'lesson_quiz' OR lesson_quiz_attempt_id IS NOT NULL",
            name="context_link",
        ),
        CheckConstraint("context <> 'retake' OR retake_id IS NOT NULL", name="retake_link"),
        CheckConstraint(
            "context <> 'review_round' OR review_round_id IS NOT NULL", name="review_round_link"
        ),
        UniqueConstraint("review_round_id", "question_id"),
        Index("ix_answers_learner_question", "learner_id", "stack_id", "question_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    learner_id: Mapped[int] = mapped_column(Integer)
    stack_id: Mapped[str] = mapped_column(ID)
    question_id: Mapped[str] = mapped_column(ID, comment="Permanent ID.")
    syllabus_version: Mapped[str] = mapped_column(String(20))
    context: Mapped[str] = mapped_column(String(20), comment="lesson_quiz, retake or review_round")
    lesson_quiz_attempt_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("lesson_quiz_attempts.id", ondelete="CASCADE")
    )
    retake_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("retakes.id", ondelete="CASCADE"), index=True
    )
    review_round_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("review_rounds.id", ondelete="CASCADE")
    )
    response: Mapped[str | None] = mapped_column(Text)
    correct: Mapped[bool | None] = mapped_column(Boolean)
    feedback: Mapped[str | None] = mapped_column(Text, comment="The grader's line (written).")
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
