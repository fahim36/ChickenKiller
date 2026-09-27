"""Today's Daily Challenge over the API (#17), with its written Question graded (#7).

Each Active Stack has one Daily Challenge a Day, the same three Questions for everyone, released
at 00:00 UTC (ADR-0005). Only the Learner's first answer to each Question is scored; after each
answer they see the result, the Explanation and the Sources. A wrong first answer is a Missed
Question. After finishing, a replay is for learning only and changes nothing. The clock is the
test's (`clock`, conftest.py) and the grader is the fake one, which passes an answer saying
"right".

The mini Stack launched on 1 January: Challenge #1 is on 1 Jan (two multiple-choice Questions,
"a" is right, and one written), #2 on 2 Jan, and nothing is written for 3 Jan."""

from datetime import UTC, date, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from httpx2 import Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import quizzes
from app.content.importer import import_folder
from app.models import Answer, ChallengePlay
from tests.conftest import (
    CHALLENGE_MIX,
    ClientFactory,
    ContentFactory,
    FakeClock,
    FakeGrader,
    challenge,
    onboard,
    write_challenges,
)
from tests.test_lesson_quiz import RIGHT, WRONG, code, keys, learner_id
from tests.test_onboarding import other_stack

MC1, MC2, WRITTEN = CHALLENGE_MIX
SECOND = ["w01-l01-q02", "w01-l01-q04", "w01-l01-q08"]
"""Challenge #2's Questions."""

TODAY = "/stacks/mini-stack/challenges/today"

# 10:00 UTC on Challenge #1's Day.
MORNING = datetime(2026, 1, 1, 10, 0, tzinfo=UTC)


def import_stack(session: Session, make_content: ContentFactory, edit: Any = None) -> None:
    """The mini Stack with Challenges #1 (1 Jan) and #2 (2 Jan), imported on 1 Jan."""
    folder = make_content(edit)
    write_challenges(folder.parent, challenge(1), challenge(2, questions=SECOND))
    import_folder(session, folder, today=date(2026, 1, 1))


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> TestClient:
    """A Learner on the mini Stack, at 10:00 UTC on 1 January, who hasn't played anything."""
    clock.set(MORNING)
    import_stack(session, make_content)
    onboard(api)
    return api


def today(client: TestClient, url: str = TODAY) -> dict[str, Any]:
    response = client.get(url)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def answer(client: TestClient, question_id: str, given: str | None, number: int = 1) -> Response:
    return client.post(
        f"/stacks/mini-stack/challenges/{number}/answers",
        json={"question_id": question_id, "answer": given},
    )


def answered(client: TestClient, question_id: str, given: str | None, number: int = 1) -> Any:
    response = answer(client, question_id, given, number)
    assert response.status_code == 200, response.text
    return response.json()


def play_all(client: TestClient, *, written: str = RIGHT, mc2: str = "a") -> Any:
    """Answer Challenge #1: the first Question right, the second `mc2`, the written one
    `written`. Returns the last result."""
    answered(client, MC1, "a")
    answered(client, MC2, mc2)
    return answered(client, WRITTEN, written)


def challenge_answers(session: Session) -> list[tuple[str, bool | None]]:
    session.expire_all()
    return [
        (a.question_id, a.correct)
        for a in session.scalars(
            select(Answer).where(Answer.context == "daily_challenge").order_by(Answer.id)
        )
    ]


def the_play(session: Session) -> ChallengePlay:
    session.expire_all()
    return session.scalars(select(ChallengePlay)).one()


def missed(session: Session) -> list[str]:
    return quizzes.missed_question_ids(session, learner_id(session), "mini-stack")


# --- Today's Challenge ---------------------------------------------------------------------------


def test_today_s_challenge_is_the_one_dated_today_utc(learner: TestClient) -> None:
    body = today(learner)

    assert body["stack_id"] == "mini-stack"
    assert body["day"] == "2026-01-01"
    c = body["challenge"]
    assert (c["number"], c["day"], c["label"]) == (1, "2026-01-01", "Mini Stack #1 · 1 Jan")
    assert (c["status"], c["score"], c["out_of"]) == ("not_started", None, None)
    assert [q["id"] for q in c["questions"]] == CHALLENGE_MIX
    assert c["questions"][0] == {
        "id": MC1,
        "type": "multiple_choice",
        "prompt": "Question 1?",
        "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
        "retired": False,
        "retired_reason": None,
        "replaced_by": None,
        "outcome": None,
        "answered": None,
    }
    assert c["questions"][2]["type"] == "written"


def test_the_correct_answers_are_never_sent_before_the_learner_answers(
    learner: TestClient,
) -> None:
    response = learner.get(TODAY)

    assert keys(response.json()["challenge"]["questions"]).isdisjoint(
        {"answer", "explanation", "model_answer", "key_points", "summary", "sources"}
    )
    assert "Because." not in response.text


@pytest.mark.parametrize(
    ("now", "number"),
    [
        (datetime(2026, 1, 1, 0, 0, tzinfo=UTC), 1),
        (datetime(2026, 1, 1, 23, 59, 59, 999999, tzinfo=UTC), 1),
        (datetime(2026, 1, 2, 0, 0, tzinfo=UTC), 2),
    ],
)
def test_the_next_challenge_appears_at_midnight_utc(
    learner: TestClient, clock: FakeClock, now: datetime, number: int
) -> None:
    clock.set(now)

    assert today(learner)["challenge"]["number"] == number


def test_an_upcoming_challenge_s_questions_never_reach_the_learner(learner: TestClient) -> None:
    response = learner.get(TODAY)

    assert not set(SECOND) & set(response.text.split('"'))
    assert answer(learner, SECOND[0], "a", number=2).status_code == 404
    assert answer(learner, MC1, "a", number=99).status_code == 404


def test_a_day_with_no_challenge_written_says_so(learner: TestClient, clock: FakeClock) -> None:
    clock.set(datetime(2026, 1, 3, 9, 0, tzinfo=UTC))

    body = today(learner)

    assert (body["day"], body["challenge"]) == ("2026-01-03", None)


def test_a_stack_with_no_challenges_at_all_has_none_today(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))
    onboard(learner, "mini-stack", "other-stack")

    assert today(learner, "/stacks/other-stack/challenges/today")["challenge"] is None


def test_it_is_behind_the_active_stack_guard(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(other_stack))

    assert code(learner.get("/stacks/other-stack/challenges/today")) == (409, "not_active_stack")
    assert learner.get("/stacks/nope/challenges/today").status_code == 404


def test_every_learner_gets_the_same_challenge(
    learner: TestClient, admin: TestClient, signed_in: ClientFactory
) -> None:
    admin.post("/invitations", json={"email": "other@example.com"}).raise_for_status()
    other = signed_in("other@example.com")
    onboard(other)
    answered(learner, MC1, "b")

    theirs = today(other)["challenge"]

    assert [q["id"] for q in theirs["questions"]] == CHALLENGE_MIX
    assert theirs["status"] == "not_started"


# --- Answering -----------------------------------------------------------------------------------


def test_after_each_answer_the_learner_sees_the_result_explanation_and_sources(
    learner: TestClient,
) -> None:
    result = answered(learner, MC1, "b")

    assert (result["counted"], result["outcome"]) == (True, "wrong")
    q = result["question"]
    assert (q["response"], q["answer"], q["explanation"]) == ("b", "a", "Because.")
    assert q["sources"] == [
        {
            "url": "https://example.com/docs/page-1",
            "title": "Docs page 1",
            "publisher": "Example",
            "accessed": "2026-01-01",
            "claim": "What the Question relies on.",
        }
    ]
    assert result["challenge"]["status"] == "in_progress"


def test_the_challenge_shows_what_was_answered_and_only_that(learner: TestClient) -> None:
    answered(learner, MC1, "a")

    questions = today(learner)["challenge"]["questions"]

    assert questions[0]["outcome"] == "correct"
    assert questions[0]["answered"]["explanation"] == "Because."
    assert [q["answered"] for q in questions[1:]] == [None, None]
    assert keys(questions[1:]).isdisjoint({"answer", "explanation", "model_answer", "sources"})


def test_the_written_question_is_graded_against_its_model_answer(
    learner: TestClient, grader: FakeGrader
) -> None:
    result = answered(learner, WRITTEN, WRONG)

    assert result["outcome"] == "wrong"
    assert result["question"]["feedback"] == "Missing: one."
    assert result["question"]["model_answer"] == {"summary": "S", "key_points": ["one", "two"]}
    assert grader.calls == [("Explain 7.", {"summary": "S", "key_points": ["one", "two"]}, WRONG)]


def test_only_the_first_answer_to_a_question_is_scored(
    session: Session, learner: TestClient
) -> None:
    answered(learner, MC1, "b")

    again = answered(learner, MC1, "a")

    assert (again["counted"], again["outcome"]) == (False, "correct")
    assert challenge_answers(session) == [(MC1, False)]
    assert today(learner)["challenge"]["questions"][0]["outcome"] == "wrong"


def test_finishing_scores_the_first_answers(session: Session, learner: TestClient) -> None:
    last = play_all(learner, mc2="b")

    c = last["challenge"]
    assert (c["status"], c["score"], c["out_of"]) == ("finished", 2, 3)
    assert [q["outcome"] for q in c["questions"]] == ["correct", "wrong", "correct"]
    play = the_play(session)
    assert (play.challenge_number, play.score, play.out_of) == (1, 2, 3)
    assert play.started_at == play.finished_at == MORNING
    assert (play.finished_day, play.on_its_day) == (date(2026, 1, 1), True)


def test_a_wrong_first_answer_is_a_missed_question(session: Session, learner: TestClient) -> None:
    play_all(learner, mc2="b", written=WRONG)

    assert missed(session) == [MC2, WRITTEN]


def test_an_answer_that_is_not_a_choice_records_nothing(
    session: Session, learner: TestClient
) -> None:
    assert code(answer(learner, MC1, "z")) == (422, "not_a_choice")
    assert code(answer(learner, "w01-l01-q02", "a")) == (422, "question_not_in_challenge")
    assert challenge_answers(session) == []
    assert today(learner)["challenge"]["status"] == "not_started"


def test_challenge_answers_count_as_seen(session: Session, learner: TestClient) -> None:
    answered(learner, MC1, "a")

    assert MC1 in quizzes.seen_question_ids(session, learner_id(session), "mini-stack")


# --- Replaying -----------------------------------------------------------------------------------


def test_a_replay_is_marked_but_changes_nothing(session: Session, learner: TestClient) -> None:
    play_all(learner, mc2="b")
    before = (challenge_answers(session), missed(session))

    replays = [answered(learner, MC1, "b"), answered(learner, MC2, "a")]
    replays.append(answered(learner, WRITTEN, WRONG))

    assert [(r["counted"], r["outcome"]) for r in replays] == [
        (False, "wrong"),
        (False, "correct"),
        (False, "wrong"),
    ]
    assert replays[0]["question"]["explanation"] == "Because."
    assert (challenge_answers(session), missed(session)) == before
    c = today(learner)["challenge"]
    assert (c["status"], c["score"], c["out_of"]) == ("finished", 2, 3)


def test_a_replay_never_counts_towards_a_missed_question_leaving_review(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    """A Missed Question leaves Review once answered correctly on three different Days; right
    answers in a replay are not answers at all."""
    play_all(learner, mc2="b")
    for day in (2, 3, 4):
        clock.set(datetime(2026, 1, day, 10, 0, tzinfo=UTC))
        # #1 is no longer today's, but a finished play can always be replayed.
        answered(learner, MC2, "a")

    assert MC2 in [q["id"] for q in learner.get("/review").json()["questions"]]


# --- Grading failures (#7) -----------------------------------------------------------------------


def test_when_grading_fails_the_question_is_ungraded_for_good(
    session: Session, learner: TestClient, grader: FakeGrader
) -> None:
    answered(learner, MC1, "a")
    answered(learner, MC2, "a")
    grader.failing = True

    result = answered(learner, WRITTEN, RIGHT)

    assert (result["counted"], result["outcome"]) == (True, "ungraded")
    assert result["question"]["feedback"] is None
    c = result["challenge"]
    assert (c["status"], c["score"], c["out_of"]) == ("finished", 2, 3)
    assert challenge_answers(session)[-1] == (WRITTEN, None)
    assert missed(session) == []


def test_a_resubmission_after_a_grading_failure_gets_feedback_but_no_point(
    session: Session, learner: TestClient, grader: FakeGrader
) -> None:
    grader.failing = True
    answered(learner, WRITTEN, RIGHT)
    grader.failing = False

    again = answered(learner, WRITTEN, RIGHT)

    assert (again["counted"], again["outcome"]) == (False, "correct")
    assert again["question"]["feedback"] == "Covers every key point."
    assert challenge_answers(session) == [(WRITTEN, None)]
    assert today(learner)["challenge"]["questions"][2]["outcome"] == "ungraded"


def test_a_resubmission_that_can_t_be_graded_can_be_sent_again(
    learner: TestClient, grader: FakeGrader
) -> None:
    grader.failing = True
    answered(learner, WRITTEN, RIGHT)

    assert code(answer(learner, WRITTEN, RIGHT)) == (503, "grading_failed")


# --- Retired Questions ---------------------------------------------------------------------------


def retire_written(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    """Challenge #1's written Question is retired, and replaced by a new q09."""
    replacement = {**bank["questions"][6], "id": "w01-l01-q09", "prompt": "Explain 9."}
    bank["questions"][6]["retired"] = {"reason": "Out of date.", "replaced_by": "w01-l01-q09"}
    bank["questions"].append(replacement)


def test_a_retired_question_can_t_be_answered_and_isn_t_scored(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(MORNING)
    import_stack(session, make_content)
    import_folder(session, make_content(retire_written), today=date(2026, 1, 1))
    onboard(api)

    questions = today(api)["challenge"]["questions"]
    assert questions[2] == {
        "id": WRITTEN,
        "type": "written",
        "prompt": "Explain 7.",
        "choices": [],
        "retired": True,
        "retired_reason": "Out of date.",
        "replaced_by": {
            "question_id": "w01-l01-q09",
            "challenge_number": None,
            "challenge_label": None,
        },
        "outcome": None,
        "answered": None,
    }
    assert code(answer(api, WRITTEN, RIGHT)) == (409, "question_retired")

    answered(api, MC1, "a")
    c = answered(api, MC2, "b")["challenge"]
    assert (c["status"], c["score"], c["out_of"]) == ("finished", 1, 2)


def test_a_play_left_with_only_a_retired_question_to_answer_is_finished(
    session: Session, learner: TestClient, make_content: ContentFactory
) -> None:
    answered(learner, MC1, "a")
    answered(learner, MC2, "a")
    import_folder(session, make_content(retire_written), today=date(2026, 1, 1))

    c = today(learner)["challenge"]

    assert (c["status"], c["score"], c["out_of"]) == ("finished", 2, 2)
    assert the_play(session).on_its_day is True


# --- Across midnight -----------------------------------------------------------------------------


def test_a_play_started_on_its_day_can_be_finished_after_midnight_but_not_on_its_day(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    answered(learner, MC1, "a")
    clock.set(datetime(2026, 1, 2, 0, 0, 1, tzinfo=UTC))

    answered(learner, MC2, "a")
    answered(learner, WRITTEN, RIGHT)

    play = the_play(session)
    assert (play.score, play.finished_day, play.on_its_day) == (3, date(2026, 1, 2), False)
    assert today(learner)["challenge"]["number"] == 2


def test_a_past_challenge_can_still_be_played_but_not_on_its_day(
    session: Session, learner: TestClient, clock: FakeClock
) -> None:
    """From the Archive (#19, test_archive.py)."""
    clock.set(datetime(2026, 1, 2, 0, 0, tzinfo=UTC))

    play_all(learner)

    assert the_play(session).on_its_day is False


# --- Review --------------------------------------------------------------------------------------


def test_a_finished_challenge_s_questions_come_back_as_spaced_repeats(
    learner: TestClient, clock: FakeClock
) -> None:
    answered(learner, MC1, "a")
    clock.set(datetime(2026, 1, 4, 10, 0, tzinfo=UTC))
    assert learner.get("/review").json()["questions"] == []  # not finished: not played yet

    clock.set(MORNING)
    answered(learner, MC2, "a")
    answered(learner, WRITTEN, RIGHT)
    clock.set(datetime(2026, 1, 4, 10, 0, tzinfo=UTC))

    assert [q["id"] for q in learner.get("/review").json()["questions"]] == CHALLENGE_MIX
