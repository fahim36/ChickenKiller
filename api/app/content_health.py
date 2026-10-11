"""Read-only imported-content maintenance evidence; never a learner quality score."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.content.check import LESSON_MIN, QUIZ_MULTIPLE_CHOICE, QUIZ_MULTIPLE_SELECT
from app.models import Concept, Lesson, Question, QuestionReport, Stack

ENRICHMENT_TARGET = 4
SOURCE_SAMPLE = 20


@dataclass(frozen=True)
class ConceptHealth:
    id: str
    name: str
    active_questions: int
    multiple_choice: int
    multiple_select: int
    legacy_written: int
    status: Literal["thin", "enriched", "retired_only", "untested"]


@dataclass(frozen=True)
class LessonHealth:
    id: str
    title: str
    active_questions: int
    multiple_choice: int
    multiple_select: int
    legacy_written: int
    quiz_eligible: bool


@dataclass(frozen=True)
class SourceHealth:
    url: str
    title: str
    oldest_accessed: date
    latest_accessed: date
    questions: int


@dataclass(frozen=True)
class StackHealth:
    id: str
    name: str
    syllabus_version: str | None
    active_questions: int
    retired_questions: int
    thin_concepts: int
    retired_only_concepts: int
    untested_concepts: int
    without_current_lesson: int
    unresolved_reports: int
    source_urls: int
    concepts: list[ConceptHealth]
    lessons: list[LessonHealth]
    sources: list[SourceHealth]


def _types(questions: list[Question]) -> Counter[str]:
    return Counter(q.type for q in questions)


def for_stack(session: Session, stack: Stack) -> StackHealth:
    bank = list(
        session.scalars(
            select(Question)
            .where(Question.stack_id == stack.id)
            .options(selectinload(Question.sources))
        )
    )
    live = [q for q in bank if not q.retired]
    by_concept: dict[int, list[Question]] = defaultdict(list)
    historical_concepts = {q.concept_pk for q in bank}
    by_lesson: dict[str | None, list[Question]] = defaultdict(list)
    for q in live:
        by_concept[q.concept_pk].append(q)
        by_lesson[q.lesson_id].append(q)
    concepts = []
    for c in session.scalars(
        select(Concept).where(Concept.stack_id == stack.id).order_by(Concept.id)
    ):
        questions = by_concept[c.pk]
        count = len(questions)
        status: Literal["thin", "enriched", "retired_only", "untested"]
        if count:
            status = "thin" if count < ENRICHMENT_TARGET else "enriched"
        else:
            status = "retired_only" if c.pk in historical_concepts else "untested"
        types = _types(questions)
        concepts.append(
            ConceptHealth(
                c.id,
                c.name,
                count,
                types["multiple_choice"],
                types["multiple_select"],
                types["written"],
                status,
            )
        )
    lessons = []
    current_ids = set()
    for lesson in session.scalars(
        select(Lesson)
        .where(Lesson.syllabus_pk == stack.current_syllabus_pk)
        .order_by(Lesson.position, Lesson.id)
    ):
        current_ids.add(lesson.id)
        questions = by_lesson[lesson.id]
        types = _types(questions)
        eligible = (
            len(questions) >= LESSON_MIN
            and types["multiple_choice"] >= QUIZ_MULTIPLE_CHOICE
            and (types["multiple_select"] + types["written"] >= QUIZ_MULTIPLE_SELECT)
        )
        lessons.append(
            LessonHealth(
                lesson.id,
                lesson.title,
                len(questions),
                types["multiple_choice"],
                types["multiple_select"],
                types["written"],
                eligible,
            )
        )
    sources: dict[str, SourceHealth] = {}
    for q in live:
        # The same URL can occur more than once on a Question; count distinct Questions.
        seen_urls = set()
        for source in q.sources:
            previous = sources.get(source.url)
            sources[source.url] = SourceHealth(
                source.url,
                previous.title if previous else source.title,
                min(previous.oldest_accessed, source.accessed) if previous else source.accessed,
                max(previous.latest_accessed, source.accessed) if previous else source.accessed,
                (previous.questions if previous else 0) + int(source.url not in seen_urls),
            )
            seen_urls.add(source.url)
    unresolved = len(
        session.scalars(
            select(QuestionReport.id).where(
                QuestionReport.stack_id == stack.id, QuestionReport.status.in_(("open", "accepted"))
            )
        ).all()
    )
    return StackHealth(
        id=stack.id,
        name=stack.name,
        syllabus_version=stack.current_syllabus.version if stack.current_syllabus else None,
        active_questions=len(live),
        retired_questions=len(bank) - len(live),
        thin_concepts=sum(c.status == "thin" for c in concepts),
        retired_only_concepts=sum(c.status == "retired_only" for c in concepts),
        untested_concepts=sum(c.status == "untested" for c in concepts),
        without_current_lesson=sum(q.lesson_id not in current_ids for q in live),
        unresolved_reports=unresolved,
        source_urls=len(sources),
        concepts=concepts,
        lessons=lessons,
        sources=sorted(sources.values(), key=lambda s: (s.oldest_accessed, s.url))[:SOURCE_SAMPLE],
    )


def overview(session: Session) -> list[StackHealth]:
    return [
        for_stack(session, stack) for stack in session.scalars(select(Stack).order_by(Stack.id))
    ]
