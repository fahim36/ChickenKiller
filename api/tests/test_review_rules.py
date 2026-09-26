"""The Daily Review rules (#9): which calendar day a Review Round belongs to, when a round
becomes a Pending Review Round, and which Questions a round asks. Plain functions with a fake
clock (`now`) and a seeded random source; the API is tested in test_daily_review.py."""

import random
from datetime import UTC, date, datetime, timedelta

from app.review import pick_round_questions, review_day, round_state

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


# --- Picking a round's Questions ----------------------------------------------------------------

COMPLETED = [f"w01-l01-q{n:02}" for n in range(1, 21)]


def test_missed_questions_come_first_in_the_order_they_were_missed() -> None:
    picked = pick_round_questions(["x3", "x1", "x2"], COMPLETED, random.Random(1))

    assert picked[:3] == ["x3", "x1", "x2"]


def test_questions_from_completed_lessons_fill_the_rest_up_to_ten() -> None:
    picked = pick_round_questions(["x1", "x2"], COMPLETED, random.Random(1))

    assert len(picked) == 10
    assert set(picked[2:]) < set(COMPLETED)


def test_the_fill_is_random_and_follows_the_random_source() -> None:
    first = pick_round_questions([], COMPLETED, random.Random(1))

    assert first == pick_round_questions([], COMPLETED, random.Random(1))
    assert any(
        pick_round_questions([], COMPLETED, random.Random(seed)) != first for seed in range(2, 6)
    )


def test_a_round_never_asks_a_question_twice() -> None:
    # A Missed Question is usually also a Question of a Completed Lesson.
    missed = ["w01-l01-q01", "w01-l01-q02", "w01-l01-q01"]
    picked = pick_round_questions(missed, COMPLETED[:9], random.Random(1))

    assert len(picked) == len(set(picked)) == 9
    assert picked[:2] == ["w01-l01-q01", "w01-l01-q02"]


def test_more_than_ten_missed_questions_fill_the_round_first_missed_first() -> None:
    missed = [f"m{n:02}" for n in range(12)]

    assert pick_round_questions(missed, COMPLETED, random.Random(1)) == missed[:10]


def test_a_round_holds_what_there_is_when_there_are_fewer_than_ten() -> None:
    assert sorted(pick_round_questions([], COMPLETED[:4], random.Random(1))) == COMPLETED[:4]
    assert pick_round_questions([], [], random.Random(1)) == []
