"""The MCP connector: lets a Learner's Claude client read the Stacks and propose content.

Served at `/mcp/` (streamable HTTP). Every request needs a personal access token
(app/access_tokens.py) as its bearer token; it signs the client in as that Learner, and every
draft it submits is recorded as theirs. This is how /update-syllabus and /write-challenges style
work can be done from any Claude client, by several people, each one known.

Content stays in git (ADR-0004): the append-only Question Bank and the Challenge files are
checked against the committed baseline, so the connector never writes them. It stores drafts
(`ContentDraft`); the Admin accepts or rejects each, and `content-export-drafts` writes the
accepted ones into the repo for the skills to merge and `content-check` to check.

Tools:
- anyone: `whoami`, `list_stacks`, `get_syllabus`, `submit_questions`, `submit_challenge`,
  `list_my_drafts`.
- the Admin only: `get_question_bank` and `get_challenges_status`. The bank includes the
  Upcoming Challenges' Questions, which no Learner may see before their Day.

No tool ever returns a Question's answer or Model Answer. New Questions are multiple choice or
multiple select: written ones are legacy (ADR-0008), and `submit_questions` refuses them.
"""

import contextvars
import json
from collections.abc import Awaitable, Callable, MutableMapping
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from pydantic import TypeAdapter, ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import access_tokens, stack_builder
from app.content import format as fmt
from app.content.check import CHALLENGE_TYPES, multiple_select_problems
from app.models import (
    Concept,
    ContentDraft,
    DailyChallenge,
    Learner,
    Lesson,
    Question,
    Stack,
    Syllabus,
    Week,
)

SessionScope = Callable[[], AbstractContextManager[Session]]
Scope = MutableMapping[str, Any]
Receive = Callable[[], Awaitable[MutableMapping[str, Any]]]
Send = Callable[[MutableMapping[str, Any]], Awaitable[None]]
ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]

MAX_QUESTIONS_PER_DRAFT = 50
MAX_NOTE_CHARS = 2000

_QUESTION: TypeAdapter[Any] = TypeAdapter(fmt.Question)
_CONCEPT = TypeAdapter(fmt.Concept)
_SYLLABUS: TypeAdapter[Any] = TypeAdapter(fmt.Syllabus)

BUILD_STACK_PROMPT = """\
Build the new Stack "{name}" (id: {stack_id}) for {audience}, through this connector. Work in
three steps and check `get_stack_plan("{stack_id}")` between them.

1. Request it. If `get_stack_plan` says nobody requested it, call `request_stack` with the id,
   the name, a one-line summary, the audience and the number of Weeks.

2. The weekly plan. Research what the role needs today from high-trust primary sources
   (official docs, standards, well-known books and courses, job postings). Then call
   `submit_syllabus` with the whole first Syllabus: schema_version 1, a version named for
   today's UTC date (vYYYY-MM-DD), the stack, every Material (id, title, https url, type,
   subject), and each Week with its number, title, goal, deliverable, interview_checks,
   Lessons (id like w01-l01, title, topics, exercise, minutes, materials) and Milestones
   (id like w01-m01, title, kind build or job-hunt, minutes, materials). Ids are lower-case
   words joined by hyphens and never reused.

3. The quiz setup. For every Lesson of the plan, call `submit_questions` (up to 50 per call)
   until `get_stack_plan` shows each Lesson ready: at least 8 Questions per Lesson, at least
   4 multiple choice and 2 multiple select, and every Concept with at least 2 Questions (so a
   Retake has a sibling). Declare new Concepts in `concepts`. Each Question has an id like
   w01-l01-q01, its lesson and concept, a clear prompt, an explanation, materials, and one
   or more sources (url, title, publisher, accessed = today, claim) that you actually fetched
   and that support the answer. Multiple choice (type multiple_choice): 4 choices, one right
   (`answer`), the right one not clearly the longest. Multiple select (type multiple_select):
   a prompt ending "Select all that apply.", 4 to 6 choices, `answers` listing every correct
   one (at least 2, and at least 1 choice wrong), the correct ones not all longer than the
   wrong ones. Never written: written Questions are no longer accepted.

Everything is a draft under your name until the Admin accepts it. Don't invent Sources."""


@dataclass(frozen=True)
class Caller:
    learner_id: int
    email: str
    is_admin: bool


_caller: contextvars.ContextVar[Caller] = contextvars.ContextVar("mcp_caller")


class ToolRefused(ToolError):
    """A tool call that can't be done: the message goes back to the client."""


def _me() -> Caller:
    return _caller.get()


def _admin() -> Caller:
    caller = _me()
    if not caller.is_admin:
        raise ToolRefused("Only the Admin can use this tool.")
    return caller


def build_server(
    session_scope: SessionScope, now: Callable[[], datetime], admin_emails: frozenset[str]
) -> MCPServer:
    """The MCP server and its tools. `session_scope` opens a database session per call."""
    server = MCPServer(
        name="Interview Cracker",
        instructions=(
            "Read the Stacks' Syllabuses and propose new Questions and Daily Challenges. "
            "Proposals are drafts, recorded under your name, for the Admin to accept; they "
            "change nothing until then. Questions follow the Question Bank format "
            "(content/schema): every Question needs Sources you fetched. To build a new Stack, "
            "use the build_stack prompt: request_stack, then its weekly plan (submit_syllabus), "
            "then its Questions (submit_questions)."
        ),
    )

    @server.tool()
    def whoami() -> dict[str, Any]:
        """Who this connector is signed in as."""
        caller = _me()
        return {"email": caller.email, "is_admin": caller.is_admin}

    @server.tool()
    def list_stacks() -> list[dict[str, Any]]:
        """The Stacks with a Syllabus: id, name and current Syllabus version."""
        with session_scope() as session:
            rows = session.execute(
                select(Stack.id, Stack.name, Syllabus.version)
                .join(Syllabus, Syllabus.pk == Stack.current_syllabus_pk)
                .order_by(Stack.name)
            ).all()
        return [{"id": i, "name": n, "version": v} for i, n, v in rows]

    @server.tool()
    def get_syllabus(stack_id: str) -> dict[str, Any]:
        """A Stack's current Syllabus: its Weeks and their Lessons (id, title, topics)."""
        with session_scope() as session:
            stack = _stack(session, stack_id)
            weeks = session.scalars(
                select(Week)
                .where(Week.syllabus_pk == stack.current_syllabus_pk)
                .order_by(Week.position)
            ).all()
            lessons = session.scalars(
                select(Lesson)
                .where(Lesson.syllabus_pk == stack.current_syllabus_pk)
                .order_by(Lesson.position)
            ).all()
            by_week: dict[int, list[dict[str, Any]]] = {}
            for lesson in lessons:
                by_week.setdefault(lesson.week_pk, []).append(
                    {"id": lesson.id, "title": lesson.title, "topics": list(lesson.topics)}
                )
            return {
                "stack_id": stack.id,
                "name": stack.name,
                "weeks": [
                    {
                        "id": w.id,
                        "number": w.number,
                        "title": w.title,
                        "goal": w.goal,
                        "lessons": by_week.get(w.pk, []),
                    }
                    for w in weeks
                ],
            }

    @server.tool()
    def get_question_bank(stack_id: str, lesson_id: str | None = None) -> dict[str, Any]:
        """Admin only. The Stack's Question Bank (optionally one Lesson's): each Question's id,
        Concept, type, Lesson, prompt and whether it is retired. Never the answers."""
        _admin()
        with session_scope() as session:
            _stack(session, stack_id)
            query = (
                select(Question, Concept.id)
                .join(Concept, Concept.pk == Question.concept_pk)
                .where(Question.stack_id == stack_id)
                .order_by(Question.position)
            )
            if lesson_id:
                query = query.where(Question.lesson_id == lesson_id)
            rows = session.execute(query).all()
            concepts = session.scalars(
                select(Concept.id).where(Concept.stack_id == stack_id).order_by(Concept.id)
            ).all()
            return {
                "concepts": list(concepts),
                "questions": [
                    {
                        "id": q.id,
                        "concept": concept_id,
                        "type": q.type,
                        "lesson": q.lesson_id,
                        "prompt": q.prompt,
                        "retired": q.retired_reason is not None,
                    }
                    for q, concept_id in rows
                ],
            }

    @server.tool()
    def get_challenges_status(stack_id: str) -> dict[str, Any]:
        """Admin only. How far ahead the Stack's Daily Challenges are written, and the next
        free Day and number."""
        _admin()
        with session_scope() as session:
            _stack(session, stack_id)
            last_day, last_number = session.execute(
                select(func.max(DailyChallenge.day), func.max(DailyChallenge.number)).where(
                    DailyChallenge.stack_id == stack_id
                )
            ).one()
        today = now().date()
        return {
            "today": today.isoformat(),
            "written_through": last_day.isoformat() if last_day else None,
            "days_left": max((last_day - today).days, 0) if last_day else 0,
            "next_number": (last_number or 0) + 1,
        }

    @server.tool()
    def submit_questions(
        stack_id: str,
        questions: list[dict[str, Any]],
        concepts: list[dict[str, Any]] | None = None,
        note: str = "",
    ) -> dict[str, Any]:
        """Propose new Questions for a Stack's Question Bank, as a draft for the Admin.

        Each Question follows the Question Bank format: multiple_choice (choices, `answer`) or
        multiple_select (4 to 6 choices, `answers`: every correct one, at least 2, not all),
        with a Concept and Sources. Written Questions are legacy and refused. New Concepts go
        in `concepts` ({id, name}). IDs must be new. `note` says what the Questions cover and
        why."""
        caller = _me()
        if not questions or len(questions) > MAX_QUESTIONS_PER_DRAFT:
            raise ToolRefused(f"Send between 1 and {MAX_QUESTIONS_PER_DRAFT} Questions.")
        parsed_questions = [
            _parse(_QUESTION, q, f"questions[{i}]") for i, q in enumerate(questions)
        ]
        parsed_concepts = [
            _parse(_CONCEPT, c, f"concepts[{i}]") for i, c in enumerate(concepts or [])
        ]
        written = [q.id for q in parsed_questions if isinstance(q, fmt.WrittenQuestion)]
        if written:
            raise ToolRefused(
                f"Written Questions are no longer accepted: write {', '.join(written)} as "
                "multiple_select (select all that apply) instead."
            )
        for i, q in enumerate(parsed_questions):
            if isinstance(q, fmt.MultipleSelectQuestion):
                problems = multiple_select_problems(q)
                if problems:
                    raise ToolRefused(f"questions[{i}] ({q.id}): {'; '.join(problems)}.")
        ids = [q.id for q in parsed_questions]
        if len(set(ids)) != len(ids):
            raise ToolRefused("Two of the Questions have the same id.")
        with session_scope() as session:
            lessons = _lessons_of(session, stack_id)
            drafted_questions, drafted_concepts = stack_builder.drafted_ids(session, stack_id)
            taken = sorted(
                set(
                    session.scalars(
                        select(Question.id).where(
                            Question.stack_id == stack_id, Question.id.in_(ids)
                        )
                    )
                )
                | (set(ids) & drafted_questions)
            )
            if taken:
                raise ToolRefused(
                    f"These ids are already in the bank or a draft: {', '.join(taken)}."
                )
            untagged = sorted({q.lesson for q in parsed_questions if q.lesson} - set(lessons))
            if untagged:
                raise ToolRefused(f"No such Lessons in this Stack: {', '.join(untagged)}.")
            known = (
                set(session.scalars(select(Concept.id).where(Concept.stack_id == stack_id)))
                | drafted_concepts
                | {c.id for c in parsed_concepts}
            )
            unknown = sorted({q.concept for q in parsed_questions} - known)
            if unknown:
                raise ToolRefused(
                    f"Unknown Concepts (add them to `concepts`): {', '.join(unknown)}."
                )
            payload = {
                "concepts": [c.model_dump(mode="json") for c in parsed_concepts],
                "questions": [
                    q.model_dump(mode="json", exclude_none=True) for q in parsed_questions
                ],
            }
            return _save_draft(session, caller, stack_id, "questions", payload, note, now())

    @server.tool()
    def submit_challenge(
        stack_id: str, day: str, question_ids: list[str], note: str = ""
    ) -> dict[str, Any]:
        """Propose a Daily Challenge: three Question ids from the bank (not retired), two
        multiple choice then one multiple select, for a future UTC Day (YYYY-MM-DD) that has
        none yet. A draft for the Admin."""
        caller = _me()
        try:
            on = date.fromisoformat(day)
        except ValueError as error:
            raise ToolRefused("`day` must be a date, YYYY-MM-DD.") from error
        if on <= now().date():
            raise ToolRefused("The Day must be in the future (UTC).")
        if len(question_ids) != 3 or len(set(question_ids)) != 3:
            raise ToolRefused("A Daily Challenge is three different Questions.")
        with session_scope() as session:
            _stack(session, stack_id)
            if session.scalar(
                select(DailyChallenge.pk).where(
                    DailyChallenge.stack_id == stack_id, DailyChallenge.day == on
                )
            ):
                raise ToolRefused(f"{day} already has a Daily Challenge.")
            live = {
                qid: kind
                for qid, kind in session.execute(
                    select(Question.id, Question.type).where(
                        Question.stack_id == stack_id,
                        Question.id.in_(question_ids),
                        Question.retired_reason.is_(None),
                    )
                )
            }
            missing = [q for q in question_ids if q not in live]
            if missing:
                raise ToolRefused(f"Not live Questions of this Stack: {', '.join(missing)}.")
            if tuple(live[q] for q in question_ids) != CHALLENGE_TYPES:
                raise ToolRefused(
                    "A Daily Challenge is two multiple-choice Questions, then one multiple "
                    "select, in that order."
                )
            payload = {"day": on.isoformat(), "questions": question_ids}
            return _save_draft(session, caller, stack_id, "challenge", payload, note, now())

    @server.tool()
    def request_stack(
        stack_id: str,
        name: str,
        summary: str,
        audience: str = "",
        weeks: int = 12,
        notes: str = "",
    ) -> dict[str, Any]:
        """Start a new Stack: step 1 of 3. Records a request (id such as data-engineer, name,
        one-line summary, who it is for, how many Weeks). Then submit its weekly plan with
        submit_syllabus, then its Questions with submit_questions. `get_stack_plan` says where
        it stands. Use the `build_stack` prompt for the whole procedure."""
        caller = _me()
        with session_scope() as session:
            try:
                stack_builder.request_stack(
                    session,
                    caller.learner_id,
                    stack_id=stack_id,
                    name=name,
                    summary=summary,
                    audience=audience,
                    weeks=weeks,
                    notes=notes,
                    now=now(),
                )
            except stack_builder.RequestRefused as error:
                raise ToolRefused(str(error)) from error
            found = stack_builder.plan(session, stack_id.strip().lower())
            assert found is not None
            return found.summary()

    @server.tool()
    def get_stack_plan(stack_id: str) -> dict[str, Any]:
        """Where a requested Stack stands: the request, its weekly plan, how many Questions
        each Lesson has drafted, and the next step."""
        with session_scope() as session:
            found = stack_builder.plan(session, stack_id)
            if found is None:
                raise ToolRefused(f"Nobody requested a Stack {stack_id!r}: use request_stack.")
            summary = found.summary()
            if found.syllabus is not None:
                summary["syllabus"] = found.syllabus.payload
            return summary

    @server.tool()
    def list_requested_stacks() -> list[dict[str, Any]]:
        """Stacks requested but not live yet, newest first, with their progress."""
        with session_scope() as session:
            return [p.summary() for p in stack_builder.requested_stacks(session)]

    @server.tool()
    def delete_stack_request(stack_id: str) -> dict[str, Any]:
        """Delete a requested Stack that isn't live yet, with all its drafts (weekly plans and
        Questions). Only whoever requested it, or the Admin."""
        caller = _me()
        with session_scope() as session:
            learner = session.get(Learner, caller.learner_id)
            assert learner is not None
            try:
                gone = stack_builder.delete_request(
                    session, learner, stack_id, is_admin=caller.is_admin
                )
            except stack_builder.RequestNotFound as error:
                raise ToolRefused(f"No request for {stack_id!r} that you may delete.") from error
            except stack_builder.RequestRefused as error:
                raise ToolRefused(str(error)) from error
        return {"stack_id": stack_id, "drafts_deleted": gone}

    @server.tool()
    def submit_syllabus(stack_id: str, syllabus: dict[str, Any], note: str = "") -> dict[str, Any]:
        """Step 2 of 3 for a requested Stack: its weekly plan, the whole first Syllabus in the
        Syllabus format (schema_version 1, version vYYYY-MM-DD, stack {id, name, summary},
        materials, and weeks with lessons and milestones). A new submission replaces the
        previous plan; Questions already drafted must still match its Lesson ids."""
        caller = _me()
        parsed = _parse(_SYLLABUS, syllabus, "syllabus")
        if parsed.stack.id != stack_id:
            raise ToolRefused(f"syllabus.stack.id is {parsed.stack.id!r}, not {stack_id!r}.")
        materials = {m.id for m in parsed.materials}
        refs = {
            ref
            for week in parsed.weeks
            for item in [*week.lessons, *week.milestones]
            for ref in item.materials
        }
        if refs - materials:
            missing = ", ".join(sorted(refs - materials))
            raise ToolRefused(f"Materials not in `materials`: {missing}.")
        ids = [w.id for w in parsed.weeks] + [
            x.id for w in parsed.weeks for x in [*w.lessons, *w.milestones]
        ]
        if len(ids) != len(set(ids)):
            raise ToolRefused("Every Week, Lesson and Milestone needs its own id.")
        with session_scope() as session:
            if session.get(Stack, stack_id) is not None:
                raise ToolRefused(
                    "This Stack is live already: change it with /update-syllabus instead."
                )
            if stack_builder.find_request(session, stack_id) is None:
                raise ToolRefused(f"Request the Stack first with request_stack({stack_id!r}, ...).")
            payload = parsed.model_dump(mode="json", exclude_none=False)
            return _save_draft(session, caller, stack_id, "syllabus", payload, note, now())

    @server.tool()
    def list_my_drafts() -> list[dict[str, Any]]:
        """Your drafts, newest first, with their status (pending, accepted, rejected or
        exported)."""
        caller = _me()
        with session_scope() as session:
            drafts = session.scalars(
                select(ContentDraft)
                .where(ContentDraft.learner_id == caller.learner_id)
                .order_by(ContentDraft.created_at.desc(), ContentDraft.id.desc())
                .limit(50)
            ).all()
            return [_draft_out(d) for d in drafts]

    @server.prompt()
    def build_stack(stack_id: str, name: str = "", audience: str = "") -> str:
        """Build a new Stack from scratch: the weekly plan first, then the quiz setup."""
        return BUILD_STACK_PROMPT.format(
            stack_id=stack_id,
            name=name or stack_id,
            audience=audience or "the Learners who will study it",
        )

    return server


def _lessons_of(session: Session, stack_id: str) -> list[str]:
    """The Lesson ids Questions may be tagged to: a live Stack's current Syllabus, or a
    requested Stack's weekly-plan draft."""
    stack = session.get(Stack, stack_id)
    if stack is not None and stack.current_syllabus_pk is not None:
        return list(
            session.scalars(
                select(Lesson.id)
                .where(Lesson.syllabus_pk == stack.current_syllabus_pk)
                .order_by(Lesson.position)
            )
        )
    if stack_builder.find_request(session, stack_id) is None:
        raise ToolRefused(f"No Stack {stack_id!r}. `list_stacks` lists them.")
    syllabus = stack_builder.current_syllabus(session, stack_id)
    if syllabus is None:
        raise ToolRefused("Submit the weekly plan with submit_syllabus before its Questions.")
    return list(stack_builder.drafted_lessons(syllabus))


def _stack(session: Session, stack_id: str) -> Stack:
    stack = session.get(Stack, stack_id)
    if stack is None or stack.current_syllabus_pk is None:
        raise ToolRefused(f"No Stack {stack_id!r}. `list_stacks` lists them.")
    return stack


def _parse(adapter: TypeAdapter[Any], value: Any, where: str) -> Any:
    try:
        return adapter.validate_python(value)
    except ValidationError as error:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in error.errors()[:5]
        )
        raise ToolRefused(f"{where} isn't valid: {problems}") from error


def _save_draft(
    session: Session,
    caller: Caller,
    stack_id: str,
    kind: str,
    payload: dict[str, Any],
    note: str,
    now: datetime,
) -> dict[str, Any]:
    draft = ContentDraft(
        learner_id=caller.learner_id,
        stack_id=stack_id,
        kind=kind,
        payload=payload,
        note=note.strip()[:MAX_NOTE_CHARS],
        status="pending",
        created_at=now,
    )
    session.add(draft)
    session.commit()
    return _draft_out(draft)


def _draft_out(draft: ContentDraft) -> dict[str, Any]:
    return {
        "id": draft.id,
        "stack_id": draft.stack_id,
        "kind": draft.kind,
        "status": draft.status,
        "created_at": draft.created_at.isoformat(),
        "items": len(draft.payload.get("questions", [])),
    }


class BearerTokenAuth:
    """ASGI middleware: signs each request in by its personal access token, or answers 401."""

    def __init__(
        self,
        app: ASGIApp,
        session_scope: SessionScope,
        now: Callable[[], datetime],
        admin_emails: frozenset[str],
    ) -> None:
        self.app = app
        self.session_scope = session_scope
        self.now = now
        self.admin_emails = admin_emails

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        scheme, _, token = headers.get("authorization", "").partition(" ")
        caller = None
        if scheme.lower() == "bearer" and token:
            with self.session_scope() as session:
                learner = access_tokens.learner_for(session, token.strip(), self.now())
                if learner is not None:
                    caller = _caller_for(learner, self.admin_emails)
        if caller is None:
            await _unauthorized(send)
            return
        reset = _caller.set(caller)
        try:
            await self.app(scope, receive, send)
        finally:
            _caller.reset(reset)


def _caller_for(learner: Learner, admin_emails: frozenset[str]) -> Caller:
    return Caller(learner.id, learner.email, learner.email in admin_emails)


async def _unauthorized(send: Send) -> None:
    body = json.dumps(
        {"error": "Use a personal access token from Settings as the bearer token."}
    ).encode()
    await send(
        {
            "type": "http.response.start",
            "status": 401,
            "headers": [
                (b"content-type", b"application/json"),
                (b"www-authenticate", b"Bearer"),
                (b"content-length", str(len(body)).encode()),
            ],
        }
    )
    await send({"type": "http.response.body", "body": body})
