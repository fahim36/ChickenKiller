"""The Archive and Catch-up over the API (#19).

Each Stack's Archive is every released Daily Challenge, back to #1, newest first; an Upcoming
Challenge never appears in it. Any of them can be played: a first play is scored as usual, and
its misses are Missed Questions, but a past Challenge's play is never on its own Day, so it
never counts toward a Streak (#18 counts only `on_its_day` plays). A played Challenge shows the
first result and can be replayed, which changes nothing. A Retired Question shows its reason and
a link to the released Challenge that asks its replacement, if one does, and can't be answered.

Catch-up is the Archive's past Challenges the Learner hasn't finished, across their Active
Stacks, with a count per Stack. It is optional and never blocks anything.

The mini Stack launched on 1 January: Challenge #1 on 1 Jan, #2 on 2 Jan (see
test_daily_challenge.py). The clock is the test's and the grader the fake one."""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from tests.conftest import (
    CHALLENGE_MIX,
    ContentFactory,
    FakeClock,
    challenge,
    onboard,
    write_challenges,
)
from tests.test_daily_challenge import (
    MC1,
    MC2,
    MORNING,
    SECOND,
    WRITTEN,
    answer,
    answered,
    challenge_answers,
    import_stack,
    missed,
    play_all,
    retire_written,
    the_play,
    today,
)
from tests.test_lesson_quiz import RIGHT, WRONG, code
from tests.test_onboarding import other_stack

ARCHIVE = "/stacks/mini-stack/challenges"

# 10:00 UTC on Challenge #2's Day, and the Day after it.
NEXT_MORNING = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
LATER = datetime(2026, 1, 3, 10, 0, tzinfo=UTC)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner on the mini Stack, on 3 January, after both Challenges' Days, who hasn't
    played anything."""
    clock.set(MORNING)
    import_stack(session, make_content)
    onboard(api)
    clock.set(LATER)
    return api


def get(client: TestClient, url: str) -> Any:
    response = client.get(url)
    assert response.status_code == 200, response.text
    return response.json()


def listed(client: TestClient) -> list[tuple[int, str, str, int | None, int | None]]:
    return [
        (c["number"], c["label"], c["status"], c["score"], c["out_of"])
        for c in get(client, ARCHIVE)["challenges"]
    ]


# --- The Archive -------------------------------------------------------------------------------


def test_the_archive_lists_every_released_challenge_newest_first(learner: TestClient) -> None:
    body = get(learner, ARCHIVE)

    assert (body["stack_id"], body["stack_name"], body["day"]) == (
        "mini-stack",
        "Mini Stack",
        "2026-01-03",
    )
    assert listed(learner) == [
        (2, "Mini Stack #2 · 2 Jan", "not_started", None, None),
        (1, "Mini Stack #1 · 1 Jan", "not_started", None, None),
    ]


def test_the_archive_never_shows_an_upcoming_challenge(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 1, 1, 23, 59, tzinfo=UTC))

    assert [n for n, *_ in listed(learner)] == [1]
    assert learner.get(f"{ARCHIVE}/2").status_code == 404
    assert learner.get(f"{ARCHIVE}/99").status_code == 404


def test_the_archive_shows_each_challenge_s_first_result(learner: TestClient) -> None:
    play_all(learner, mc2="b")
    answered(learner, SECOND[0], "a", number=2)

    assert listed(learner) == [
        (2, "Mini Stack #2 · 2 Jan", "in_progress", None, None),
        (1, "Mini Stack #1 · 1 Jan", "finished", 2, 3),
    ]


def test_an_archived_challenge_can_be_opened_like_today_s(learner: TestClient) -> None:
    body = get(learner, f"{ARCHIVE}/1")

    assert (body["stack_name"], body["day"]) == ("Mini Stack", "2026-01-03")
    c = body["challenge"]
    assert (c["number"], c["label"], c["status"]) == (1, "Mini Stack #1 · 1 Jan", "not_started")
    assert [q["id"] for q in c["questions"]] == CHALLENGE_MIX
    assert c["questions"][0]["answered"] is None


def test_the_archive_is_behind_the_active_stack_guard(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))

    assert code(learner.get("/stacks/other-stack/challenges")) == (409, "not_active_stack")
    assert code(learner.get("/stacks/other-stack/challenges/1")) == (409, "not_active_stack")


# --- Playing from the Archive ------------------------------------------------------------------


def test_a_past_challenge_is_graded_as_usual_with_misses_recorded(
    session: Session, learner: TestClient
) -> None:
    last = play_all(learner, mc2="b", written=WRONG)

    c = last["challenge"]
    assert (c["status"], c["score"], c["out_of"]) == ("finished", 1, 3)
    assert [q["outcome"] for q in c["questions"]] == ["correct", "wrong", "wrong"]
    assert last["question"]["explanation"] == "Because."
    assert missed(session) == [MC2, WRITTEN]


def test_an_archive_play_never_counts_toward_a_streak(
    session: Session, learner: TestClient
) -> None:
    """A Streak counts only plays on the Challenge's own Day (#18); an Archive play is stored as
    not on its Day."""
    play_all(learner)

    play = the_play(session)
    assert (play.score, play.finished_day, play.on_its_day) == (3, date(2026, 1, 3), False)


def test_today_s_challenge_played_from_the_archive_is_still_on_its_day(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    clock.set(NEXT_MORNING)
    assert get(learner, f"{ARCHIVE}/2")["challenge"] == today(learner)["challenge"]

    for qid in SECOND:
        answered(learner, qid, RIGHT if qid == SECOND[2] else "a", number=2)

    play = the_play(session)
    assert (play.challenge_number, play.on_its_day) == (2, True)


def test_an_archive_play_leaves_the_streak_as_it_was(learner: TestClient, clock: FakeClock) -> None:
    """End to end with #18's Streak: today's Challenge finished makes 1; a past one played from
    the Archive the same Day adds nothing."""
    clock.set(NEXT_MORNING)
    for qid in SECOND:
        answered(learner, qid, RIGHT if qid == SECOND[2] else "a", number=2)
    assert today(learner)["streak"] == 1

    last = play_all(learner)

    assert last["challenge"]["status"] == "finished"
    assert today(learner)["streak"] == 1


def test_a_replay_of_an_archived_challenge_changes_no_score(
    session: Session, learner: TestClient
) -> None:
    play_all(learner, mc2="b")
    before = (challenge_answers(session), missed(session))

    replays = [answered(learner, MC1, "b"), answered(learner, MC2, "a")]
    replays.append(answered(learner, WRITTEN, WRONG))

    assert [r["counted"] for r in replays] == [False, False, False]
    assert replays[1]["question"]["explanation"] == "Because."
    assert replays[1]["question"]["sources"][0]["url"] == "https://example.com/docs/page-1"
    assert (challenge_answers(session), missed(session)) == before
    c = get(learner, f"{ARCHIVE}/1")["challenge"]
    assert (c["status"], c["score"], c["out_of"]) == ("finished", 2, 3)
    assert [q["outcome"] for q in c["questions"]] == ["correct", "wrong", "correct"]
    assert listed(learner)[1][2:] == ("finished", 2, 3)


# --- Retired Questions -------------------------------------------------------------------------


def asks_replacement(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """The mini Stack's bank with the replacement q09 in it, not yet retiring anything."""
    bank["questions"].append({**bank["questions"][6], "id": "w01-l01-q09", "prompt": "Explain 9."})


@pytest.fixture
def retired(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """Challenge #1's written Question retired on 1 Jan ("Out of date."), replaced by q09,
    which Challenge #2 (2 Jan) asks. A Learner on the mini Stack who hasn't played anything."""
    clock.set(MORNING)
    folder = make_content(asks_replacement)
    write_challenges(
        folder.parent, challenge(1), challenge(2, questions=[*SECOND[:2], "w01-l01-q09"])
    )
    import_folder(session, folder, today=date(2026, 1, 1))
    import_folder(session, make_content(retire_written), today=date(2026, 1, 1))
    onboard(api)
    return api


def test_a_retired_question_shows_its_reason_and_the_challenge_asking_its_replacement(
    retired: TestClient, clock: FakeClock
) -> None:
    clock.set(LATER)

    q = get(retired, f"{ARCHIVE}/1")["challenge"]["questions"][2]

    assert (q["id"], q["retired"], q["retired_reason"]) == (WRITTEN, True, "Out of date.")
    assert q["replaced_by"] == {
        "question_id": "w01-l01-q09",
        "challenge_number": 2,
        "challenge_label": "Mini Stack #2 · 2 Jan",
    }
    assert (q["choices"], q["answered"]) == ([], None)


def test_a_replacement_in_an_upcoming_challenge_gets_no_link(retired: TestClient) -> None:
    """Challenge #2 isn't released on 1 Jan: nothing about it is sent."""
    body = get(retired, f"{ARCHIVE}/1")

    assert body["challenge"]["questions"][2]["replaced_by"] == {
        "question_id": "w01-l01-q09",
        "challenge_number": None,
        "challenge_label": None,
    }


def test_a_retired_question_in_the_archive_can_t_be_answered_and_isn_t_scored(
    session: Session, retired: TestClient, clock: FakeClock
) -> None:
    clock.set(LATER)

    assert code(answer(retired, WRITTEN, RIGHT)) == (409, "question_retired")
    answered(retired, MC1, "a")
    c = answered(retired, MC2, "b")["challenge"]

    assert (c["status"], c["score"], c["out_of"]) == ("finished", 1, 2)
    assert challenge_answers(session) == [(MC1, True), (MC2, False)]
    assert the_play(session).on_its_day is False


def test_a_question_that_isn_t_retired_has_no_reason_or_replacement(
    learner: TestClient,
) -> None:
    q = get(learner, f"{ARCHIVE}/1")["challenge"]["questions"][0]

    assert (q["retired"], q["retired_reason"], q["replaced_by"]) == (False, None, None)


# --- Catch-up ----------------------------------------------------------------------------------


def with_other_stack(session: Session, make_content: ContentFactory, *numbers: int) -> None:
    """The other Stack, with Challenges `numbers` from the same launch, imported on 1 Jan."""
    folder = make_content(other_stack)
    write_challenges(folder.parent, *(challenge(n) for n in numbers))
    import_folder(session, folder, today=date(2026, 1, 1))


def catch_up(client: TestClient) -> list[tuple[str, int, list[tuple[int, str]]]]:
    return [
        (s["stack_id"], s["count"], [(c["number"], c["status"]) for c in s["challenges"]])
        for s in get(client, "/catch-up")["stacks"]
    ]


def test_catch_up_lists_unplayed_past_challenges_across_active_stacks(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    with_other_stack(session, make_content, 1, 2, 3)
    onboard(learner, "mini-stack", "other-stack")

    body = get(learner, "/catch-up")

    assert [(s["stack_id"], s["stack_name"], s["count"]) for s in body["stacks"]] == [
        ("mini-stack", "Mini Stack", 2),
        ("other-stack", "Other Stack", 2),
    ]
    first = body["stacks"][0]["challenges"][0]
    assert (first["number"], first["label"]) == (2, "Mini Stack #2 · 2 Jan")


def test_catch_up_leaves_out_today_s_and_finished_challenges(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    """Today's is the home page's; a started one stays until it is finished."""
    with_other_stack(session, make_content, 1, 2, 3)
    onboard(learner, "mini-stack", "other-stack")
    play_all(learner)
    answered(learner, SECOND[0], "a", number=2)

    assert catch_up(learner) == [
        ("mini-stack", 1, [(2, "in_progress")]),
        ("other-stack", 2, [(2, "not_started"), (1, "not_started")]),
    ]


def test_catch_up_counts_only_active_stacks(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    with_other_stack(session, make_content, 1)

    assert catch_up(learner) == [
        ("mini-stack", 2, [(2, "not_started"), (1, "not_started")]),
    ]


def test_an_active_stack_with_nothing_to_catch_up_on_counts_zero(
    learner: TestClient, clock: FakeClock
) -> None:
    clock.set(MORNING)

    assert catch_up(learner) == [("mini-stack", 0, [])]
