"""The Lesson Quiz rules as plain functions: scoring against the Pass Mark, and drawing Questions
from a Question Bank (#6), and composing a Lesson Quiz of both Question types (#7)."""

import random
from collections import Counter

import pytest

from app.quiz import QUIZ_COMPOSITION, BankQuestion, draw_questions, draw_quiz, score

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


# --- Composing a Lesson Quiz (#7) ------------------------------------------------------------


def typed(mc: int, written: int) -> list[BankQuestion]:
    """A bank with `mc` multiple-choice Questions (m1, m2, ...) and `written` written ones (w1,
    ...), each on its own Concept."""
    return [BankQuestion(f"m{n}", f"cm{n}") for n in range(1, mc + 1)] + [
        BankQuestion(f"w{n}", f"cw{n}", "written") for n in range(1, written + 1)
    ]


def test_a_lesson_quiz_asks_four_multiple_choice_then_two_written() -> None:
    assert QUIZ_COMPOSITION == {"multiple_choice": 4, "written": 2}
    for seed in range(20):
        drawn = draw_quiz(typed(6, 3), random.Random(seed))
        assert [q[0] for q in drawn] == list("mmmmww"), drawn
        assert len(set(drawn)) == 6


def test_a_bank_short_of_written_questions_fills_up_with_multiple_choice() -> None:
    assert [q[0] for q in draw_quiz(typed(6, 1), random.Random(0))] == list("mmmmmw")
    assert sorted(draw_quiz(typed(6, 0), random.Random(0))) == [f"m{n}" for n in range(1, 7)]


def test_a_bank_short_of_multiple_choice_fills_up_with_written() -> None:
    assert [q[0] for q in draw_quiz(typed(2, 5), random.Random(0))] == list("mmwwww")


def test_a_small_bank_gives_every_question() -> None:
    assert sorted(draw_quiz(typed(2, 1), random.Random(0))) == ["m1", "m2", "w1"]
