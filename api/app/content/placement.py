"""Reviewed, versioned whole-Week placement coverage; no learner evidence."""

import hashlib
import json
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.content.format import PermanentId, Text
from app.content.loader import ContentFolder


class PlacementLesson(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    lesson: PermanentId
    essential_concepts: list[PermanentId] = Field(min_length=1, max_length=10)
    count: Literal[5, 10]
    questions: list[PermanentId] = Field(min_length=5)
    rationale: Text

    @model_validator(mode="after")
    def unique_ids(self) -> "PlacementLesson":
        for values in (self.essential_concepts, self.questions):
            if len(values) != len(set(values)):
                raise ValueError("placement references must be unique")
        if len(self.essential_concepts) > self.count or len(self.questions) < self.count:
            raise ValueError("placement count cannot meet essential coverage")
        return self


class PlacementPlan(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    stack: PermanentId
    week: PermanentId
    version: int = Field(ge=1)
    reviewed_by: Text
    lessons: list[PlacementLesson] = Field(min_length=1)


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def read_plans(content: ContentFolder) -> list[PlacementPlan]:
    """Plans accompany their Syllabus version; old folders without them remain valid."""
    plans = [
        PlacementPlan.model_validate_json(path.read_text(encoding="utf-8"))
        for path in sorted((content.path / "placement").glob("*.json"))
    ]
    if len({p.week for p in plans}) != len(plans):
        raise ValueError("duplicate placement Week")
    weeks = {w.id: w for w in content.syllabus.weeks}
    questions = {q.id: q for q in content.bank.live_questions()}
    for plan in plans:
        if plan.stack != content.syllabus.stack.id or plan.week not in weeks:
            raise ValueError("placement Stack and Week must resolve")
        lessons = weeks[plan.week].lessons
        if {p.lesson for p in plan.lessons} != {lesson.id for lesson in lessons} or len(
            plan.lessons
        ) != len(lessons):
            raise ValueError("placement must cover every Lesson exactly once")
        drawn: set[str] = set()
        for blueprint in plan.lessons:
            candidates = [questions.get(qid) for qid in blueprint.questions]
            if any(
                q is None
                or q.lesson != blueprint.lesson
                or q.type not in {"multiple_choice", "multiple_select"}
                for q in candidates
            ):
                raise ValueError("placement Questions must be active MC/MS in the teaching Lesson")
            if drawn.intersection(blueprint.questions):
                raise ValueError("a placement Question cannot count for two Lessons")
            drawn.update(blueprint.questions)
            covered = {q.concept for q in candidates if q is not None}
            if not set(blueprint.essential_concepts).issubset(covered):
                raise ValueError("placement essential Concepts lack mapped Questions")
    return plans


def teaching_revision(content: ContentFolder, plan: PlacementPlan) -> str:
    week = next(w for w in content.syllabus.weeks if w.id == plan.week)
    return digest(
        {
            "week": week.id,
            "teaching": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "topics": lesson.topics,
                    "exercise": lesson.exercise,
                    "materials": [
                        {
                            "id": material.id,
                            "title": material.title,
                            "subject": material.subject,
                            "type": material.type,
                        }
                        for material_id in lesson.materials
                        for material in content.syllabus.materials
                        if material.id == material_id
                    ],
                }
                for lesson in week.lessons
            ],
            "coverage": sorted(
                [
                    {
                        "lesson": item.lesson,
                        "essential": sorted(item.essential_concepts),
                        "count": item.count,
                    }
                    for item in plan.lessons
                ],
                key=lambda item: str(item["lesson"]),
            ),
        }
    )
