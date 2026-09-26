"""The Lesson Quiz rules: the Pass Mark, scoring, drawing Questions from a Question Bank, and
picking a Retake's sibling Question.

Plain functions with no database or HTTP, tested directly (tests/test_lesson_quiz_rules.py).
Randomness is passed in (`rng`), so a test can seed it. `app/quizzes.py` and `app/retakes.py`
store attempts, Retakes and answers and call these.
"""

import random
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
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
    bank: Sequence[BankQuestion],
    rng: random.Random,
    size: int = QUIZ_SIZE,
    avoid: Collection[str] = (),
) -> list[str]:
    """Draw `size` distinct Questions (their permanent IDs) for a quiz, in the order they are
    asked.

    - Questions in `avoid` (a previous attempt's, #8) are drawn only once every other Question
      is used, so a fresh quiz repeats as few of them as the bank allows.
    - Within that, Concepts are covered as evenly as possible: no Concept is used twice while
      an unused one remains, and so on for a third use.

    A bank with fewer than `size` Questions gives them all. The caller picks which Questions may
    be drawn (#6: multiple choice only).
    """
    avoided = set(avoid)
    pool = list(bank)
    rng.shuffle(pool)
    uses: Counter[str] = Counter()
    drawn: list[str] = []
    while pool and len(drawn) < size:
        # `min` keeps the first of equals, so the shuffle breaks ties at random.
        best = min(pool, key=lambda q: (q.id in avoided, uses[q.concept]))
        pool.remove(best)
        uses[best.concept] += 1
        drawn.append(best.id)
    rng.shuffle(drawn)
    return drawn


def pick_sibling(
    concept_questions: Sequence[str],
    original: str,
    asked: Sequence[str],
    rng: random.Random,
) -> str | None:
    """The Question (permanent ID) for the next Retake of the Missed Question `original`.

    `concept_questions` are the Questions on its Concept that a Retake may ask (the original may
    be among them); `asked` are the siblings already asked for this Missed Question, in order.

    - Never the original. None if the Concept has no other Question (the content check requires
      two per Concept, so that means no Question of a type Retakes can ask yet).
    - An unused sibling while one remains; once all are used they cycle again, never asking the
      same one twice in a row. A Concept with exactly two Questions has one sibling, so every
      Retake of it asks that sibling again.
    """
    siblings = sorted(set(concept_questions) - {original})
    if not siblings:
        return None
    unused = [q for q in siblings if q not in asked]
    if unused:
        return rng.choice(unused)
    others = [q for q in siblings if not asked or q != asked[-1]]
    return rng.choice(others or siblings)
