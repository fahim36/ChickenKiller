"""The Lesson Quiz rules as plain functions: scoring against the Pass Mark, drawing Questions
from a Question Bank (#6), skipping the Questions the Learner has seen (#6), composing a Lesson
Quiz of both Question types (#7), and a fresh quiz and Retake siblings (#8)."""

import random
from collections import Counter

import pytest

from app.quiz import (
    QUIZ_COMPOSITION,
    BankQuestion,
    draw_questions,
    draw_quiz,
    pick_sibling,
    score,
)

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


# --- Skipping seen Questions (#6) ------------------------------------------------------------


def test_a_quiz_skips_the_questions_the_learner_has_seen_when_the_bank_allows() -> None:
    questions = bank(*"aaabbbccc")
    for seed in range(30):
        drawn = draw_questions(questions, random.Random(seed), seen=["a1", "b1", "c1"])
        assert set(drawn) == {"a2", "a3", "b2", "b3", "c2", "c3"}, drawn


def test_an_unseen_question_comes_before_covering_another_concept() -> None:
    for seed in range(30):
        drawn = draw_questions(bank(*"aab"), random.Random(seed), size=2, seen=["b1"])
        assert sorted(drawn) == ["a1", "a2"], drawn


def test_a_quiz_draws_seen_questions_only_as_far_as_the_bank_runs_short() -> None:
    questions = bank(*"aabbcc")
    for seed in range(30):
        drawn = set(draw_questions(questions, random.Random(seed), size=4, seen=["a1", "b1", "c1"]))
        assert {"a2", "b2", "c2"} <= drawn, drawn
        assert len(drawn) == 4


def test_a_lesson_quiz_short_of_unseen_questions_of_a_type_keeps_four_and_two() -> None:
    seen = ["m1", "m2", "m3", "m4", "w1"]
    for seed in range(20):
        drawn = draw_quiz(typed(6, 3), random.Random(seed), seen=seen)
        assert [q[0] for q in drawn] == list("mmmmww"), drawn
        assert {"m5", "m6"} <= set(drawn[:4]), drawn
        assert sorted(drawn[4:]) == ["w2", "w3"], drawn


def test_a_fresh_quiz_repeats_other_seen_questions_before_the_previous_attempts() -> None:
    previous = ["m1", "m2", "m3", "m4", "w1", "w2"]
    seen = [*previous, "m5", "m6"]  # m5 and m6 were answered somewhere else
    for seed in range(20):
        drawn = draw_quiz(typed(8, 2), random.Random(seed), avoid=previous, seen=seen)
        assert sorted(drawn[:4]) == ["m5", "m6", "m7", "m8"], drawn
        assert sorted(drawn[4:]) == ["w1", "w2"], drawn


# --- A fresh quiz after one below the Pass Mark (#8) -----------------------------------------


def test_a_fresh_quiz_avoids_the_previous_attempts_questions_when_the_bank_allows() -> None:
    questions = bank(*"aaabbbcccddd")
    previous = ["a1", "b1", "c1", "d1", "a2", "b2"]
    for seed in range(30):
        drawn = draw_questions(questions, random.Random(seed), avoid=previous)
        assert set(drawn) == {"a3", "b3", "c2", "c3", "d2", "d3"}, drawn


def test_a_fresh_quiz_repeats_only_as_many_previous_questions_as_it_must() -> None:
    questions = bank(*"aabbccdd")
    previous = ["a1", "b1", "c1", "d1", "a2", "b2"]
    for seed in range(30):
        drawn = set(draw_questions(questions, random.Random(seed), avoid=previous))
        assert len(drawn) == 6
        assert {"c2", "d2"} <= drawn  # the only new ones
        assert len(drawn & set(previous)) == 4


def test_the_repeated_questions_still_spread_across_concepts() -> None:
    questions = bank(*"aaabbbcccddd")
    previous = ["a1", "a2", "a3", "b1", "b2", "b3", "c1", "c2", "c3", "d1"]
    for seed in range(30):
        drawn = draw_questions(questions, random.Random(seed), avoid=previous)
        assert {"d2", "d3"} <= set(drawn)
        assert "d1" not in drawn, drawn  # Concept d is used twice already
        assert sorted(Counter(q[0] for q in drawn).values()) == [1, 1, 2, 2], drawn


# --- Retake siblings (#8) --------------------------------------------------------------------


def test_a_retake_uses_a_sibling_never_the_original() -> None:
    concept = ["a1", "a2", "a3", "a4"]
    for seed in range(30):
        assert pick_sibling(concept, "a2", [], random.Random(seed)) in {"a1", "a3", "a4"}


def test_another_retake_uses_an_unused_sibling_while_one_remains() -> None:
    concept = ["a1", "a2", "a3", "a4"]
    for seed in range(30):
        rng = random.Random(seed)
        asked: list[str] = []
        for _ in range(3):
            sibling = pick_sibling(concept, "a2", asked, rng)
            assert sibling is not None
            asked.append(sibling)
        assert sorted(asked) == ["a1", "a3", "a4"]


def test_once_every_sibling_is_used_they_cycle_without_asking_one_twice_in_a_row() -> None:
    concept = ["a1", "a2", "a3"]
    for seed in range(30):
        rng = random.Random(seed)
        asked = ["a1", "a3"]
        for _ in range(6):
            sibling = pick_sibling(concept, "a2", asked, rng)
            assert sibling in {"a1", "a3"}
            assert sibling != asked[-1]
            asked.append(sibling)


def test_a_concept_with_one_sibling_retakes_it_again_rather_than_the_original() -> None:
    assert pick_sibling(["a1", "a2"], "a1", ["a2", "a2"], random.Random(0)) == "a2"


def test_a_concept_with_no_sibling_has_no_retake() -> None:
    assert pick_sibling(["a1"], "a1", [], random.Random(0)) is None


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


def test_a_fresh_lesson_quiz_avoids_previous_questions_of_each_type() -> None:
    previous = ["m1", "m2", "m3", "m4", "w1", "w2"]
    for seed in range(20):
        drawn = draw_quiz(typed(8, 3), random.Random(seed), avoid=previous)
        assert sorted(drawn[:4]) == ["m5", "m6", "m7", "m8"], drawn
        assert "w3" in drawn[4:]  # the only unused written one, and one repeat it can't avoid
        assert len(set(drawn[4:]) & {"w1", "w2"}) == 1, drawn
