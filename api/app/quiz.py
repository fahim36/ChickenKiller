"""The Lesson Quiz rules: the Pass Mark, scoring, drawing Questions from a Question Bank, and
picking a Retake's sibling Question.

Plain functions with no database or HTTP, tested directly (tests/test_lesson_quiz_rules.py).
Randomness is passed in (`rng`), so a test can seed it. `app/quizzes.py` and `app/retakes.py`
store attempts, Retakes and answers and call these.
"""

import random
from collections import Counter
from collections.abc import Collection, Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
from typing import NamedTuple

PASS_MARK = Fraction(80, 100)
"""The minimum score a Lesson Quiz (or Placement Quiz) needs: 80%, compared exactly."""

QUIZ_COMPOSITION: dict[str, int] = {"multiple_choice": 4, "multiple_select": 2}
"""How many Questions of each type a Lesson Quiz asks, in the order they are asked: four
multiple choice, then two multiple select (ADR-0008). See `draw_quiz` for a bank short of one
type."""

QUIZ_STAND_INS: dict[str, str] = {"multiple_select": "written"}
"""A legacy type that fills a type's slots when the bank has too few of that type: a Lesson
whose multiple-select Questions aren't written yet still asks its written ones (ADR-0008)."""

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
    bank: Sequence[BankQuestion],
    rng: random.Random,
    size: int = QUIZ_SIZE,
    avoid: Collection[str] = (),
    seen: Collection[str] = (),
) -> list[str]:
    """Draw `size` distinct Questions (their permanent IDs) for a quiz, in the order they are
    asked.

    - Questions in `avoid` (a previous attempt's, #8) are drawn only once every other Question
      is used, so a fresh quiz repeats as few of them as the bank allows.
    - Next, Questions in `seen` (the Learner has answered them anywhere, #6) are drawn only
      once every unseen one is used.
    - Within that, Concepts are covered as evenly as possible: no Concept is used twice while
      an unused one remains, and so on for a third use. An unseen Question still comes before
      a seen one on an unused Concept.

    A bank with fewer than `size` Questions gives them all. A Lesson Quiz draws through
    `draw_quiz`, which calls this once per Question type.
    """
    avoided, seen_ids = set(avoid), set(seen)
    pool = list(bank)
    rng.shuffle(pool)
    uses: Counter[str] = Counter()
    drawn: list[str] = []
    while pool and len(drawn) < size:
        # `min` keeps the first of equals, so the shuffle breaks ties at random.
        best = min(pool, key=lambda q: (q.id in avoided, q.id in seen_ids, uses[q.concept]))
        pool.remove(best)
        uses[best.concept] += 1
        drawn.append(best.id)
    rng.shuffle(drawn)
    return drawn


def draw_quiz(
    bank: Sequence[BankQuestion],
    rng: random.Random,
    composition: Mapping[str, int] = QUIZ_COMPOSITION,
    avoid: Collection[str] = (),
    seen: Collection[str] = (),
    stand_ins: Mapping[str, str] = QUIZ_STAND_INS,
) -> list[str]:
    """Draw a Lesson Quiz (permanent IDs, in the order they are asked): each type's share of
    `composition` drawn with `draw_questions`, the types in `composition` order.

    A type with too few Questions in the bank first takes its stand-in's (`stand_ins`: legacy
    written Questions fill the multiple-select slots), and only then is the shortfall made up
    from the bank's other Questions (so a bank with neither gives six multiple choice). A bank
    with fewer Questions than the quiz size gives them all. Questions in
    `avoid` (a previous attempt's, #8), then those in `seen` (#6), are drawn only where a type
    has too few others: a type short of unseen Questions repeats seen ones of its own type
    before borrowing another type's, so the quiz keeps its mix.
    """
    by_type: dict[str, list[BankQuestion]] = {t: [] for t in composition}
    by_type.update({s: [] for t, s in stand_ins.items() if t in composition})
    for question in bank:
        if question.type in by_type:
            by_type[question.type].append(question)
    drawn = {t: draw_questions(by_type[t], rng, n, avoid, seen) for t, n in composition.items()}
    for kind, stand_in in stand_ins.items():
        short = composition.get(kind, 0) - len(drawn.get(kind, []))
        if short > 0 and stand_in not in composition:
            drawn[kind] += draw_questions(by_type[stand_in], rng, short, avoid, seen)

    shortfall = sum(composition.values()) - sum(len(ids) for ids in drawn.values())
    if shortfall > 0:
        taken = {qid for ids in drawn.values() for qid in ids}
        rest = [q for qs in by_type.values() for q in qs if q.id not in taken]
        extra = set(draw_questions(rest, rng, shortfall, avoid, seen))
        for question in rest:
            if question.id in extra:
                drawn[_slot(question.type, composition, stand_ins)].append(question.id)
    return [qid for t in composition for qid in drawn[t]]


def _slot(kind: str, composition: Mapping[str, int], stand_ins: Mapping[str, str]) -> str:
    """The type whose slots a Question of type `kind` is asked in: its own, or the type it
    stands in for."""
    if kind in composition:
        return kind
    return next(t for t, s in stand_ins.items() if s == kind)


def pick_sibling(
    concept_questions: Sequence[str],
    original: str,
    asked: Sequence[str],
    rng: random.Random,
) -> str | None:
    """The Question (permanent ID) for the next Retake of the Missed Question `original`.

    `concept_questions` are the Questions on its Concept (the original may be among them);
    `asked` are the siblings already asked for this Missed Question, in order.

    - Never the original. None only if the Concept has no other Question, which the content
      check rules out (two Questions per Concept).
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
