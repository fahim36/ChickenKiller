"""The Lesson Quiz rules: the Pass Mark, scoring, and drawing Questions from a Question Bank.

Plain functions with no database or HTTP, tested directly (tests/test_lesson_quiz_rules.py).
Randomness is passed in (`rng`), so a test can seed it. `app/quizzes.py` stores attempts and
answers and calls these.
"""

import random
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple

PASS_MARK = Fraction(80, 100)
"""The minimum score a Lesson Quiz (or Placement Quiz) needs: 80%, compared exactly."""

QUIZ_SIZE = 6
"""Questions in a Lesson Quiz. #7 makes them four multiple choice and two written."""


@dataclass(frozen=True)
class Score:
    correct: int
    total: int

    @property
    def percent(self) -> int:
        """The score as a whole percentage, rounded half up (5 of 6 is 83, 4 of 6 is 67). For
        display only: `passed` compares the exact fraction."""
        if self.total == 0:
            return 0
        return int(Fraction(self.correct * 100, self.total) + Fraction(1, 2))

    @property
    def passed(self) -> bool:
        return self.total > 0 and Fraction(self.correct, self.total) >= PASS_MARK


def score(results: Iterable[bool | None]) -> Score:
    """Score a quiz from each Question's result. Only `True` counts: a wrong answer (`False`)
    and an unanswered Question (`None`) are both Missed Questions."""
    results = list(results)
    return Score(correct=sum(1 for r in results if r is True), total=len(results))


class BankQuestion(NamedTuple):
    """What drawing needs to know about a Question of the Question Bank."""

    id: str
    concept: str


def draw_questions(
    bank: Sequence[BankQuestion], rng: random.Random, size: int = QUIZ_SIZE
) -> list[str]:
    """Draw `size` distinct Questions (their permanent IDs) for a quiz, in the order they are
    asked.

    Concepts are covered as evenly as possible: no Concept is used twice while an unused one
    remains, and so on for a third use. A bank with fewer than `size` Questions gives them all.
    The caller picks which Questions may be drawn (#6: multiple choice only).
    """
    by_concept: dict[str, list[str]] = {}
    for question in bank:
        by_concept.setdefault(question.concept, []).append(question.id)
    queues = list(by_concept.values())
    for queue in queues:
        rng.shuffle(queue)
    rng.shuffle(queues)

    drawn: list[str] = []
    while len(drawn) < size and any(queues):
        for queue in queues:
            if queue and len(drawn) < size:
                drawn.append(queue.pop())
    rng.shuffle(drawn)
    return drawn
