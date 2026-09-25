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
internal and never sent to the browser.
"""

from datetime import datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
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


class Invitation(Base):
    """The Admin's invitation for one email address. Pending until that person first signs in."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(Text, unique=True, comment="Lower-cased.")
    invited_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
