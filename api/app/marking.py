"""Marking one answer to one Question: the same rules wherever the Question is asked (Lesson
Quiz, #8's Retakes and #9's Review).

    mark(question, response, grader) -> Marked(correct, feedback)

- Multiple choice: correct when `response` is the Question's answer. A response that isn't one
  of its choices raises NotAChoice.
- Multiple select (ADR-0008): `response` is the ticked choice IDs, comma-separated ("a,c";
  `response_text` turns the list an API body carries into that). Correct only when the ticks
  are exactly the Question's `answers`: all or nothing, with no grading call, so it can never
  fail to grade. An ID that isn't one of its choices raises NotAChoice; no ticks is unanswered.
- Written (legacy, ADR-0008): graded against the Model Answer by `grader` (app/grading.py;
  routes get it from `GraderDep`). An answer longer than `grading.MAX_ANSWER_CHARS` raises
  AnswerTooLong before any call. When grading fails it raises `grading.GradingFailed`: the
  caller must record nothing and let the Learner resubmit, so a failure never counts as a
  Missed Question.
- Unanswered (`None`, a blank written answer, or no ticks): missed, with no feedback and no
  grading call.

Callers that mark several answers should use `mark_all`, which refuses a bad choice or an
overlong answer before any grading call is paid for, then grades the written answers in
parallel: a grading call takes seconds, so two written answers take about as long as one.
"""

from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any

from app.grading import MAX_ANSWER_CHARS, Grader, GradingFailed
from app.models import Question

__all__ = [
    "AnswerTooLong",
    "GradingFailed",
    "Marked",
    "NotAChoice",
    "mark",
    "mark_all",
    "response_text",
    "selected_choices",
]

MULTIPLE_SELECT = "multiple_select"


class NotAChoice(Exception):
    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


class AnswerTooLong(Exception):
    def __init__(self, question_id: str) -> None:
        super().__init__(question_id)
        self.question_id = question_id


@dataclass(frozen=True)
class Marked:
    correct: bool
    feedback: str | None = None
    """The grader's one line, for a written answer that was graded; otherwise None."""


def response_text(response: str | Sequence[str] | None) -> str | None:
    """A response as it is marked and stored: a list of ticked choice IDs (a multiple-select
    answer) becomes them sorted and comma-separated, "a,c", or None for no ticks. A string is
    kept as it is."""
    if response is None or isinstance(response, str):
        return response
    ticked = sorted({choice.strip() for choice in response if choice.strip()})
    return ",".join(ticked) or None


def selected_choices(response: str | None) -> list[str]:
    """The choice IDs a multiple-select `response` ticked ("a,c"), sorted; none for None."""
    if response is None:
        return []
    return sorted({choice.strip() for choice in response.split(",") if choice.strip()})


def mark(question: Question, response: str | None, grader: Grader) -> Marked:
    """Mark one response to `question`. Raises NotAChoice, AnswerTooLong or GradingFailed."""
    if question.type == "written":
        return _mark_written(question, response, grader)
    if question.type == MULTIPLE_SELECT:
        return _mark_multiple_select(question, response)
    if response is None:
        return Marked(correct=False)
    if response not in {c["id"] for c in question.choices or []}:
        raise NotAChoice(question.id)
    return Marked(correct=response == question.answer)


def mark_all(
    questions: Sequence[Question], responses: Mapping[str, str | None], grader: Grader
) -> dict[str, Marked]:
    """Mark each Question's response (a Question left out of `responses` is unanswered), keyed
    by Question ID in the order given. Multiple choice is marked first and every written answer's
    length checked, before any grading call; the written answers are then graded at the same
    time. Any exception from `mark` propagates (the first Question's, in the order given): all
    or nothing."""
    for q in questions:
        response = responses.get(q.id)
        if q.type == "written" and response is not None and len(response) > MAX_ANSWER_CHARS:
            raise AnswerTooLong(q.id)
    marked = {q.id: mark(q, responses.get(q.id), grader) for q in questions if q.type != "written"}
    written = [q for q in questions if q.type == "written"]
    if len(written) > 1:
        # Only the grading call runs on the threads: the Questions' attributes are read here,
        # since an ORM session must not be used from several threads.
        calls = [(q, responses.get(q.id)) for q in written]
        with ThreadPoolExecutor(max_workers=len(calls)) as pool:
            futures = [
                pool.submit(_mark_written_detached, *_detach(q, r), grader) for q, r in calls
            ]
        for q, future in zip(written, futures, strict=True):
            marked[q.id] = future.result()
    else:
        marked.update({q.id: mark(q, responses.get(q.id), grader) for q in written})
    return {q.id: marked[q.id] for q in questions}


def _mark_multiple_select(question: Question, response: str | None) -> Marked:
    ticked = selected_choices(response)
    if not ticked:
        return Marked(correct=False)
    if not set(ticked) <= {c["id"] for c in question.choices or []}:
        raise NotAChoice(question.id)
    return Marked(correct=set(ticked) == set(question.answers or []))


def _detach(
    question: Question, response: str | None
) -> tuple[str, str, Mapping[str, Any], str | None]:
    return question.id, question.prompt, question.model_answer or {}, response


def _mark_written(question: Question, response: str | None, grader: Grader) -> Marked:
    assert question.model_answer is not None, f"{question.id} has no Model Answer"
    return _mark_written_detached(
        question.id, question.prompt, question.model_answer, response, grader
    )


def _mark_written_detached(
    question_id: str,
    prompt: str,
    model_answer: Mapping[str, Any],
    response: str | None,
    grader: Grader,
) -> Marked:
    if response is None or not response.strip():
        return Marked(correct=False)
    if len(response) > MAX_ANSWER_CHARS:
        raise AnswerTooLong(question_id)
    assert model_answer, f"{question_id} has no Model Answer"
    grade = grader.grade(prompt, model_answer, response)
    return Marked(correct=grade.passed, feedback=grade.feedback)
