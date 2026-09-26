import re
import zoneinfo
from datetime import datetime
from functools import cache

from pydantic import BaseModel as _BaseModel
from pydantic import ConfigDict, field_validator

from app.unlocking import LessonState


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
    """A Lesson on the Week map, with its state for the signed-in Learner."""

    id: str
    title: str
    minutes: int
    state: LessonState


class MilestoneOut(BaseModel):
    """A Milestone on the Week map, and whether the signed-in Learner has ticked it."""

    id: str
    title: str
    kind: str
    minutes: int
    ticked: bool


class MilestoneTickIn(BaseModel):
    ticked: bool


class MilestoneTickOut(BaseModel):
    id: str
    ticked: bool


class WeekOut(BaseModel):
    """A Week of the Week map: its Lessons and Milestones in Syllabus order."""

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
    state: LessonState
    previous_lesson_id: str | None
    next_lesson_id: str | None


class ActiveStackOut(BaseModel):
    """The Learner's Active Stack, and when they started studying it."""

    id: str
    name: str
    started_at: datetime


class MeOut(BaseModel):
    """The signed-in Learner. Admin-only screens check `is_admin`.

    `needs_onboarding` is true until the Learner has picked an Active Stack and a time zone.
    """

    email: str
    is_admin: bool
    needs_onboarding: bool
    active_stack: ActiveStackOut | None
    time_zone: str | None


class SettingsIn(BaseModel):
    """What onboarding sets, and settings change: the Active Stack and the time zone."""

    active_stack_id: str
    time_zone: str

    @field_validator("time_zone")
    @classmethod
    def _is_an_iana_name(cls, value: str) -> str:
        if value not in _iana_time_zones():
            raise ValueError("Choose a time zone from the list, such as Asia/Dhaka")
        return value


@cache
def _iana_time_zones() -> frozenset[str]:
    # Exact names only: looking a name up with ZoneInfo would also accept file paths, and any
    # letter case on Windows.
    return frozenset(zoneinfo.available_timezones())


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
