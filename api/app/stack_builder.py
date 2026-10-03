"""Building a new Stack through drafts: a request, then its weekly plan, then its Questions.

1. **Request** (`request_stack`): someone asks for a Stack, from the "Add a Stack" button or
   the MCP connector: its id, name, summary, who it is for and how many Weeks. A draft of kind
   `stack`.
2. **Weekly plan** (`syllabus` draft): Claude, through the connector, submits the Stack's first
   Syllabus: its Weeks, Lessons, Milestones and Materials, in the Syllabus format. The newest
   one not rejected is the plan.
3. **Quiz setup** (`questions` drafts): then Questions for each Lesson of that plan. A Lesson
   Quiz needs at least 8 Questions per Lesson that aren't retired, 4 of them multiple choice and
   2 multiple select, and every Concept at least 2 (the content check's rules). A new Stack has
   no written Questions: they are legacy (ADR-0008).

`plan` reports where a Stack stands, so both the Stacks screen and Claude know the next step.
Content still only enters through git (ADR-0004, ADR-0007): once the Admin accepts the drafts,
`content-export-drafts` writes the version folder and the Question Bank files, and
`content-check` then `content-import` make the Stack live.
"""

import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import ContentDraft, Learner, Stack

LESSON_MIN = 8
QUIZ_MULTIPLE_CHOICE, QUIZ_MULTIPLE_SELECT = 4, 2
MIN_QUESTIONS_PER_CONCEPT = 2
MAX_WEEKS = 52
LIVE = ("pending", "accepted", "exported")
"""Draft statuses that still count: everything but rejected."""

_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
RESERVED_IDS = {"new"}
"""`/stacks/new` is the Add a Stack screen, so no Stack may be called that."""


class RequestRefused(Exception):
    """The Stack can't be requested: the message says why."""


class RequestNotFound(Exception):
    """No live request for that Stack, or not one this Learner may delete."""


@dataclass(frozen=True)
class LessonProgress:
    id: str
    title: str
    multiple_choice: int
    multiple_select: int

    @property
    def total(self) -> int:
        return self.multiple_choice + self.multiple_select

    @property
    def ready(self) -> bool:
        return (
            self.total >= LESSON_MIN
            and self.multiple_choice >= QUIZ_MULTIPLE_CHOICE
            and self.multiple_select >= QUIZ_MULTIPLE_SELECT
        )


@dataclass(frozen=True)
class Plan:
    """Where a requested Stack stands."""

    request: ContentDraft
    requested_by: str
    syllabus: ContentDraft | None
    lessons: list[LessonProgress] = field(default_factory=list)
    thin_concepts: list[str] = field(default_factory=list)
    """Concepts with fewer than two Questions drafted."""

    @property
    def step(self) -> str:
        """`plan` (no weekly plan yet), `questions` (Lessons still short of Questions), or
        `review` (everything is drafted: the Admin accepts and exports)."""
        if self.syllabus is None:
            return "plan"
        if not self.lessons or not all(lesson.ready for lesson in self.lessons):
            return "questions"
        if self.thin_concepts:
            return "questions"
        return "review"

    def summary(self) -> dict[str, Any]:
        payload = self.request.payload
        return {
            "stack_id": payload["id"],
            "name": payload["name"],
            "requested_by": self.requested_by,
            "request_status": self.request.status,
            "weeks_wanted": payload.get("weeks"),
            "step": self.step,
            "next_step": NEXT_STEP[self.step],
            "syllabus_draft": self.syllabus.id if self.syllabus else None,
            "syllabus_status": self.syllabus.status if self.syllabus else None,
            "lessons": [
                {
                    "id": lesson.id,
                    "title": lesson.title,
                    "multiple_choice": lesson.multiple_choice,
                    "multiple_select": lesson.multiple_select,
                    "ready": lesson.ready,
                }
                for lesson in self.lessons
            ],
            "lessons_ready": sum(1 for lesson in self.lessons if lesson.ready),
            "thin_concepts": self.thin_concepts,
        }


NEXT_STEP = {
    "plan": (
        "Research the field, then submit the weekly plan with submit_syllabus: every Week with "
        "its Lessons, Milestones and Materials, in the Syllabus format."
    ),
    "questions": (
        f"Submit Questions for each Lesson with submit_questions: at least {LESSON_MIN} per "
        f"Lesson, {QUIZ_MULTIPLE_CHOICE} multiple choice and {QUIZ_MULTIPLE_SELECT} multiple "
        "select (never written), every "
        f"Concept with at least {MIN_QUESTIONS_PER_CONCEPT}, each with the Sources you fetched."
    ),
    "review": (
        "Everything is drafted. The Admin accepts the drafts in the app, runs "
        "content-export-drafts, then content-check and content-import."
    ),
}


def request_stack(
    session: Session,
    learner: Learner | int,
    *,
    stack_id: str,
    name: str,
    summary: str,
    audience: str = "",
    weeks: int = 12,
    notes: str = "",
    now: datetime,
) -> ContentDraft:
    """Record a request for a new Stack. Raises RequestRefused."""
    stack_id = stack_id.strip().lower()
    name, summary = name.strip(), summary.strip()
    if not _ID.match(stack_id) or len(stack_id) > 80 or stack_id in RESERVED_IDS:
        raise RequestRefused(
            "The id must be lower-case words joined by hyphens, such as data-engineer."
        )
    if not name or not summary:
        raise RequestRefused("Give the Stack a name and a one-line summary.")
    if not 1 <= weeks <= MAX_WEEKS:
        raise RequestRefused(f"A Stack has between 1 and {MAX_WEEKS} Weeks.")
    if session.get(Stack, stack_id) is not None:
        raise RequestRefused(f"There is already a Stack {stack_id!r}.")
    if find_request(session, stack_id) is not None:
        raise RequestRefused(f"{stack_id!r} is already requested.")
    draft = ContentDraft(
        learner_id=learner if isinstance(learner, int) else learner.id,
        stack_id=stack_id,
        kind="stack",
        payload={
            "id": stack_id,
            "name": name[:120],
            "summary": summary[:500],
            "audience": audience.strip()[:500],
            "weeks": weeks,
        },
        note=notes.strip()[:2000],
        status="pending",
        created_at=now,
    )
    session.add(draft)
    session.commit()
    return draft


def find_request(session: Session, stack_id: str) -> ContentDraft | None:
    """The live request for `stack_id`, if any."""
    return session.scalar(
        select(ContentDraft)
        .where(
            ContentDraft.stack_id == stack_id,
            ContentDraft.kind == "stack",
            ContentDraft.status.in_(LIVE),
        )
        .order_by(ContentDraft.id.desc())
        .limit(1)
    )


def current_syllabus(session: Session, stack_id: str) -> ContentDraft | None:
    """The newest weekly plan drafted for `stack_id` that isn't rejected."""
    return session.scalar(
        select(ContentDraft)
        .where(
            ContentDraft.stack_id == stack_id,
            ContentDraft.kind == "syllabus",
            ContentDraft.status.in_(LIVE),
        )
        .order_by(ContentDraft.id.desc())
        .limit(1)
    )


def drafted_lessons(syllabus: ContentDraft | None) -> dict[str, str]:
    """The Lessons (id: title) of a weekly-plan draft, in order."""
    if syllabus is None:
        return {}
    return {
        lesson["id"]: lesson["title"]
        for week in syllabus.payload.get("weeks", [])
        for lesson in week.get("lessons", [])
    }


def question_drafts(session: Session, stack_id: str) -> list[ContentDraft]:
    return list(
        session.scalars(
            select(ContentDraft)
            .where(
                ContentDraft.stack_id == stack_id,
                ContentDraft.kind == "questions",
                ContentDraft.status.in_(LIVE),
            )
            .order_by(ContentDraft.id)
        )
    )


def drafted_ids(session: Session, stack_id: str) -> tuple[set[str], set[str]]:
    """The Question and Concept ids already drafted for the Stack (not rejected)."""
    questions: set[str] = set()
    concepts: set[str] = set()
    for draft in question_drafts(session, stack_id):
        questions.update(q["id"] for q in draft.payload.get("questions", []))
        concepts.update(c["id"] for c in draft.payload.get("concepts", []))
    return questions, concepts


def plan(session: Session, stack_id: str) -> Plan | None:
    """Where the requested Stack `stack_id` stands, or None if nobody requested it."""
    request = find_request(session, stack_id)
    if request is None:
        return None
    author = session.get(Learner, request.learner_id)
    syllabus = current_syllabus(session, stack_id)
    lessons = drafted_lessons(syllabus)
    types: dict[str, Counter[str]] = {lesson_id: Counter() for lesson_id in lessons}
    per_concept: Counter[str] = Counter()
    declared: set[str] = set()
    for draft in question_drafts(session, stack_id):
        declared.update(c["id"] for c in draft.payload.get("concepts", []))
        for q in draft.payload.get("questions", []):
            per_concept[q["concept"]] += 1
            if q.get("lesson") in types:
                types[q["lesson"]][q["type"]] += 1
    return Plan(
        request=request,
        requested_by=author.email if author else "",
        syllabus=syllabus,
        lessons=[
            LessonProgress(
                lesson_id,
                title,
                types[lesson_id]["multiple_choice"],
                types[lesson_id]["multiple_select"],
            )
            for lesson_id, title in lessons.items()
        ],
        thin_concepts=sorted(
            c for c in declared | set(per_concept) if per_concept[c] < MIN_QUESTIONS_PER_CONCEPT
        ),
    )


def requested_stacks(session: Session) -> list[Plan]:
    """Every live Stack request not imported yet, newest first."""
    requests = session.scalars(
        select(ContentDraft)
        .where(ContentDraft.kind == "stack", ContentDraft.status.in_(LIVE))
        .order_by(ContentDraft.id.desc())
    ).all()
    plans = []
    for request in requests:
        if session.get(Stack, request.stack_id) is not None:
            continue  # imported: it is a real Stack now
        found = plan(session, request.stack_id)
        if found is not None:
            plans.append(found)
    return plans


def delete_request(session: Session, learner: Learner, stack_id: str, *, is_admin: bool) -> int:
    """Delete a requested Stack that isn't live yet, with every draft for it (its weekly plans
    and Questions, whatever their status). Only its requester or the Admin may. Returns how many
    drafts went. Raises RequestNotFound, or RequestRefused for a live Stack. Files already
    exported into `content/` stay: delete them from the repo by hand."""
    request = find_request(session, stack_id)
    if request is None or (request.learner_id != learner.id and not is_admin):
        raise RequestNotFound(stack_id)
    if session.get(Stack, stack_id) is not None:
        raise RequestRefused("This Stack is live already, so it can't be deleted here.")
    result = session.execute(delete(ContentDraft).where(ContentDraft.stack_id == stack_id))
    session.commit()
    return int(result.rowcount)  # type: ignore[attr-defined]
