"""`marking.mark`: one answer to one Question, marked the same way wherever it is asked (Lesson
Quiz, Retakes and Review). No database: Questions are plain objects."""

import threading
from typing import Any

import pytest

from app.grading import Grade
from app.marking import AnswerTooLong, GradingFailed, Marked, NotAChoice, mark, mark_all
from app.models import Question
from tests.conftest import FakeGrader

MULTIPLE_CHOICE = Question(
    id="q-mc",
    type="multiple_choice",
    prompt="Pick one.",
    choices=[{"id": "a", "text": "A"}, {"id": "b", "text": "B"}],
    answer="a",
)
WRITTEN = Question(
    id="q-w",
    type="written",
    prompt="Explain.",
    model_answer={"summary": "S", "key_points": ["one", "two"]},
)


def test_multiple_choice_is_right_only_for_its_answer() -> None:
    grader = FakeGrader()
    assert mark(MULTIPLE_CHOICE, "a", grader) == Marked(correct=True)
    assert mark(MULTIPLE_CHOICE, "b", grader) == Marked(correct=False)
    assert mark(MULTIPLE_CHOICE, None, grader) == Marked(correct=False)
    with pytest.raises(NotAChoice):
        mark(MULTIPLE_CHOICE, "z", grader)
    assert grader.calls == []


def test_a_written_answer_is_graded_with_feedback() -> None:
    grader = FakeGrader()
    assert mark(WRITTEN, "The right idea.", grader) == Marked(True, "Covers every key point.")
    assert mark(WRITTEN, "Hmm.", grader) == Marked(False, "Missing: one.")
    assert grader.calls[0] == ("Explain.", WRITTEN.model_answer, "The right idea.")


def test_a_blank_written_answer_is_missed_without_grading() -> None:
    grader = FakeGrader()
    assert mark(WRITTEN, None, grader) == Marked(correct=False)
    assert mark(WRITTEN, "  ", grader) == Marked(correct=False)
    assert grader.calls == []


def test_a_grading_failure_is_raised_not_marked_missed() -> None:
    grader = FakeGrader()
    grader.failing = True
    with pytest.raises(GradingFailed):
        mark(WRITTEN, "The right idea.", grader)


def test_an_overlong_written_answer_is_refused() -> None:
    with pytest.raises(AnswerTooLong):
        mark(WRITTEN, "x" * 4001, FakeGrader())


WRITTEN_2 = Question(
    id="q-w2",
    type="written",
    prompt="Explain again.",
    model_answer={"summary": "S", "key_points": ["three"]},
)


class MeetingGrader(FakeGrader):
    """Grades only once `parties` calls are in flight together, so sequential grading would
    time out."""

    def __init__(self, parties: int) -> None:
        super().__init__()
        self.barrier = threading.Barrier(parties, timeout=5)

    def grade(self, prompt: str, model_answer: Any, answer: str) -> Grade:
        self.barrier.wait()
        return super().grade(prompt, model_answer, answer)


def test_mark_all_grades_the_written_answers_at_the_same_time() -> None:
    grader = MeetingGrader(2)
    responses = {"q-mc": "a", "q-w": "The right idea.", "q-w2": "Hmm."}

    marked = mark_all([WRITTEN, MULTIPLE_CHOICE, WRITTEN_2], responses, grader)

    assert list(marked) == ["q-w", "q-mc", "q-w2"]
    assert marked == {
        "q-w": Marked(True, "Covers every key point."),
        "q-mc": Marked(correct=True),
        "q-w2": Marked(False, "Missing: three."),
    }


def test_mark_all_refuses_a_bad_choice_before_any_grading() -> None:
    grader = FakeGrader()
    with pytest.raises(NotAChoice):
        mark_all([WRITTEN, MULTIPLE_CHOICE, WRITTEN_2], {"q-mc": "z", "q-w": "x"}, grader)
    assert grader.calls == []


def test_mark_all_raises_when_any_parallel_grading_fails() -> None:
    grader = FakeGrader()
    grader.failing = True
    with pytest.raises(GradingFailed):
        mark_all([WRITTEN, WRITTEN_2], {"q-w": "The right idea.", "q-w2": "Also right."}, grader)
