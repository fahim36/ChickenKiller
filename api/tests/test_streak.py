"""The Streak over the API (#11): the Week map's count of consecutive days on which the Learner
finished their whole Daily Review. The clock is the test's (`clock`, conftest.py); the rules
themselves are tested in test_review_rules.py.

The Learner is in Asia/Dhaka (UTC+6) with a Completed Lesson (test_daily_review's `learner`).
A day's Daily Review is finished in one round by starting it at 21:00 in Dhaka: Round 2 would
open four hours after Round 1 is finished, after midnight, so it never opens."""

from datetime import UTC, date, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Learner, ReviewDay
from tests import test_daily_review
from tests.conftest import LEARNER_EMAIL, FakeClock
from tests.test_daily_review import current_round, daily_review, finish
from tests.test_lesson_quiz import lesson_states

learner = test_daily_review.learner  # the fixture

# 21:00 in Dhaka on 26 September, the Learner's first day.
FIRST_EVENING = datetime(2026, 9, 26, 15, 0, tzinfo=UTC)


def streak(client: TestClient) -> int:
    response = client.get("/stacks/mini-stack")
    assert response.status_code == 200, response.text
    value: int = response.json()["streak"]
    return value


def evening(day: int) -> datetime:
    """21:00 in Dhaka on the Learner's `day`-th day (0 is the first)."""
    return FIRST_EVENING + timedelta(days=day)


def finish_day(client: TestClient, clock: FakeClock, day: int) -> None:
    """Use the app at 21:00 in Dhaka on `day` and finish its only Review Round."""
    clock.set(evening(day))
    finish(client, current_round(client))


def test_the_streak_is_zero_before_any_daily_review_is_finished(learner: TestClient) -> None:
    assert streak(learner) == 0


def test_finishing_the_day_s_daily_review_counts_today(
    learner: TestClient, clock: FakeClock
) -> None:
    finish_day(learner, clock, 0)

    assert streak(learner) == 1


def test_each_day_with_every_round_finished_adds_one(learner: TestClient, clock: FakeClock) -> None:
    for day in range(3):
        finish_day(learner, clock, day)

    assert streak(learner) == 3


def test_today_s_round_still_to_do_does_not_break_the_streak(
    learner: TestClient, clock: FakeClock
) -> None:
    for day in range(3):
        finish_day(learner, clock, day)
    clock.set(evening(3) - timedelta(hours=1))  # Round 1 opens at 20:00...
    current_round(learner)
    clock.advance(hours=2)  # ...and is pending at 22:00

    assert current_round(learner)["state"] == "pending"
    assert streak(learner) == 3


def test_a_day_with_a_round_left_unfinished_resets_the_streak_and_nothing_else(
    learner: TestClient, clock: FakeClock
) -> None:
    for day in range(2):
        finish_day(learner, clock, day)
    clock.set(evening(2))
    current_round(learner)  # Round 1 opens and is left unfinished
    before = lesson_states(learner)

    clock.set(evening(3) - timedelta(hours=11))  # 10:00 the next day

    assert streak(learner) == 0
    assert lesson_states(learner) == before


def test_a_round_that_came_due_while_the_learner_was_away_counts_as_unfinished(
    learner: TestClient, clock: FakeClock
) -> None:
    """Round 1 finished at 10:00, so Round 2 opened at 14:00, while nobody was using the app. It
    was never stored, but it was owed."""
    finish_day(learner, clock, 0)
    clock.set(evening(1) - timedelta(hours=11))  # 10:00 in Dhaka
    finish(learner, current_round(learner))
    assert streak(learner) == 1  # still today, Round 2 not due yet

    clock.set(evening(2))

    assert streak(learner) == 0


def test_the_streak_counts_again_from_the_day_after_it_broke(
    learner: TestClient, clock: FakeClock
) -> None:
    finish_day(learner, clock, 0)
    clock.set(evening(1))
    current_round(learner)  # left unfinished
    finish_day(learner, clock, 2)
    finish_day(learner, clock, 3)

    assert streak(learner) == 2


def test_a_day_without_using_the_app_breaks_the_streak(
    learner: TestClient, clock: FakeClock
) -> None:
    """Round 1 opens on the day's first use, so a day away owes a Round 1 that never opened."""
    finish_day(learner, clock, 0)
    finish_day(learner, clock, 1)
    finish_day(learner, clock, 3)  # day 2 skipped

    assert streak(learner) == 1


def test_a_day_with_nothing_owed_neither_extends_nor_breaks_the_streak(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    """A day whose first use came when there was nothing to review opens no round. Day 1 is
    recorded that way here, as `reviews.start_day` records such a day."""
    learner_id = session.scalars(select(Learner.id).where(Learner.email == LEARNER_EMAIL)).one()
    session.add(
        ReviewDay(
            learner_id=learner_id,
            stack_id="mini-stack",
            day=date(2026, 9, 27),
            first_used_at=evening(1),
        )
    )
    session.commit()
    finish_day(learner, clock, 0)
    clock.set(evening(1))
    assert daily_review(learner)["rounds"] == []
    assert streak(learner) == 1

    finish_day(learner, clock, 2)

    assert streak(learner) == 2
