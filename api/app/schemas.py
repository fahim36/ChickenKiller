import re
from datetime import datetime

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, field_validator


class BaseModel(_BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StackSummary(BaseModel):
    id: str
    name: str
    summary: str
    version: str


class MaterialOut(BaseModel):
    id: str
    title: str
    url: str
    type: str


class LessonSummary(BaseModel):
    id: str
    title: str
    minutes: int


class MilestoneOut(BaseModel):
    id: str
    title: str
    kind: str
    minutes: int


class WeekOut(BaseModel):
    id: str
    number: int
    title: str
    goal: str
    deliverable: str
    lessons: list[LessonSummary]
    milestones: list[MilestoneOut]


class SyllabusOut(StackSummary):
    weeks: list[WeekOut]


class WeekRef(BaseModel):
    id: str
    number: int
    title: str


class LessonOut(BaseModel):
    id: str
    stack_id: str
    week: WeekRef
    title: str
    topics: list[str]
    exercise: str | None
    minutes: int
    materials: list[MaterialOut]
    previous_lesson_id: str | None
    next_lesson_id: str | None


class MeOut(BaseModel):
    """The signed-in Learner. Later admin-only screens check `is_admin`."""

    email: str
    is_admin: bool


# Deliberately loose: Clerk verifies the address when the person signs up.
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InvitationIn(BaseModel):
    email: str

    @field_validator("email")
    @classmethod
    def _is_an_email(cls, value: str) -> str:
        value = value.strip().lower()
        if not _EMAIL.match(value):
            raise ValueError("Enter an email address, such as name@example.com")
        return value


class InvitationOut(BaseModel):
    email: str
    invited_at: datetime
