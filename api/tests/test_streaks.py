"""Streaks and the Result Card (#18).

Each Active Stack has its own Streak: the number of consecutive UTC Days (ADR-0005) on which the
Learner played that Day's Daily Challenge. Missing a Day resets it and changes nothing else; a
Day with no Challenge neither extends nor breaks it; an Archive play never counts. The rule is
tested directly (`challenges.streak_length`), then over the API with the test's clock.

After finishing a Challenge the Learner can share its Result Card: the Stack, number, UTC date,
score and a mark per Question, never the Questions or answers.

The mini Stack's Challenges here are #1 (1 Jan), #2 (2 Jan), #4 (4 Jan) and #5 (5 Jan): nothing
is written for 3 January. Each is the same three Questions (two multiple choice, "a" is right,
and one written)."""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import challenges
from app.content.importer import import_folder
from app.models import ChallengePlay
from tests.conftest import (
    CHALLENGE_MIX,
    ContentFactory,
    FakeClock,
    FakeGrader,
    challenge,
    onboard,
    write_challenges,
)
from tests.test_daily_challenge import MC1, MC2, WRITTEN, answered, retire_written, today
from tests.test_lesson_quiz import RIGHT, WRONG, learner_id
from tests.test_onboarding import other_stack

# --- The rule ------------------------------------------------------------------------------------


def jan(*days: int) -> list[date]:
    return [date(2026, 1, d) for d in days]


@pytest.mark.parametrize(
    ("challenge_days", "played", "today", "expected"),
    [
        pytest.param(jan(1, 2, 3), [], date(2026, 1, 3), 0, id="never played"),
        pytest.param(jan(1, 2, 3), jan(1, 2, 3), date(2026, 1, 3), 3, id="every Day"),
        pytest.param(jan(1, 2, 3), jan(1, 2), date(2026, 1, 3), 2, id="today not played yet"),
        pytest.param(jan(1, 2, 3), jan(1), date(2026, 1, 3), 0, id="yesterday missed"),
        pytest.param(jan(1, 2, 3, 4), jan(1, 3, 4), date(2026, 1, 4), 2, id="broken, then again"),
        pytest.param(jan(1, 2, 4), jan(1, 2, 4), date(2026, 1, 4), 3, id="a Day with none"),
        pytest.param(jan(1, 2, 4), jan(1, 2), date(2026, 1, 3), 2, id="none today"),
        pytest.param(jan(1, 2), jan(1, 2), date(2026, 1, 9), 2, id="none for a week"),
        pytest.param(jan(1, 2, 5), jan(1, 2), date(2026, 1, 4), 2, id="upcoming ignored"),
        pytest.param([], [], date(2026, 1, 4), 0, id="no Challenges"),
    ],
)
def test_the_streak_rule(
    challenge_days: list[date], played: list[date], today: date, expected: int
) -> None:
    assert challenges.streak_length(challenge_days, set(played), today) == expected


# --- Over the API --------------------------------------------------------------------------------

TODAY = "/stacks/mini-stack/challenges/today"


def at(day: int, hour: int = 10) -> datetime:
    return datetime(2026, 1, day, hour, 0, tzinfo=UTC)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner on the mini Stack, at 10:00 UTC on 1 January, who hasn't played anything."""
    clock.set(at(1))
    folder = make_content()
    write_challenges(folder.parent, challenge(1), challenge(2), challenge(4), challenge(5))
    import_folder(session, folder, today=date(2026, 1, 1))
    onboard(api)
    return api


def play(client: TestClient, number: int, *, mc2: str = "a", written: str = RIGHT) -> str | None:
    """Finish Challenge #`number` now. Returns its Result Card."""
    answered(client, MC1, "a", number)
    answered(client, MC2, mc2, number)
    card: str | None = answered(client, WRITTEN, written, number)["challenge"]["result_card"]
    return card


def streak(client: TestClient, url: str = TODAY) -> int:
    value: int = today(client, url)["streak"]
    return value


def test_a_new_learner_has_no_streak(learner: TestClient) -> None:
    assert streak(learner) == 0


def test_finishing_today_s_challenge_extends_the_streak(
    learner: TestClient, clock: FakeClock
) -> None:
    play(learner, 1)
    assert streak(learner) == 1

    clock.set(at(2))
    assert streak(learner) == 1  # today's isn't played yet: neither extends nor breaks
    answered(learner, MC1, "a", 2)
    assert streak(learner) == 1  # started isn't finished
    play(learner, 2)
    assert streak(learner) == 2


def test_a_wrong_answer_still_counts_as_playing(learner: TestClient) -> None:
    play(learner, 1, mc2="b", written=WRONG)

    assert streak(learner) == 1


def test_a_day_with_no_challenge_neither_extends_nor_breaks_it(
    learner: TestClient, clock: FakeClock
) -> None:
    play(learner, 1)
    clock.set(at(2))
    play(learner, 2)

    clock.set(at(3))
    assert (today(learner)["challenge"], streak(learner)) == (None, 2)
    clock.set(at(4))
    assert streak(learner) == 2
    play(learner, 4)
    assert streak(learner) == 3


def test_a_missed_day_resets_the_streak_and_changes_nothing_else(
    learner: TestClient, clock: FakeClock
) -> None:
    play(learner, 1)
    clock.set(at(2, 23))
    assert streak(learner) == 1

    clock.set(at(4))  # #2 was missed; 3 January had none
    assert streak(learner) == 0
    assert learner.get("/review").status_code == 200
    play(learner, 4)
    assert streak(learner) == 1
    clock.set(at(5))
    play(learner, 5)
    assert streak(learner) == 2


def test_a_challenge_finished_after_its_day_doesn_t_count(
    learner: TestClient, clock: FakeClock
) -> None:
    """A play started on its Day but finished after midnight wasn't played on its Day."""
    answered(learner, MC1, "a")
    clock.set(datetime(2026, 1, 2, 0, 1, tzinfo=UTC))
    answered(learner, MC2, "a", 1)
    answered(learner, WRITTEN, RIGHT, 1)

    assert streak(learner) == 0


def test_an_archive_play_never_changes_a_streak(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    """Playing #2 from the Archive (#19) on 4 January doesn't mend the Day it was missed."""
    play(learner, 1)
    clock.set(at(4))
    assert streak(learner) == 0

    session.add(
        ChallengePlay(
            learner_id=learner_id(session),
            stack_id="mini-stack",
            challenge_number=2,
            started_at=at(4),
            finished_at=at(4),
            finished_day=date(2026, 1, 4),
            on_its_day=False,
            score=3,
            out_of=3,
        )
    )
    session.flush()

    assert streak(learner) == 0
    play(learner, 4)
    assert streak(learner) == 1


def test_each_active_stack_has_its_own_streak(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))
    onboard(learner, "mini-stack", "other-stack")
    play(learner, 1)

    assert streak(learner) == 1
    assert streak(learner, "/stacks/other-stack/challenges/today") == 0


# --- The Result Card -----------------------------------------------------------------------------


def test_a_finished_challenge_has_a_result_card(learner: TestClient) -> None:
    assert today(learner)["challenge"]["result_card"] is None
    answered(learner, MC1, "a")
    assert today(learner)["challenge"]["result_card"] is None

    card = play(learner, 1, mc2="b")

    assert card == "Mini Stack #1 · 1 Jan · 2/3 ✅❌✅"
    assert today(learner)["challenge"]["result_card"] == card


def test_the_result_card_never_shows_questions_or_answers(learner: TestClient) -> None:
    card = play(learner, 1, mc2="b", written=WRONG)

    assert card == "Mini Stack #1 · 1 Jan · 1/3 ✅❌❌"
    for text in [*CHALLENGE_MIX, "Question", "Explain", RIGHT, WRONG, "Right", "Wrong"]:
        assert text not in card


def test_an_ungraded_question_has_its_own_mark(learner: TestClient, grader: FakeGrader) -> None:
    answered(learner, MC1, "a")
    answered(learner, MC2, "a")
    grader.failing = True

    card = answered(learner, WRITTEN, RIGHT)["challenge"]["result_card"]

    assert card == "Mini Stack #1 · 1 Jan · 2/3 ✅✅⬜"


def test_a_retired_question_left_unanswered_has_no_mark(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    answered(learner, MC1, "a")
    answered(learner, MC2, "b")
    folder = make_content(retire_written)
    write_challenges(folder.parent, challenge(1))  # the Upcoming ones would use it
    import_folder(session, folder, today=date(2026, 1, 1))

    assert today(learner)["challenge"]["result_card"] == "Mini Stack #1 · 1 Jan · 1/2 ✅❌"
