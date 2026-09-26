"""`marking.mark`: one answer to one Question, marked the same way wherever it is asked (Lesson
Quiz now; Retakes and Review Rounds call it too). No database: Questions are plain objects."""

import pytest

from app.marking import AnswerTooLong, GradingFailed, Marked, NotAChoice, mark
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
