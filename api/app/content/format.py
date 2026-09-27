"""The fixed content format, defined once.

A Stack's folder holds its Syllabus versions and its one Question Bank:

    <stack-id>/<version>/syllabus.json        one Syllabus version
    <stack-id>/<version>/changelog.json       what changed since the previous version
    <stack-id>/question-bank/<name>.json      the Question Bank, in as many files as is readable
    <stack-id>/challenges/launch.json         the Day the Stack's Daily Challenges start
    <stack-id>/challenges/<number>.json       one Daily Challenge, such as 001.json

The JSON Schema files in `content/schema/` are generated from these models
(`uv run content-schema`), so this module is the single source of truth for the format.
Rules that span several items (unique IDs, references that must resolve, Question Bank sizes)
live in `app.content.check`.
"""

from datetime import date
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
    """The single idea a Question tests. Concepts belong to the Stack, like the Question Bank."""

    id: PermanentId
    name: Text


class Choice(_Model):
    id: ChoiceId
    text: Text


class ModelAnswer(_Model):
    summary: Text
    key_points: Annotated[list[Text], Field(min_length=2)]


class Source(_Model):
    """Where a Question's content came from. A Source is for checking a Question; a Material is
    for learning."""

    url: HttpsUrl
    title: Text
    publisher: Text
    accessed: Annotated[
        date,
        Field(
            description=(
                "The UTC date the Source was read, YYYY-MM-DD: in the run that wrote the "
                "Question (the content check allows today or yesterday for a new Question)."
            )
        ),
    ]
    claim: Annotated[Text, Field(description="The claim the Question relies on.")]


class Retirement(_Model):
    """Why a Question was taken out of use. It stays in the Question Bank, and is never drawn."""

    reason: Text
    replaced_by: Annotated[
        PermanentId | None,
        Field(description="The Question that replaces it, if any: a Question in the bank."),
    ] = None
    on: Annotated[date | None, Field(description="The UTC date it was retired.")] = None


LessonTag = Annotated[
    PermanentId | None,
    Field(
        description=(
            "The Lesson the Question belongs to, in the Stack's newest Syllabus; null for none. "
            "It is the one field of a committed Question that may change (a re-tag)."
        )
    ),
]
Sources = Annotated[list[Source], Field(min_length=1)]
MaybeRetired = Annotated[
    Retirement | None,
    Field(description="Set once to retire the Question; a retirement is never undone."),
]


class MultipleChoiceQuestion(_Model):
    id: PermanentId
    lesson: LessonTag = None
    concept: PermanentId
    type: Literal["multiple_choice"]
    prompt: Text
    choices: Annotated[list[Choice], Field(min_length=2)]
    answer: ChoiceId
    explanation: Text
    materials: MaterialRefs
    sources: Sources
    retired: MaybeRetired = None


class WrittenQuestion(_Model):
    id: PermanentId
    lesson: LessonTag = None
    concept: PermanentId
    type: Literal["written"]
    prompt: Text
    model_answer: ModelAnswer
    explanation: Text
    materials: MaterialRefs
    sources: Sources
    retired: MaybeRetired = None


Question = Annotated[MultipleChoiceQuestion | WrittenQuestion, Field(discriminator="type")]


class QuestionBank(_Model):
    """One file of a Stack's Question Bank (`question-bank/<name>.json`). The bank is every file
    together: files only group Questions for readable diffs, and a Concept declared in one file
    can be tested in another. Questions testing the same Concept are siblings.

    The bank is append-only (ADR-0004): a committed Question is never edited or deleted, only
    retired or re-tagged to another Lesson."""

    model_config = ConfigDict(title="Question Bank")

    schema_version: Literal[2]
    concepts: list[Concept]
    questions: list[Question]


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


class ChallengeLaunch(_Model):
    """The Day a Stack's run of Daily Challenges starts (`challenges/launch.json`): Challenge #1
    is on it, and #n is n - 1 Days later. Like the Question Bank, it is the Stack's, not a
    version's."""

    model_config = ConfigDict(title="Challenge Launch")

    schema_version: Literal[1]
    launch: Annotated[date, Field(description="The UTC Day of Challenge #1, YYYY-MM-DD.")]


class DailyChallenge(_Model):
    """One Daily Challenge of a Stack (`challenges/<number>.json`, zero-padded: `001.json`): its
    three Questions, from the Stack's Question Bank. Written ahead as an Upcoming Challenge, it
    can be edited until its Day begins (00:00 UTC), and is frozen from then on."""

    model_config = ConfigDict(title="Daily Challenge")

    schema_version: Literal[1]
    number: Annotated[int, Field(ge=1, description="Numbered from the Stack's launch: #1, #2...")]
    date: Annotated[
        date,
        Field(description="Its UTC Day, YYYY-MM-DD: the launch Day plus number - 1 Days."),
    ]
    questions: Annotated[
        list[PermanentId],
        Field(
            min_length=3,
            max_length=3,
            json_schema_extra={"uniqueItems": True},
            description=(
                "IDs of three Questions of the Stack's Question Bank: two multiple choice and "
                "one written."
            ),
        ),
        AfterValidator(_unique),
    ]
