"""Tables for imported Syllabus content. Ids are the permanent ids from the content files."""

from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Stack(Base):
    __tablename__ = "stacks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    version: Mapped[str] = mapped_column(String(20))

    weeks: Mapped[list["Week"]] = relationship(order_by="Week.number", cascade="all, delete-orphan")


class Material(Base):
    __tablename__ = "materials"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(Text)
    url: Mapped[str] = mapped_column(Text)
    type: Mapped[str] = mapped_column(String(20))
    subject: Mapped[str] = mapped_column(String(100))


class Week(Base):
    __tablename__ = "weeks"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    stack_id: Mapped[str] = mapped_column(ForeignKey("stacks.id"))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    goal: Mapped[str] = mapped_column(Text)
    deliverable: Mapped[str] = mapped_column(Text)
    interview_checks: Mapped[list[str]] = mapped_column(JSON)

    lessons: Mapped[list["Lesson"]] = relationship(
        order_by="Lesson.position", back_populates="week", cascade="all, delete-orphan"
    )
    milestones: Mapped[list["Milestone"]] = relationship(
        order_by="Milestone.position", cascade="all, delete-orphan"
    )


class Lesson(Base):
    __tablename__ = "lessons"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    week_id: Mapped[str] = mapped_column(ForeignKey("weeks.id"))
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    topics: Mapped[list[str]] = mapped_column(JSON)
    exercise: Mapped[str | None] = mapped_column(Text, nullable=True)
    minutes: Mapped[int] = mapped_column(Integer)
    material_ids: Mapped[list[str]] = mapped_column(JSON)

    week: Mapped[Week] = relationship(back_populates="lessons")


class Milestone(Base):
    __tablename__ = "milestones"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    week_id: Mapped[str] = mapped_column(ForeignKey("weeks.id"))
    position: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20))
    minutes: Mapped[int] = mapped_column(Integer)
    material_ids: Mapped[list[str]] = mapped_column(JSON)


class Concept(Base):
    __tablename__ = "concepts"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"))
    name: Mapped[str] = mapped_column(Text)


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    lesson_id: Mapped[str] = mapped_column(ForeignKey("lessons.id"))
    concept_id: Mapped[str] = mapped_column(ForeignKey("concepts.id"))
    position: Mapped[int] = mapped_column(Integer)
    type: Mapped[str] = mapped_column(String(20))
    prompt: Mapped[str] = mapped_column(Text)
    choices: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    answer: Mapped[str | None] = mapped_column(String(1), nullable=True)
    model_answer: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    material_ids: Mapped[list[str]] = mapped_column(JSON)
