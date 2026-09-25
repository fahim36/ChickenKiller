"""The fixed content format, defined once.

A content folder is one version of one Stack's Syllabus:

    <stack-id>/<version>/syllabus.json
    <stack-id>/<version>/questions/<lesson-id>.json   (one Question Bank per Lesson)

The JSON Schema files in `content/schema/` are generated from these models
(`uv run content-schema`), so this module is the single source of truth for the format.
Rules that span several items (unique IDs, references that must resolve, Question Bank sizes)
live in `app.content.check`.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

PermanentId = Annotated[
    str,
    StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", max_length=80),
    Field(
        description=(
            "Permanent ID: lowercase words joined by hyphens. It never changes across "
            "Syllabus versions, so Learner progress can be keyed by it."
        )
    ),
]
Text = Annotated[str, StringConstraints(min_length=1)]
ChoiceId = Annotated[str, StringConstraints(pattern=r"^[a-h]$")]


def _unique(ids: list[str]) -> list[str]:
    duplicates = sorted({i for i in ids if ids.count(i) > 1})
    if duplicates:
        raise ValueError(f"listed more than once: {', '.join(duplicates)}")
    return ids


MaterialRefs = Annotated[
    list[PermanentId],
    AfterValidator(_unique),
    Field(
        json_schema_extra={"uniqueItems": True}, description="IDs of Materials in this Syllabus."
    ),
]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class MaterialType(StrEnum):
    BOOK = "book"
    DOCS = "docs"
    FREE = "free"
    PAID = "paid"
    PAPER = "paper"
    PLATFORM = "platform"
    TOOL = "tool"
    VIDEO = "video"


class Stack(_Model):
    id: PermanentId
    name: Text
    summary: Text
    published: bool = Field(
        default=True,
        description=(
            "Whether Learners can choose this Stack. Set false to import a Stack before it is "
            "ready; a later version can publish or withdraw it."
        ),
    )


class Material(_Model):
    """An external learning reference attached to a Lesson, Milestone or Question."""

    id: PermanentId
    title: Text
    url: Annotated[str, StringConstraints(pattern=r"^https://")]
    type: MaterialType
    subject: Text


class Lesson(_Model):
    id: PermanentId
    title: Text
    topics: Annotated[list[Text], Field(min_length=1)]
    exercise: str | None
    minutes: Annotated[int, Field(ge=1)]
    materials: MaterialRefs


class Milestone(_Model):
    id: PermanentId
    title: Text
    kind: Literal["build", "job-hunt"]
    minutes: Annotated[int, Field(ge=1)]
    materials: MaterialRefs


class Week(_Model):
    id: PermanentId
    number: Annotated[int, Field(ge=1)]
    title: Text
    goal: Text
    deliverable: Text
    interview_checks: list[Text]
    lessons: Annotated[list[Lesson], Field(min_length=1)]
    milestones: list[Milestone]


class Syllabus(_Model):
    """One version of a Stack's Syllabus: its Weeks, Lessons, Milestones and Materials."""

    model_config = ConfigDict(title="Syllabus")

    schema_version: Literal[1]
    version: Annotated[
        str,
        StringConstraints(pattern=r"^v\d{4}-\d{2}-\d{2}$"),
        Field(
            description="Syllabus version, e.g. v2026-09-26. Newer versions sort after older ones."
        ),
    ]
    stack: Stack
    materials: list[Material]
    weeks: Annotated[list[Week], Field(min_length=1)]


class Concept(_Model):
    id: PermanentId
    name: Text


class Choice(_Model):
    id: ChoiceId
    text: Text


class ModelAnswer(_Model):
    summary: Text
    key_points: Annotated[list[Text], Field(min_length=2)]


class MultipleChoiceQuestion(_Model):
    id: PermanentId
    concept: PermanentId
    type: Literal["multiple_choice"]
    prompt: Text
    choices: Annotated[list[Choice], Field(min_length=2)]
    answer: ChoiceId
    explanation: Text
    materials: MaterialRefs


class WrittenQuestion(_Model):
    id: PermanentId
    concept: PermanentId
    type: Literal["written"]
    prompt: Text
    model_answer: ModelAnswer
    explanation: Text
    materials: MaterialRefs


Question = Annotated[MultipleChoiceQuestion | WrittenQuestion, Field(discriminator="type")]


class QuestionBank(_Model):
    """All pre-written Questions for one Lesson. Questions testing the same Concept are siblings."""

    model_config = ConfigDict(title="Question Bank")

    schema_version: Literal[1]
    lesson_id: PermanentId
    concepts: Annotated[list[Concept], Field(min_length=1)]
    questions: Annotated[list[Question], Field(min_length=1)]
