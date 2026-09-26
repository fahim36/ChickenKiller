"""Importing a new Syllabus version without losing progress (#13), over the API.

The Learner studies version 1 of a small Stack, then version 2 is imported. The two versions
differ by one added, one changed and one removed Lesson:

    v1  w01: w01-l01, w01-l02, w01-l03    w02: w02-l01
    v2  w01: w01-l01*, w01-new, w01-l03   w02: w02-l01

- `w01-l01` is changed: its Question Bank gains `w01-l01-q09`.
- `w01-l02` is removed; `w01-new` is added in its place, which is behind a Learner who had
  completed `w01-l02`.

Every Lesson has a bank of eight Questions: six multiple choice (choice "a" is right) and two
written (the fake grader passes an answer saying "right"). The clock is the test's."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app import updated_lessons
from app.content.importer import import_folder
from app.models import Answer, Lesson, Syllabus
from tests.conftest import (
    ContentFactory,
    FakeClock,
    as_version,
    changelog_entry,
    complete_lessons,
    make_bank,
    make_changelog,
    onboard,
)
from tests.test_daily_review import answer, current_round, daily_review, finish, right_answer
from tests.test_lesson_quiz import answer_all, code, learner_id, lesson_states, start, submit

V1, V2 = "v2026-01-01", "v2026-02-01"
STACK = "/stacks/mini-stack"


def quiz_url(lesson: str) -> str:
    return f"{STACK}/lessons/{lesson}/quiz"


def version_1(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    [week] = syllabus["weeks"]
    week["lessons"].append(
        {
            "id": "w01-l03",
            "title": "Third lesson",
            "topics": ["D"],
            "exercise": None,
            "minutes": 30,
            "materials": [],
        }
    )
    syllabus["weeks"].append(
        {
            "id": "w02",
            "number": 2,
            "title": "Week two",
            "goal": "More.",
            "deliverable": "Another thing.",
            "interview_checks": [],
            "lessons": [
                {
                    "id": "w02-l01",
                    "title": "Fourth lesson",
                    "topics": ["E"],
                    "exercise": None,
                    "minutes": 30,
                    "materials": [],
                }
            ],
            "milestones": [],
        }
    )


def version_2(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    version_1(syllabus, bank)
    lessons = syllabus["weeks"][0]["lessons"]
    lessons[1] = {
        "id": "w01-new",
        "title": "New lesson",
        "topics": ["N"],
        "exercise": None,
        "minutes": 45,
        "materials": [],
    }
    bank["questions"].append(
        {
            "id": "w01-l01-q09",
            "concept": "concept-a",
            "type": "multiple_choice",
            "prompt": "A new question?",
            "choices": [{"id": "a", "text": "Right"}, {"id": "b", "text": "Wrong"}],
            "answer": "a",
            "explanation": "Because.",
            "materials": [],
        }
    )


V1_BANKS = {
    "w01-l02": make_bank("w01-l02", "second"),
    "w01-l03": make_bank("w01-l03", "third"),
    "w02-l01": make_bank("w02-l01", "fourth"),
}
V2_BANKS = {
    "w01-new": make_bank("w01-new", "new"),
    "w01-l03": make_bank("w01-l03", "third"),
    "w02-l01": make_bank("w02-l01", "fourth"),
}
V2_CHANGELOG = make_changelog(
    V2,
    V1,
    changelog_entry("lesson", "w01-new", "added"),
    changelog_entry("lesson", "w01-l01", "changed"),
    changelog_entry("lesson", "w01-l02", "removed"),
)

# 09:00 UTC on 26 September.
MORNING = datetime(2026, 9, 26, 9, 0, tzinfo=UTC)


def import_version_2(session: Session, make_content: ContentFactory) -> None:
    result = import_folder(
        session,
        make_content(as_version(V2, version_2), extra_banks=V2_BANKS, changelog=V2_CHANGELOG),
    )
    assert (result.status, result.is_current) == ("imported", True)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> Iterator[TestClient]:
    """A Learner on version 1 who has completed w01-l01, completed w01-l02 after missing a
    Question and retaking it, ticked w01-m01, and started (not submitted) the Lesson Quiz of
    their Unlocked Lesson, w01-l03."""
    clock.set(MORNING)
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    onboard(api)
    complete_lessons(session, "w01-l01")

    quiz = start(api, quiz_url("w01-l02"))
    result = submit(api, quiz, answer_all(quiz, wrong=1), quiz_url("w01-l02")).json()
    assert result["next_step"] == "retakes"
    [retake] = result["retakes"]
    retaken = api.post(
        f"{STACK}/lessons/w01-l02/retakes/{retake['id']}/answers",
        json={"answer": right_answer(retake["question"])},
    ).json()
    assert retaken["lesson_completed"] is True

    api.put(f"{STACK}/milestones/w01-m01", json={"ticked": True}).raise_for_status()
    in_progress = start(api, quiz_url("w01-l03"))
    assert in_progress["version"] == V1
    yield api


def week_map(client: TestClient) -> dict[str, Any]:
    response = client.get(STACK)
    assert response.status_code == 200, response.text
    body: dict[str, Any] = response.json()
    return body


def missed_in(session: Session, lesson: str) -> list[str]:
    return list(
        session.scalars(
            select(Answer.question_id).where(
                Answer.correct.is_(False), Answer.question_id.startswith(lesson)
            )
        )
    )


# --- Progress carries over ---------------------------------------------------------------------


def test_the_week_map_before_the_update(learner: TestClient) -> None:
    assert lesson_states(learner) == {
        "w01-l01": "completed",
        "w01-l02": "completed",
        "w01-l03": "unlocked",
        "w02-l01": "locked",
    }


def test_completed_lessons_stay_completed_and_the_changed_and_added_lessons_are_updated(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)

    assert lesson_states(learner) == {
        "w01-l01": "updated",
        "w01-new": "updated",
        "w01-l03": "unlocked",
        "w02-l01": "locked",
    }


def test_the_unlocked_lesson_is_the_next_surviving_lesson_after_the_removed_one(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    """w01-l02, the furthest Completed Lesson, was removed: w01-l03 after it stays Unlocked,
    and the Lesson added in its place doesn't hold it back."""
    import_version_2(session, make_content)

    [week_1, _] = week_map(learner)["weeks"]
    assert [lesson["id"] for lesson in week_1["lessons"]] == ["w01-l01", "w01-new", "w01-l03"]
    assert lesson_states(learner)["w01-l03"] == "unlocked"


def test_a_removed_completed_lesson_stays_in_the_learners_history(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)

    body = week_map(learner)
    assert body["version"] == V2
    assert [(r["id"], r["title"], r["version"]) for r in body["removed_lessons"]] == [
        ("w01-l02", "Second lesson", V1)
    ]
    assert "w01-l02" not in lesson_states(learner)


def test_a_removed_lesson_disappears_from_the_path_of_a_learner_who_had_not_reached_it(
    session: Session, api: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    onboard(api)
    import_version_2(session, make_content)

    assert lesson_states(api) == {
        "w01-l01": "unlocked",
        "w01-new": "locked",
        "w01-l03": "locked",
        "w02-l01": "locked",
    }
    assert week_map(api)["removed_lessons"] == []


def test_milestone_ticks_and_missed_questions_are_kept(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    missed_before = missed_in(session, "w01-l02")
    assert len(missed_before) == 1

    import_version_2(session, make_content)

    [week_1, _] = week_map(learner)["weeks"]
    assert week_1["milestones"][0]["ticked"] is True
    assert missed_in(session, "w01-l02") == missed_before


def test_an_updated_lesson_has_no_lesson_quiz(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)

    for lesson in ("w01-l01", "w01-new"):
        assert code(learner.post(quiz_url(lesson))) == (409, "lesson_updated")
        assert learner.get(f"{STACK}/lessons/{lesson}").json()["state"] == "updated"


# --- A Lesson Quiz in progress ----------------------------------------------------------------


def test_a_quiz_in_progress_finishes_on_the_old_version_and_the_next_attempt_uses_the_new_one(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)

    resumed = start(learner, quiz_url("w01-l03"))
    assert resumed["version"] == V1
    result = submit(learner, resumed, answer_all(resumed, wrong=2), quiz_url("w01-l03"))
    assert result.status_code == 200, result.text
    assert result.json()["next_step"] == "fresh_quiz"
    recorded = session.scalars(
        select(Answer.syllabus_version).where(Answer.question_id.startswith("w01-l03"))
    ).all()
    assert set(recorded) == {V1}

    fresh = start(learner, quiz_url("w01-l03"))
    assert fresh["attempt_id"] != resumed["attempt_id"]
    assert fresh["version"] == V2


def test_a_lesson_completed_on_the_old_version_after_the_import_is_updated_if_it_changed(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    """The Learner started w01-l01's quiz on version 1 and passed it after version 2 changed
    the Lesson: it is completed in version 1, so it is Updated, and q09 is new to them."""
    clock.set(MORNING)
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    onboard(api)
    quiz = start(api, quiz_url("w01-l01"))
    import_version_2(session, make_content)

    assert submit(api, quiz, answer_all(quiz), quiz_url("w01-l01")).json()["lesson_completed"]

    assert lesson_states(api)["w01-l01"] == "updated"
    owed = updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack")
    assert owed == ["w01-l01-q09"]


# --- The Daily Review --------------------------------------------------------------------------


def next_day(client: TestClient, clock: FakeClock) -> None:
    """Finish today's open Review Round, so nothing carries over, and move to the next day."""
    current = daily_review(client)["current"]
    if current is not None:
        finish(client, current)
    clock.advance(days=1)


def test_the_updated_lessons_new_questions_come_after_the_missed_questions_next_day(
    session: Session, make_content: ContentFactory, learner: TestClient, clock: FakeClock
) -> None:
    """Round 1 the next day: the Missed Questions still in the Syllabus first (the one missed
    in the removed w01-l02 has left the rotation), then the Updated Lessons' new Questions in
    Syllabus order: w01-l01's q09, then the added Lesson's bank, up to ten."""
    import_version_2(session, make_content)
    resumed = start(learner, quiz_url("w01-l03"))
    submit(learner, resumed, answer_all(resumed, wrong=2), quiz_url("w01-l03"))
    missed_in_l03 = [q["id"] for q in resumed["questions"][:2]]

    next_day(learner, clock)
    round_ = current_round(learner)

    asked = [q["id"] for q in round_["remaining"]]
    assert asked == [
        *missed_in_l03,
        "w01-l01-q09",
        *[f"w01-new-q{n:02}" for n in range(1, 8)],
    ]
    assert not [q for q in asked if q.startswith("w01-l02")]


def test_round_2_asks_the_new_questions_round_1_had_no_room_for(
    session: Session, make_content: ContentFactory, learner: TestClient, clock: FakeClock
) -> None:
    """Round 1 had no room for the added Lesson's last Question, q08: Round 2 leads with it,
    and none of Round 1's Missed or new Questions come back the same day. (Completed Lessons'
    Questions may repeat to fill a short round: here that pool is w01-l01's nine.)"""
    import_version_2(session, make_content)
    resumed = start(learner, quiz_url("w01-l03"))
    submit(learner, resumed, answer_all(resumed, wrong=2), quiz_url("w01-l03"))
    next_day(learner, clock)
    round_1 = current_round(learner)
    finish(learner, round_1)

    clock.advance(hours=4)
    round_2 = current_round(learner)

    assert round_2["number"] == 2
    asked = [q["id"] for q in round_2["remaining"]]
    assert asked[0] == "w01-new-q08"
    led_round_1 = {q["id"] for q in round_1["remaining"] if not q["id"].startswith("w01-l01-q0")}
    assert led_round_1 and not led_round_1 & set(asked)


def test_a_new_question_is_owed_until_the_learner_answers_it(
    session: Session, make_content: ContentFactory, learner: TestClient, clock: FakeClock
) -> None:
    import_version_2(session, make_content)
    next_day(learner, clock)
    round_ = current_round(learner)
    owed_before = updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack")
    assert owed_before[0] == "w01-l01-q09"

    assert answer(learner, round_, "w01-l01-q09", "b").status_code == 200

    owed = updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack")
    assert owed == owed_before[1:]


def test_nothing_is_owed_before_a_new_version(learner: TestClient, session: Session) -> None:
    assert updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack") == []


# --- The importer ------------------------------------------------------------------------------


def test_reimporting_a_version_fills_in_lesson_fingerprints_it_was_imported_without(
    session: Session, make_content: ContentFactory
) -> None:
    folder = make_content(as_version(V1, version_1), extra_banks=V1_BANKS)
    import_folder(session, folder)
    stored = dict(session.execute(select(Lesson.id, Lesson.content_hash)).all())
    session.execute(update(Lesson).values(content_hash=None))

    assert import_folder(session, folder).status == "unchanged"

    session.expire_all()
    assert dict(session.execute(select(Lesson.id, Lesson.content_hash)).all()) == stored
    assert all(stored.values())


def test_an_unchanged_lesson_keeps_its_fingerprint_across_versions(
    session: Session, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    import_version_2(session, make_content)

    rows = session.execute(
        select(Lesson.id, Syllabus.version, Lesson.content_hash).join(
            Syllabus, Syllabus.pk == Lesson.syllabus_pk
        )
    ).all()
    by_version = {(lesson, version): h for lesson, version, h in rows}
    assert by_version[("w01-l03", V1)] == by_version[("w01-l03", V2)]
    assert by_version[("w01-l01", V1)] != by_version[("w01-l01", V2)]
