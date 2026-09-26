"""The Daily Review rules (#9, #10): which Day (UTC) a Review Round belongs to, when a round
becomes a Pending Review Round, when Rounds 2 and 3 open, which Questions carry over from a day
with rounds left unfinished, when a Missed Question leaves the rotation, and which Questions a
round asks, and the Streak (#11). Plain functions with a fake clock (`now`) and a seeded random
source; the API is tested in test_daily_review.py and test_streak.py."""

import random
from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from app.review import (
    DayOutcome,
    RoundSources,
    carried_over,
    day_outcome,
    in_rotation,
    next_round_opens_at,
    pick_round_questions,
    review_day,
    round_state,
    streak,
)

OPENED = datetime(2026, 9, 26, 4, 0, tzinfo=UTC)


# --- The review day ---------------------------------------------------------------------------


def test_the_review_day_turns_at_midnight_utc() -> None:
    before = datetime(2026, 9, 26, 23, 59, 59, tzinfo=UTC)
    assert review_day(before) == date(2026, 9, 26)
    assert review_day(before + timedelta(seconds=1)) == date(2026, 9, 27)


def test_the_review_day_is_the_utc_day_whatever_zone_the_clock_is_read_in() -> None:
    # 01:00 on the 27th in Dhaka (UTC+6) is still the 26th in UTC.
    dhaka = timezone(timedelta(hours=6))

    assert review_day(datetime(2026, 9, 27, 1, 0, tzinfo=dhaka)) == date(2026, 9, 26)


# --- Round state ------------------------------------------------------------------------------


def test_a_round_is_optional_for_its_first_two_hours() -> None:
    assert round_state(OPENED, None, OPENED) == "optional"
    assert round_state(OPENED, None, OPENED + timedelta(hours=1, minutes=59, seconds=59)) == (
        "optional"
    )


def test_a_round_becomes_pending_exactly_two_hours_after_it_opened() -> None:
    assert round_state(OPENED, None, OPENED + timedelta(hours=2)) == "pending"
    assert round_state(OPENED, None, OPENED + timedelta(hours=9)) == "pending"


def test_a_finished_round_is_finished_whether_it_finished_in_time_or_late() -> None:
    in_time = OPENED + timedelta(minutes=30)
    late = OPENED + timedelta(hours=3)

    assert round_state(OPENED, in_time, OPENED + timedelta(hours=5)) == "finished"
    assert round_state(OPENED, late, late) == "finished"


# --- Rounds 2 and 3 ----------------------------------------------------------------------------

DAY = date(2026, 9, 26)


def test_the_next_round_opens_four_hours_after_the_previous_one_is_finished() -> None:
    finished = datetime(2026, 9, 26, 4, 30, tzinfo=UTC)

    assert next_round_opens_at([finished], DAY) == finished + timedelta(hours=4)
    assert next_round_opens_at([OPENED, finished], DAY) == finished + timedelta(hours=4)


def test_no_round_opens_while_the_previous_one_is_unfinished() -> None:
    assert next_round_opens_at([None], DAY) is None
    assert next_round_opens_at([OPENED, None], DAY) is None


def test_a_day_never_has_more_than_three_rounds() -> None:
    assert next_round_opens_at([OPENED, OPENED, OPENED], DAY) is None


def test_round_1_is_not_opened_by_this_rule() -> None:
    # Round 1 opens on the day's first use, not four hours after anything.
    assert next_round_opens_at([], DAY) is None


def test_no_round_opens_once_its_opening_time_falls_on_the_next_day() -> None:
    # Finished at 19:59:59: the next round opens at 23:59:59. At 20:00, it would open at
    # midnight, on the next day, whose Round 1 opens on its first use instead.
    last_in_day = datetime(2026, 9, 26, 19, 59, 59, tzinfo=UTC)
    too_late = datetime(2026, 9, 26, 20, 0, tzinfo=UTC)

    assert next_round_opens_at([last_in_day], DAY) == last_in_day + timedelta(hours=4)
    assert next_round_opens_at([too_late], DAY) is None


# --- Carry-over -------------------------------------------------------------------------------


def test_the_unanswered_questions_of_unfinished_rounds_carry_over_in_the_order_asked() -> None:
    round_2 = (["a", "b", "c", "d"], {"b"})
    round_3 = (["e", "a", "f"], set[str]())

    assert carried_over([round_2, round_3]) == ["a", "c", "d", "e", "f"]


def test_nothing_carries_over_from_rounds_answered_in_full() -> None:
    assert carried_over([(["a", "b"], {"a", "b"})]) == []
    assert carried_over([]) == []


# --- Leaving the rotation ---------------------------------------------------------------------

MISSED = datetime(2026, 9, 26, 4, 0, tzinfo=UTC)


def days_later(days: int, hours: float = 0) -> datetime:
    return MISSED + timedelta(days=days, hours=hours)


def test_a_missed_question_stays_in_the_rotation_until_correct_on_three_different_days() -> None:
    assert in_rotation(MISSED, [])
    assert in_rotation(MISSED, [days_later(1), days_later(2)])
    assert not in_rotation(MISSED, [days_later(1), days_later(2), days_later(3)])


def test_correct_answers_on_one_day_count_as_one_day() -> None:
    same_day = [days_later(1), days_later(1, hours=4), days_later(1, hours=7)]

    assert in_rotation(MISSED, same_day)
    assert not in_rotation(MISSED, [*same_day, days_later(2), days_later(3)])


def test_the_day_of_the_miss_counts_for_a_correct_answer_given_after_it() -> None:
    later_that_day = MISSED + timedelta(hours=5)

    assert not in_rotation(MISSED, [later_that_day, days_later(1), days_later(2)])


def test_correct_answers_before_a_later_miss_do_not_count() -> None:
    missed_again = days_later(3)
    before = [days_later(0, hours=5), days_later(1), days_later(2)]

    assert in_rotation(missed_again, before)
    assert in_rotation(missed_again, [*before, days_later(4), days_later(5)])
    assert not in_rotation(missed_again, [*before, days_later(4), days_later(5), days_later(6)])


# --- Picking a round's Questions ----------------------------------------------------------------

COMPLETED = [f"w01-l01-q{n:02}" for n in range(1, 21)]


def pick(missed: list[str], completed: list[str], rng: random.Random) -> list[str]:
    return pick_round_questions(RoundSources(missed=missed, completed=completed), rng)


def test_missed_questions_come_first_in_the_order_they_were_missed() -> None:
    picked = pick(["x3", "x1", "x2"], COMPLETED, random.Random(1))

    assert picked[:3] == ["x3", "x1", "x2"]


def test_questions_from_completed_lessons_fill_the_rest_up_to_ten() -> None:
    picked = pick(["x1", "x2"], COMPLETED, random.Random(1))

    assert len(picked) == 10
    assert set(picked[2:]) < set(COMPLETED)


def test_the_fill_is_random_and_follows_the_random_source() -> None:
    first = pick([], COMPLETED, random.Random(1))

    assert first == pick([], COMPLETED, random.Random(1))
    assert any(pick([], COMPLETED, random.Random(seed)) != first for seed in range(2, 6))


def test_a_round_never_asks_a_question_twice() -> None:
    # A Missed Question is usually also a Question of a Completed Lesson.
    missed = ["w01-l01-q01", "w01-l01-q02", "w01-l01-q01"]
    picked = pick(missed, COMPLETED[:9], random.Random(1))

    assert len(picked) == len(set(picked)) == 9
    assert picked[:2] == ["w01-l01-q01", "w01-l01-q02"]


def test_more_than_ten_missed_questions_fill_the_round_first_missed_first() -> None:
    missed = [f"m{n:02}" for n in range(12)]

    assert pick(missed, COMPLETED, random.Random(1)) == missed[:10]


def test_a_round_holds_what_there_is_when_there_are_fewer_than_ten() -> None:
    assert sorted(pick([], COMPLETED[:4], random.Random(1))) == COMPLETED[:4]
    assert pick([], [], random.Random(1)) == []


def test_the_sources_come_in_order_carried_over_then_missed_then_updated_then_the_fill() -> None:
    sources = RoundSources(
        carried_over=["c1", "c2"], missed=["m1", "c1"], updated=["u1"], completed=COMPLETED
    )

    picked = pick_round_questions(sources, random.Random(1))

    assert picked[:4] == ["c1", "c2", "m1", "u1"]
    assert len(picked) == 10
    assert set(picked[4:]) < set(COMPLETED)


def test_questions_asked_earlier_today_are_left_out() -> None:
    asked = {*COMPLETED[:11], "m1"}
    sources = RoundSources(missed=["m1", "m2"], completed=COMPLETED, asked_today=asked)

    picked = pick_round_questions(sources, random.Random(1))

    assert picked[0] == "m2"
    assert sorted(picked[1:]) == COMPLETED[11:]
    assert asked.isdisjoint(picked)


def test_with_too_few_questions_left_the_fill_repeats_some_asked_earlier_today() -> None:
    bank = COMPLETED[:8]
    sources = RoundSources(completed=bank, asked_today=set(bank[:6]))

    picked = pick_round_questions(sources, random.Random(1))

    assert sorted(picked[:2]) == bank[6:]
    assert sorted(picked) == bank


# --- The Streak -------------------------------------------------------------------------------

D1, D2, D3, D4, D5 = (date(2026, 9, d) for d in range(21, 26))
TODAY = date(2026, 9, 26)


def at(day: date, hour: int) -> datetime:
    """`hour` o'clock on `day`, in UTC."""
    return datetime(day.year, day.month, day.day, hour, tzinfo=UTC)


@pytest.mark.parametrize(
    ("finished_ats", "day", "outcome"),
    [
        # No round opened on a day the Learner used the app: nothing was owed.
        ([], D1, "nothing_owed"),
        ([], TODAY, "nothing_owed"),
        # All three rounds finished.
        ([at(D1, 1), at(D1, 6), at(D1, 11)], D1, "finished"),
        # Round 1 finished at 21:00: Round 2 would open after midnight, so the day is done.
        ([at(D1, 21)], D1, "finished"),
        ([at(TODAY, 21)], TODAY, "finished"),
        # A round left unfinished.
        ([at(D1, 8), None], D1, "unfinished"),
        # Round 2 came due at 12:00 while the Learner was away, so it was never stored.
        ([at(D1, 8)], D1, "unfinished"),
        # Today, still to finish: it isn't over yet.
        ([None], TODAY, "in_progress"),
        ([at(TODAY, 8)], TODAY, "in_progress"),
    ],
)
def test_a_day_s_outcome_follows_from_its_rounds(
    finished_ats: list[datetime | None], day: date, outcome: DayOutcome
) -> None:
    assert day_outcome(finished_ats, day, TODAY) == outcome


@pytest.mark.parametrize(
    ("days", "expected"),
    [
        ({}, 0),
        ({TODAY: "in_progress"}, 0),
        ({TODAY: "finished"}, 1),
        # Each finished day adds one; today, still in progress, doesn't break it yet.
        ({D3: "finished", D4: "finished", D5: "finished", TODAY: "in_progress"}, 3),
        ({D4: "finished", D5: "finished", TODAY: "finished"}, 3),
        # An unfinished day resets it to zero; finished days after it count again.
        ({D2: "finished", D3: "unfinished", TODAY: "in_progress"}, 0),
        ({D1: "finished", D2: "unfinished", D3: "finished", D4: "finished", D5: "finished"}, 3),
        # Nothing owed: neither extends nor breaks it.
        ({D3: "finished", D4: "nothing_owed", D5: "finished", TODAY: "nothing_owed"}, 2),
        ({D4: "nothing_owed", D5: "nothing_owed"}, 0),
        # A past day the Learner never used the app: its Daily Review wasn't finished.
        ({D1: "finished", D2: "finished", D4: "finished", D5: "finished", TODAY: "finished"}, 3),
        # Not having used the app yet today breaks nothing.
        ({D4: "finished", D5: "finished"}, 2),
    ],
)
def test_the_streak_counts_the_finished_days_since_the_last_unfinished_one(
    days: dict[date, DayOutcome], expected: int
) -> None:
    assert streak(days, TODAY) == expected
