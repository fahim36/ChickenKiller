"""The Review rules (app/review.py): the UTC Day, when a Missed Question leaves the queue, when a
spaced repeat is due, and the order of the queue. Plain functions: the day is passed in, so no
clock is needed here. Review over the API is tested in test_review.py."""

from datetime import UTC, date, datetime, timedelta, timezone

from app.review import (
    SET_SIZE,
    Missed,
    QuestionRef,
    Repeat,
    ReviewSources,
    in_queue,
    missed_is_due,
    queue,
    repeat_is_due,
    utc_day,
)

MISSED_AT = datetime(2026, 9, 26, 10, 0, tzinfo=UTC)
TODAY = date(2026, 9, 26)


def at(day: int, hour: int = 12) -> datetime:
    """`hour`:00 UTC on September `day`, 2026."""
    return datetime(2026, 9, day, hour, 0, tzinfo=UTC)


def ref(n: int, stack: str = "mini-stack") -> QuestionRef:
    return QuestionRef(stack, f"q{n:02}")


# --- The Day ---------------------------------------------------------------------------------


def test_the_day_turns_at_midnight_utc() -> None:
    assert utc_day(datetime(2026, 9, 26, 23, 59, 59, tzinfo=UTC)) == date(2026, 9, 26)
    assert utc_day(datetime(2026, 9, 27, 0, 0, tzinfo=UTC)) == date(2026, 9, 27)


def test_the_day_is_the_utc_day_whatever_zone_the_clock_is_read_in() -> None:
    dhaka = timezone(timedelta(hours=6))

    assert utc_day(datetime(2026, 9, 27, 5, 0, tzinfo=dhaka)) == date(2026, 9, 26)


# --- Leaving the queue: correct on three different Days ----------------------------------------


def test_a_missed_question_stays_in_queue_until_correct_on_three_different_days() -> None:
    assert in_queue(MISSED_AT, [at(27), at(28)])
    assert not in_queue(MISSED_AT, [at(27), at(28), at(29)])


def test_correct_answers_on_one_day_count_as_one_day() -> None:
    assert in_queue(MISSED_AT, [at(27, 9), at(27, 15), at(27, 23), at(28)])


def test_the_day_of_the_miss_counts_for_a_correct_answer_given_after_it() -> None:
    assert not in_queue(MISSED_AT, [at(26, 18), at(27), at(28)])


def test_correct_answers_before_a_later_miss_do_not_count() -> None:
    """A later miss (it is `last_missed_at`) starts the count again."""
    assert in_queue(at(29), [at(26, 11), at(27), at(28)])


def test_days_turn_at_midnight_utc_for_the_three_days_rule() -> None:
    """23:59 and 00:00 UTC are two Days, whatever the Learner's local time."""
    assert not in_queue(
        MISSED_AT, [datetime(2026, 9, 26, 23, 59, tzinfo=UTC), at(27, 0), at(28, 0)]
    )


def test_a_missed_question_answered_correctly_today_waits_for_tomorrow() -> None:
    """Another correct answer today can't count towards a new Day, so it isn't asked again."""
    assert missed_is_due(MISSED_AT, [], TODAY)
    assert not missed_is_due(MISSED_AT, [at(26, 11)], TODAY)
    assert missed_is_due(MISSED_AT, [at(26, 11)], TODAY + timedelta(days=1))


def test_a_missed_question_missed_again_today_is_due_again() -> None:
    assert missed_is_due(at(26, 15), [at(26, 11)], TODAY)


def test_a_missed_question_out_of_the_queue_is_not_due() -> None:
    assert not missed_is_due(MISSED_AT, [at(27), at(28), at(29)], date(2026, 9, 30))


# --- Spaced repeats ----------------------------------------------------------------------------


def test_a_question_never_answered_is_due_as_a_repeat() -> None:
    assert repeat_is_due(None, TODAY)


def test_a_repeat_is_due_three_days_after_the_day_it_was_last_answered() -> None:
    last = at(26, 23)

    assert not repeat_is_due(last, date(2026, 9, 26))
    assert not repeat_is_due(last, date(2026, 9, 28))
    assert repeat_is_due(last, date(2026, 9, 29))


# --- The queue ---------------------------------------------------------------------------------


def missed(n: int, first: datetime, stack: str = "mini-stack") -> Missed:
    return Missed(ref(n, stack), first_missed_at=first, last_missed_at=first, correct_at=())


def test_missed_questions_come_first_oldest_first_across_stacks() -> None:
    sources = ReviewSources(
        missed=[missed(1, at(20)), missed(2, at(18), "other-stack"), missed(3, at(19))],
        repeats=[Repeat(ref(9), None)],
    )

    assert queue(sources, TODAY) == [ref(2, "other-stack"), ref(3), ref(1), ref(9)]


def test_missed_questions_that_are_not_due_are_left_out() -> None:
    out_of_the_queue = Missed(ref(1), at(20), at(20), correct_at=(at(21), at(22), at(23)))
    right_today = Missed(ref(2), at(20), at(20), correct_at=(at(26, 9),))

    assert queue(ReviewSources(missed=[out_of_the_queue, right_today]), TODAY) == []


def test_updated_lessons_new_questions_come_after_the_missed_ones() -> None:
    sources = ReviewSources(
        missed=[missed(1, at(20))],
        updated=[ref(5), ref(4)],
        repeats=[Repeat(ref(9), None)],
    )

    assert queue(sources, TODAY) == [ref(1), ref(5), ref(4), ref(9)]


def test_repeats_come_last_least_recently_answered_first_never_answered_before_all() -> None:
    sources = ReviewSources(
        repeats=[
            Repeat(ref(1), at(20)),
            Repeat(ref(2), at(10)),
            Repeat(ref(3), None),
            Repeat(ref(4), at(15)),
            Repeat(ref(5), None),
        ]
    )

    assert queue(sources, TODAY) == [ref(3), ref(5), ref(2), ref(4), ref(1)]


def test_repeats_answered_in_the_last_three_days_are_left_out() -> None:
    sources = ReviewSources(repeats=[Repeat(ref(1), at(24)), Repeat(ref(2), at(23))])

    assert queue(sources, TODAY) == [ref(2)]


def test_a_question_is_queued_once_in_its_first_place() -> None:
    sources = ReviewSources(
        missed=[missed(1, at(20))],
        updated=[ref(1), ref(2)],
        repeats=[Repeat(ref(1), None), Repeat(ref(2), None), Repeat(ref(3), None)],
    )

    assert queue(sources, TODAY) == [ref(1), ref(2), ref(3)]


def test_a_missed_question_answered_correctly_today_is_not_asked_as_a_repeat_either() -> None:
    right_today = Missed(ref(1), at(20), at(20), correct_at=(at(26, 9),))
    sources = ReviewSources(missed=[right_today], repeats=[Repeat(ref(1), at(26, 9))])

    assert queue(sources, TODAY) == []


def test_a_set_is_ten_questions() -> None:
    assert SET_SIZE == 10


def test_an_empty_queue_is_empty() -> None:
    assert queue(ReviewSources(), TODAY) == []
