"""The Daily Review rules (#9, #10): which calendar day a Review Round belongs to, when a round
becomes a Pending Review Round, when Rounds 2 and 3 open, which Questions carry over from a day
with rounds left unfinished, when a Missed Question leaves the rotation, and which Questions a
round asks. Plain functions with a fake clock (`now`) and a seeded random source; the API is
tested in test_daily_review.py."""

import random
from datetime import UTC, date, datetime, timedelta

from app.review import (
    RoundSources,
    carried_over,
    in_rotation,
    next_round_opens_at,
    pick_round_questions,
    review_day,
    round_state,
)

OPENED = datetime(2026, 9, 26, 4, 0, tzinfo=UTC)


# --- The review day ---------------------------------------------------------------------------


def test_the_review_day_turns_at_midnight_in_dhaka_not_at_midnight_utc() -> None:
    # Midnight in Dhaka (UTC+6) is 18:00 UTC.
    before = datetime(2026, 9, 26, 17, 59, 59, tzinfo=UTC)
    assert review_day("Asia/Dhaka", before) == date(2026, 9, 26)
    assert review_day("Asia/Dhaka", before + timedelta(seconds=1)) == date(2026, 9, 27)


def test_the_review_day_is_still_yesterday_west_of_utc() -> None:
    now = datetime(2026, 9, 27, 7, 59, tzinfo=UTC)  # 23:59 in UTC-8 (Pacific standard time)

    assert review_day("Etc/GMT+8", now) == date(2026, 9, 26)
    assert review_day("Etc/GMT+8", now + timedelta(minutes=1)) == date(2026, 9, 27)


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

DAY = date(2026, 9, 26)  # in Dhaka (UTC+6), from 25 Sep 18:00 UTC to 26 Sep 18:00 UTC


def test_the_next_round_opens_four_hours_after_the_previous_one_is_finished() -> None:
    finished = datetime(2026, 9, 26, 4, 30, tzinfo=UTC)

    assert next_round_opens_at([finished], "Asia/Dhaka", DAY) == finished + timedelta(hours=4)
    assert next_round_opens_at([OPENED, finished], "Asia/Dhaka", DAY) == finished + timedelta(
        hours=4
    )


def test_no_round_opens_while_the_previous_one_is_unfinished() -> None:
    assert next_round_opens_at([None], "Asia/Dhaka", DAY) is None
    assert next_round_opens_at([OPENED, None], "Asia/Dhaka", DAY) is None


def test_a_day_never_has_more_than_three_rounds() -> None:
    assert next_round_opens_at([OPENED, OPENED, OPENED], "Asia/Dhaka", DAY) is None


def test_round_1_is_not_opened_by_this_rule() -> None:
    # Round 1 opens on the day's first use, not four hours after anything.
    assert next_round_opens_at([], "Asia/Dhaka", DAY) is None


def test_no_round_opens_once_its_opening_time_falls_on_the_next_day() -> None:
    # Finished at 19:59:59 in Dhaka: the next round opens at 23:59:59. At 20:00, it would open
    # at midnight, on the next day, whose Round 1 opens on its first use instead.
    last_in_day = datetime(2026, 9, 26, 13, 59, 59, tzinfo=UTC)
    too_late = datetime(2026, 9, 26, 14, 0, tzinfo=UTC)

    assert next_round_opens_at([last_in_day], "Asia/Dhaka", DAY) == last_in_day + timedelta(hours=4)
    assert next_round_opens_at([too_late], "Asia/Dhaka", DAY) is None


# --- Carry-over -------------------------------------------------------------------------------


def test_the_unanswered_questions_of_unfinished_rounds_carry_over_in_the_order_asked() -> None:
    round_2 = (["a", "b", "c", "d"], {"b"})
    round_3 = (["e", "a", "f"], set[str]())

    assert carried_over([round_2, round_3]) == ["a", "c", "d", "e", "f"]


def test_nothing_carries_over_from_rounds_answered_in_full() -> None:
    assert carried_over([(["a", "b"], {"a", "b"})]) == []
    assert carried_over([]) == []


# --- Leaving the rotation ---------------------------------------------------------------------

MISSED = datetime(2026, 9, 26, 4, 0, tzinfo=UTC)  # 10:00 in Dhaka on the 26th


def days_later(days: int, hours: float = 0) -> datetime:
    return MISSED + timedelta(days=days, hours=hours)


def test_a_missed_question_stays_in_the_rotation_until_correct_on_three_different_days() -> None:
    assert in_rotation(MISSED, [], "Asia/Dhaka")
    assert in_rotation(MISSED, [days_later(1), days_later(2)], "Asia/Dhaka")
    assert not in_rotation(MISSED, [days_later(1), days_later(2), days_later(3)], "Asia/Dhaka")


def test_correct_answers_on_one_day_count_as_one_day() -> None:
    same_day = [days_later(1), days_later(1, hours=4), days_later(1, hours=7)]

    assert in_rotation(MISSED, same_day, "Asia/Dhaka")
    assert not in_rotation(MISSED, [*same_day, days_later(2), days_later(3)], "Asia/Dhaka")


def test_the_day_of_the_miss_counts_for_a_correct_answer_given_after_it() -> None:
    later_that_day = MISSED + timedelta(hours=5)

    assert not in_rotation(MISSED, [later_that_day, days_later(1), days_later(2)], "Asia/Dhaka")


def test_days_are_counted_in_the_learner_s_time_zone() -> None:
    # 17:00 and 19:00 UTC on the 26th: one day in UTC, but 23:00 on the 26th and 01:00 on the
    # 27th in Dhaka.
    evening = datetime(2026, 9, 26, 17, 0, tzinfo=UTC)
    after_midnight = datetime(2026, 9, 26, 19, 0, tzinfo=UTC)
    correct = [evening, after_midnight, days_later(2)]

    assert not in_rotation(MISSED, correct, "Asia/Dhaka")
    assert in_rotation(MISSED, correct, "UTC")


def test_correct_answers_before_a_later_miss_do_not_count() -> None:
    missed_again = days_later(3)
    before = [days_later(0, hours=5), days_later(1), days_later(2)]

    assert in_rotation(missed_again, before, "Asia/Dhaka")
    assert in_rotation(missed_again, [*before, days_later(4), days_later(5)], "Asia/Dhaka")
    assert not in_rotation(
        missed_again, [*before, days_later(4), days_later(5), days_later(6)], "Asia/Dhaka"
    )


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
