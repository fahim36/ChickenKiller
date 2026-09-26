"""Database tables for imported Syllabus content.

Two kinds of identifier, kept apart on purpose:

- `id` (text) is always the **permanent ID** from the content files. It never changes across
  Syllabus versions, so anything about a Learner (progress, answers, Milestone ticks) stores
  permanent IDs such as `lesson_id` / `question_id`, never a `pk`.
- `pk` (integer) is a surrogate key for one row. Every imported Syllabus version gets its own
  rows of Weeks, Lessons, Milestones and Materials, so the same permanent ID appears once per
  version. `pk`s are internal and are never sent to the browser.

A Stack has many Syllabus versions and points at its current one. Its Question Bank (Concepts,
Questions and their Sources) is not versioned: one row per permanent ID, for good (ADR-0004).

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
    content_hash: Mapped[str | None] = mapped_column(
        String(64),
        comment=(
            "The Lesson's content as content-diff compares it (fields, Week), plus question_ids. "
            "Equal across versions means unchanged."
        ),
    )
    question_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        server_default=text("'[]'::jsonb"),
        comment="The Questions tagged to it, not retired, when this version was imported.",
    )

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


# --- The Question Bank -----------------------------------------------------------------------
# One per Stack, never versioned (ADR-0004): its rows are keyed by (stack id, permanent id) and
# only ever added to. An import may retire a Question or re-tag it to another Lesson; nothing
# else about a Question changes once imported (app/content/importer.py).


class Concept(Base):
    __tablename__ = "concepts"
    __table_args__ = (UniqueConstraint("stack_id", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ForeignKey("stacks.id", ondelete="CASCADE"))
    id: Mapped[str] = mapped_column(ID)
    name: Mapped[str] = mapped_column(Text)


class QuestionMaterial(Base):
    """A Question's Material, linked to that Material's row in the Stack's current Syllabus: a
    Question's Materials resolve against the newest version, so each import links them again."""

    __tablename__ = "question_materials"

    question_pk: Mapped[int] = mapped_column(
        ForeignKey("questions.pk", ondelete="CASCADE"), primary_key=True
    )
    material_pk: Mapped[int] = mapped_column(
        ForeignKey("materials.pk", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer)

    material: Mapped[Material] = relationship(lazy="joined")


class QuestionSource(Base):
    """Where a Question's content came from. Every Question has at least one."""

    __tablename__ = "question_sources"

    question_pk: Mapped[int] = mapped_column(
        ForeignKey("questions.pk", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    url: Mapped[str] = mapped_column(Text)
    title: Mapped[str] = mapped_column(Text)
    publisher: Mapped[str] = mapped_column(Text)
    accessed: Mapped[date] = mapped_column(Date, comment="UTC.")
    claim: Mapped[str] = mapped_column(Text, comment="The claim the Question relies on.")


class Question(Base):
    """A Question of a Stack's Question Bank, including its correct answer.

    `answer` / `model_answer` must never be sent to the browser before the Learner answers.
    A Retired Question (`retired_reason` set) stays, but is never drawn for anything new.
    """

    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("stack_id", "id"),)

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ForeignKey("stacks.id", ondelete="CASCADE"))
    id: Mapped[str] = mapped_column(ID)
    lesson_id: Mapped[str | None] = mapped_column(
        ID, comment="Permanent ID of the Lesson it is tagged to, if any. May change (re-tag)."
    )
    concept_pk: Mapped[int] = mapped_column(ForeignKey("concepts.pk", ondelete="CASCADE"))
    position: Mapped[int] = mapped_column(Integer, comment="Order within the Question Bank.")
    type: Mapped[str] = mapped_column(String(20), comment="multiple_choice or written")
    prompt: Mapped[str] = mapped_column(Text)
    choices: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    answer: Mapped[str | None] = mapped_column(String(1))
    model_answer: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    explanation: Mapped[str] = mapped_column(Text)
    material_ids: Mapped[list[str]] = mapped_column(
        JSONB, comment="Permanent IDs of its Materials, in order."
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), comment="Everything that never changes: the import refuses an edit."
    )
    retired_reason: Mapped[str | None] = mapped_column(Text, comment="Set once it is retired.")
    replaced_by: Mapped[str | None] = mapped_column(ID, comment="Permanent ID of its replacement.")
    retired_on: Mapped[date | None] = mapped_column(Date)

    concept: Mapped[Concept] = relationship()
    material_links: Mapped[list[QuestionMaterial]] = relationship(
        order_by=QuestionMaterial.position, cascade="all, delete-orphan"
    )
    sources: Mapped[list[QuestionSource]] = relationship(
        order_by=QuestionSource.position, cascade="all, delete-orphan"
    )

    @property
    def retired(self) -> bool:
        return self.retired_reason is not None

    @property
    def materials(self) -> list[Material]:
        return [link.material for link in self.material_links]


# --- Daily Challenges ------------------------------------------------------------------------


class DailyChallenge(Base):
    """One Daily Challenge of a Stack: three Questions of its Question Bank, for one UTC Day.

    Imported ahead as an Upcoming Challenge, it may change at import until its Day; once its Day
    has passed it is released and frozen (app/content/importer.py). Until its Day an Upcoming
    Challenge's Questions are never sent to a Learner.
    """

    __tablename__ = "daily_challenges"
    __table_args__ = (UniqueConstraint("stack_id", "number"), UniqueConstraint("stack_id", "day"))

    pk: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ForeignKey("stacks.id", ondelete="CASCADE"))
    number: Mapped[int] = mapped_column(Integer, comment="Numbered from the Stack's launch.")
    day: Mapped[date] = mapped_column(Date, comment="Its UTC Day.")
    question_ids: Mapped[list[str]] = mapped_column(
        JSONB, comment="Permanent IDs of its three Questions, in order."
    )
    content_hash: Mapped[str] = mapped_column(
        String(64), comment="The import refuses a change once its Day has passed."
    )


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


class LearnerStack(Base):
    """One Learner on one Stack: created the first time the Learner activates that Stack
    (app/onboarding.py).

    A Learner's progress on a Stack hangs off this record, keyed by `(learner_id, stack_id)` and
    the content's permanent IDs. `active` says whether it is one of their Active Stacks now.
    Deactivating the Stack only clears it, so reactivating resumes where the Learner left off.
    """

    __tablename__ = "learner_stacks"

    learner_id: Mapped[int] = mapped_column(
        ForeignKey("learners.id", ondelete="CASCADE"), primary_key=True
    )
    stack_id: Mapped[str] = mapped_column(
        ForeignKey("stacks.id", ondelete="CASCADE"), primary_key=True
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    active: Mapped[bool] = mapped_column(
        Boolean, server_default=true(), comment="Whether it is one of the Learner's Active Stacks."
    )

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
    """A Completed Lesson: its Lesson Quiz met the Pass Mark and every Retake was correct.

    `syllabus_version` is the version the Learner's Lesson Quiz started in. A later version
    that changed the Lesson makes it an Updated Lesson, whose new Questions are the ones tagged
    to it that the version it was completed in didn't list (app/updated_lessons.py, #13).
    """

    __tablename__ = "completed_lessons"
    __table_args__ = (_of_learner_stack(),)

    learner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ID, primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ID, primary_key=True, comment="Permanent ID.")
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    syllabus_version: Mapped[str] = mapped_column(
        String(20), comment="The version the Lesson was completed in."
    )


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
    """One Lesson Quiz a Learner started: the Questions drawn for it from the Question Bank.
    Read and written through app/quizzes.py.

    - `id` is random, because the browser names the attempt when it submits.
    - `syllabus_version` is the Syllabus version current when it started, which a pass completes
      the Lesson in (#13). Its Questions need no pinning: a Question never changes.
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
        String(20), comment="The Syllabus version current at start; a pass completes it there."
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

    Each Retake asks a sibling Question (same Concept, never the missed one, never a Retired
    Question). `asked_question_ids` lists the siblings asked so far, in order; the
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
    """One Day (in UTC, ADR-0005) on which the Learner used the app while studying this Stack.
    Written by the first request of that day (app/reviews.py), which is also when Round 1 of the
    day's Daily Review opens, if one is owed.

    A day with no Review Round owed nothing (the Learner had no Completed Lesson yet), so it
    neither extends nor breaks the Streak (#11).
    """

    __tablename__ = "review_days"
    __table_args__ = (_of_learner_stack(),)

    learner_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stack_id: Mapped[str] = mapped_column(ID, primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True, comment="A UTC Day.")
    first_used_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ReviewRound(Base):
    """One Review Round of a Learner's Daily Review on a Stack. Read and written through
    app/reviews.py; the timing and picking rules are app/review.py.

    - `number` is 1 to 3 within its day. Round 1 opens on the day's first use; Rounds 2 and 3
      four hours after the previous one is finished, with `opened_at` that time even when the
      row is written later (on the next request).
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
    day: Mapped[date] = mapped_column(Date, comment="The review Day, in UTC.")
    number: Mapped[int] = mapped_column(Integer, comment="1 to 3 within the day.")
    question_ids: Mapped[list[str]] = mapped_column(
        JSONB, comment="Permanent IDs of the Questions, in the order they are asked."
    )
    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When the last Question was answered."
    )


class Answer(Base):
    """One answer a Learner gave to one Question, wherever it was asked.

    Missed Questions (`correct` is false) and the Daily Review are read from here (#8, #9). A
    Question is named by its permanent ID alone: it never changes.
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
