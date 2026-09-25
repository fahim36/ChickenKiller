"""A Learner's "today" is the calendar day in their own time zone (the Daily Review needs it)."""

from datetime import UTC, date, datetime

from app.onboarding import today_for


def test_the_day_turns_at_midnight_in_dhaka_not_at_midnight_utc() -> None:
    # Midnight in Dhaka (UTC+6) is 18:00 UTC.
    assert today_for("Asia/Dhaka", datetime(2026, 9, 26, 17, 59, tzinfo=UTC)) == date(2026, 9, 26)
    assert today_for("Asia/Dhaka", datetime(2026, 9, 26, 18, 0, tzinfo=UTC)) == date(2026, 9, 27)


def test_it_is_still_yesterday_in_los_angeles_after_midnight_utc() -> None:
    now = datetime(2026, 9, 27, 3, 0, tzinfo=UTC)

    assert today_for("America/Los_Angeles", now) == date(2026, 9, 26)
    assert today_for("UTC", now) == date(2026, 9, 27)
