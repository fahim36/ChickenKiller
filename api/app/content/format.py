"""The fixed content format, defined once.

A content folder is one version of one Stack's Syllabus:

    <stack-id>/<version>/syllabus.json
    <stack-id>/<version>/questions/<lesson-id>.json   (one Question Bank per Lesson)
    <stack-id>/<version>/changelog.json               (what changed since the previous version)

The JSON Schema files in `content/schema/` are generated from these models
(`uv run content-schema`), so this module is the single source of truth for the format.
Rules that span several items (unique IDs, references that must resolve, Question Bank sizes)
live in `app.content.check`.
"""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StringConstraints

from app.content.versions import VERSION_PATTERN, validate_version

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
Version = Annotated[
    str,
    StringConstraints(pattern=VERSION_PATTERN),
    AfterValidator(validate_version),
    Field(
        description=(
            "Syllabus version: the date it was made, e.g. v2026-09-26, plus .1, .2, ... for "
            "more versions on the same day. Versions sort by date, then by that number."
        )
    ),
]
Text = Annotated[str, StringConstraints(min_length=1)]
HttpsUrl = Annotated[str, StringConstraints(pattern=r"^https://")]
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


class ItemKind(StrEnum):
    """The kinds of item that carry a permanent ID, in the order a diff lists them."""

    STACK = "stack"
    WEEK = "week"
    LESSON = "lesson"
    MILESTONE = "milestone"
    MATERIAL = "material"
    CONCEPT = "concept"
    QUESTION = "question"

    @property
    def label(self) -> str:
        return self.value.capitalize()


class Stack(_Model):
    id: PermanentId
    name: Text
    summary: Text


class Material(_Model):
    """An external learning reference attached to a Lesson, Milestone or Question."""

    id: PermanentId
    title: Text
    url: HttpsUrl
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
    version: Version
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


class ChangelogEntry(_Model):
    """One change since the previous version: what, why, and the sources behind it."""

    kind: ItemKind
    id: PermanentId
    change: Literal["added", "changed", "removed"]
    what: Annotated[Text, Field(description="What changed, in a sentence or two.")]
    why: Annotated[Text, Field(description="Why: what moved in the field, or what was wrong.")]
    sources: Annotated[
        list[HttpsUrl],
        Field(min_length=1, description="High-trust primary sources behind the change."),
    ]


class Changelog(_Model):
    """What a Syllabus Update changed since the previous version, and why (`changelog.json`)."""

    model_config = ConfigDict(title="Changelog")

    schema_version: Literal[1]
    version: Version
    previous_version: Annotated[
        Version | None,
        Field(description="The version this one follows; null for a Stack's first version."),
    ]
    summary: Text
    changes: list[ChangelogEntry]
