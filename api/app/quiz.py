"""The Lesson Quiz rules: the Pass Mark, scoring, and drawing Questions from a Question Bank.

Plain functions with no database or HTTP, tested directly (tests/test_lesson_quiz_rules.py).
Randomness is passed in (`rng`), so a test can seed it. `app/quizzes.py` stores attempts and
answers and calls these.
"""

import random
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple

PASS_MARK = Fraction(80, 100)
"""The minimum score a Lesson Quiz (or Placement Quiz) needs: 80%, compared exactly."""

QUIZ_COMPOSITION: dict[str, int] = {"multiple_choice": 4, "written": 2}
"""How many Questions of each type a Lesson Quiz asks, in the order they are asked: four
multiple choice, then two written. See `draw_quiz` for a bank short of one type."""

QUIZ_SIZE = sum(QUIZ_COMPOSITION.values())
"""Questions in a Lesson Quiz: six."""


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
    type: str = "multiple_choice"


def draw_questions(
    bank: Sequence[BankQuestion], rng: random.Random, size: int = QUIZ_SIZE
) -> list[str]:
    """Draw `size` distinct Questions (their permanent IDs) for a quiz, in the order they are
    asked.

    Concepts are covered as evenly as possible: no Concept is used twice while an unused one
    remains, and so on for a third use. A bank with fewer than `size` Questions gives them all.
    A Lesson Quiz draws through `draw_quiz`, which calls this once per Question type.
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


def draw_quiz(
    bank: Sequence[BankQuestion],
    rng: random.Random,
    composition: Mapping[str, int] = QUIZ_COMPOSITION,
) -> list[str]:
    """Draw a Lesson Quiz (permanent IDs, in the order they are asked): each type's share of
    `composition` drawn with `draw_questions`, the types in `composition` order.

    A bank short of one type still gives a full-size quiz when it can: the shortfall is made up
    from the bank's other Questions (so a bank with no written Questions gives six multiple
    choice). A bank with fewer Questions than the quiz size gives them all.
    """
    by_type: dict[str, list[BankQuestion]] = {t: [] for t in composition}
    for question in bank:
        if question.type in by_type:
            by_type[question.type].append(question)
    drawn = {t: draw_questions(by_type[t], rng, n) for t, n in composition.items()}

    shortfall = sum(composition.values()) - sum(len(ids) for ids in drawn.values())
    if shortfall > 0:
        taken = {qid for ids in drawn.values() for qid in ids}
        rest = [q for qs in by_type.values() for q in qs if q.id not in taken]
        extra = set(draw_questions(rest, rng, shortfall))
        for question in rest:
            if question.id in extra:
                drawn[question.type].append(question.id)
    return [qid for t in composition for qid in drawn[t]]
