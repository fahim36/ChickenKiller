"""The Lesson Quiz rules as plain functions: scoring against the Pass Mark, and drawing Questions
from a Question Bank (#6)."""

import random
from collections import Counter

import pytest

from app.quiz import BankQuestion, draw_questions, score

# --- Scoring ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("results", "percent", "passed"),
    [
        ([True] * 6, 100, True),
        ([True] * 5 + [False], 83, True),
        ([True] * 4 + [False] * 2, 67, False),
        ([False] * 6, 0, False),
    ],
)
def test_a_six_question_quiz_passes_at_five_correct(
    results: list[bool], percent: int, passed: bool
) -> None:
    result = score(results)
    assert (result.correct, result.total, result.percent, result.passed) == (
        sum(results),
        6,
        percent,
        passed,
    )


def test_the_pass_mark_is_eighty_percent_exactly() -> None:
    assert score([True] * 4 + [False]).passed  # 80%
    assert not score([True] * 79 + [False] * 21).passed  # 79%


def test_an_unanswered_question_is_missed() -> None:
    result = score([True, True, True, True, None, None])
    assert (result.correct, result.total, result.passed) == (4, 6, False)


def test_an_empty_quiz_never_passes() -> None:
    assert not score([]).passed


# --- Drawing ---------------------------------------------------------------------------------


def bank(*concepts: str) -> list[BankQuestion]:
    """One Question per entry, named after its Concept and position: `a1`, `a2`, `b1`, ..."""
    seen: Counter[str] = Counter()
    questions = []
    for concept in concepts:
        seen[concept] += 1
        questions.append(BankQuestion(id=f"{concept}{seen[concept]}", concept=concept))
    return questions


def test_draws_six_distinct_questions_from_the_bank() -> None:
    questions = bank(*"aabbccddee")
    drawn = draw_questions(questions, random.Random(1))
    assert len(drawn) == 6
    assert len(set(drawn)) == 6
    assert set(drawn) <= {q.id for q in questions}


def test_never_repeats_a_concept_while_an_unused_one_remains() -> None:
    questions = bank(*"aaaaaabbcdef")
    for seed in range(50):
        drawn = draw_questions(questions, random.Random(seed))
        concepts = Counter(q[0] for q in drawn)
        assert concepts == Counter("abcdef"), drawn


def test_spreads_repeats_across_concepts_once_every_concept_is_used() -> None:
    questions = bank(*"aaaabbbbcccc")
    for seed in range(20):
        drawn = draw_questions(questions, random.Random(seed))
        assert sorted(Counter(q[0] for q in drawn).values()) == [2, 2, 2]


def test_the_same_seed_draws_the_same_quiz_and_others_vary() -> None:
    questions = bank(*"aabbccddeeff")
    first = draw_questions(questions, random.Random(7))
    assert draw_questions(questions, random.Random(7)) == first
    assert {tuple(draw_questions(questions, random.Random(s))) for s in range(20)} != {tuple(first)}


def test_a_bank_with_fewer_than_six_questions_gives_them_all() -> None:
    questions = bank(*"aabbc")
    assert sorted(draw_questions(questions, random.Random(0))) == ["a1", "a2", "b1", "b2", "c1"]
