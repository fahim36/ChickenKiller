"""Practice evidence at the agreed pure-rule seam, with explicit UTC time."""

from datetime import UTC, datetime, timedelta, timezone

from app.weak_concepts import ConceptEvidence, Evidence, Outcome, Status, evidence, rank


def at(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 10, day, hour, tzinfo=UTC)


def test_weakness_requires_two_distinct_recent_missed_questions() -> None:
    repeated = [Outcome("q1", at(1), False), Outcome("q1", at(2), False)]
    assert evidence(repeated, at(3)).status == "insufficient"
    result = evidence([*repeated, Outcome("q2", at(2), False)], at(3))
    assert result.status == "weak"
    assert result.recent_missed_questions == 2
    assert result.latest_miss == at(2)


def test_recovery_needs_three_utc_days_and_two_questions_strictly_after_latest_miss() -> None:
    missed = [Outcome("q1", at(1), False), Outcome("q2", at(2), False)]
    same_day = [Outcome("q1", at(3, hour), True) for hour in (10, 12, 16)]
    assert evidence([*missed, *same_day], at(4)).status == "weak"
    one_question = [Outcome("q1", at(day), True) for day in (3, 4, 5)]
    assert evidence([*missed, *one_question], at(6)).status == "weak"
    result = evidence([*missed, *one_question, Outcome("q2", at(5), True)], at(6))
    assert result.status == "recovered"
    assert (result.recovery_days, result.recovery_questions) == (3, 2)
    reset = evidence(
        [*missed, *one_question, Outcome("q2", at(5), True), Outcome("q1", at(6), False)], at(7)
    )
    assert reset.status == "weak"
    assert reset.recovery_days == 0


def test_expiration_is_not_recovery_and_the_window_turns_at_utc_midnight() -> None:
    first = datetime(2026, 9, 1, tzinfo=UTC)
    missed = [Outcome("q1", first, False), Outcome("q2", first, False)]
    assert evidence(missed, datetime(2026, 9, 30, 23, 59, tzinfo=UTC)).status == "weak"
    expired = evidence(missed, at(1, 0))
    assert expired.status == "expired"
    assert expired.recent_missed_questions == 0
    dhaka = timezone(timedelta(hours=6))
    assert evidence(missed, datetime(2026, 10, 1, 5, 59, tzinfo=dhaka)).status == "weak"
    assert evidence(missed, datetime(2026, 10, 1, 6, 0, tzinfo=dhaka)).status == "expired"


def test_equal_time_and_future_correct_answers_cannot_recover() -> None:
    missed = [Outcome("q1", at(1), False), Outcome("q2", at(2), False)]
    result = evidence([*missed, Outcome("q1", at(2), True), Outcome("q2", at(4), True)], at(3))
    assert result.status == "weak"
    assert result.recovery_days == 0


def test_old_misses_that_never_shared_a_window_are_insufficient_not_expired() -> None:
    history = [Outcome("q1", datetime(2026, 8, 1, tzinfo=UTC), False), Outcome("q2", at(1), False)]
    assert evidence(history, at(3)).status == "insufficient"


def test_weak_ranking_prefers_distinct_misses_then_newest_miss_then_stable_id() -> None:
    def concept(
        identifier: str, count: int, latest: datetime, status: Status = "weak"
    ) -> ConceptEvidence:
        return ConceptEvidence(
            identifier, identifier, 4, None, None, Evidence(status, count, latest, 0, 0)
        )

    values = [
        concept("b", 2, at(2)),
        concept("a", 2, at(2)),
        concept("older", 2, at(1)),
        concept("more", 3, at(1)),
        concept("recovered", 4, at(3), "recovered"),
    ]
    assert [c.id for c in sorted(values, key=rank)] == ["more", "a", "b", "older", "recovered"]
