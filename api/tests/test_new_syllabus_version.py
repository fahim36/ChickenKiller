"""Importing a new Syllabus version without losing progress (#13), over the API.

The Learner studies version 1 of a small Stack, then version 2 is imported. The two versions
differ by one added, one changed and one removed Lesson:

    v1  w01: w01-l01, w01-l02, w01-l03    w02: w02-l01
    v2  w01: w01-l01*, w01-new, w01-l03   w02: w02-l01

- `w01-l01` is changed: the Question Bank gains `w01-l01-q09`, tagged to it. Its Syllabus
  fields don't change, so the changelog doesn't list it (the changelog covers the Syllabus
  only), but its fingerprint does (#15).
- `w01-l02` is removed, and its Questions are un-tagged: they stay in the Question Bank, not
  retired, but no Lesson draws them. `w01-new` is added in its place, which is behind a Learner
  who had completed `w01-l02`.

Every Lesson has a bank of eight Questions: six multiple choice (choice "a" is right) and two
written (the fake grader passes an answer saying "right"). The clock is the test's.

Streaks and Daily Challenge results must survive an import too. The Learner plays the Stack's
Daily Challenge #1 in the `learner` fixture, and its plays (#17) are in `PROGRESS_TABLES`, so
`test_an_import_changes_no_learner_data` covers them. A Streak (#18) has no table: it is counted
from those plays, and `test_the_streak_survives_an_import` checks it."""

import copy
from collections.abc import Callable, Iterator
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import updated_lessons
from app.content.importer import import_folder
from app.models import (
    Answer,
    ChallengePlay,
    CompletedLesson,
    LearnerStack,
    Lesson,
    LessonQuizAttempt,
    MilestoneTick,
    Question,
    Retake,
    Syllabus,
)
from tests.conftest import (
    CHALLENGE_MIX,
    ClientFactory,
    ContentFactory,
    FakeClock,
    as_version,
    challenge,
    changelog_entry,
    complete_lessons,
    make_bank,
    make_changelog,
    onboard,
    source,
    write_challenges,
)
from tests.test_lesson_quiz import (
    RIGHT,
    answer_all,
    code,
    learner_id,
    lesson_states,
    start,
    submit,
)
from tests.test_review import answer, answer_right, asked, review_set

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
            "lesson": "w01-l01",
            "sources": [source()],
        }
    )


V1_BANKS = {
    "w01-l02": make_bank("w01-l02", "second"),
    "w01-l03": make_bank("w01-l03", "third"),
    "w02-l01": make_bank("w02-l01", "fourth"),
}


def untagged(bank: dict[str, Any]) -> dict[str, Any]:
    """`bank` with its Questions tagged to no Lesson, as a Syllabus Update that removes their
    Lesson leaves them (a Question that isn't retired must be tagged to a current Lesson, or
    none)."""
    for question in bank["questions"]:
        question["lesson"] = None
    return bank


V2_BANKS = {
    "w01-l02": untagged(make_bank("w01-l02", "second")),
    "w01-new": make_bank("w01-new", "new"),
    "w01-l03": make_bank("w01-l03", "third"),
    "w02-l01": make_bank("w02-l01", "fourth"),
}
V2_CHANGELOG = make_changelog(
    V2,
    V1,
    changelog_entry("lesson", "w01-new", "added"),
    changelog_entry("lesson", "w01-l02", "removed"),
)

# 09:00 UTC on 26 September.
MORNING = datetime(2026, 9, 26, 9, 0, tzinfo=UTC)
CHALLENGE_DAY = "2026-09-26"
"""The Stack's launch, the Day of its Daily Challenge #1."""


def import_version_2(
    session: Session, make_content: ContentFactory, banks: dict[str, Any] = V2_BANKS
) -> None:
    result = import_folder(
        session,
        make_content(as_version(V2, version_2), extra_banks=banks, changelog=V2_CHANGELOG),
    )
    assert (result.status, result.is_current) == ("imported", True)


@pytest.fixture
def learner(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> Iterator[TestClient]:
    """A Learner on version 1 who has completed w01-l01, played the Stack's Daily Challenge #1
    (on 26 September, three of w01-l01's Questions), completed w01-l02 after missing a
    Question and retaking it, ticked w01-m01, and started (not submitted) the Lesson Quiz of
    their Unlocked Lesson, w01-l03."""
    clock.set(MORNING)
    folder = make_content(as_version(V1, version_1), extra_banks=V1_BANKS)
    write_challenges(folder.parent, challenge(1, day=CHALLENGE_DAY), launch=CHALLENGE_DAY)
    import_folder(session, folder)
    onboard(api)
    complete_lessons(session, "w01-l01")
    for question_id, given in zip(CHALLENGE_MIX, ["a", "a", RIGHT], strict=True):
        played = api.post(
            f"{STACK}/challenges/1/answers", json={"question_id": question_id, "answer": given}
        )
        assert played.json()["counted"] is True, played.text
    assert played.json()["challenge"]["status"] == "finished"

    quiz = start(api, quiz_url("w01-l02"))
    result = submit(api, quiz, answer_all(quiz, wrong=1), quiz_url("w01-l02")).json()
    assert result["next_step"] == "retakes"
    [retake] = result["retakes"]
    retaken = api.post(
        f"{STACK}/lessons/w01-l02/retakes/{retake['id']}/answers",
        json={"answer": "a"},
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


PROGRESS_TABLES = (
    LearnerStack,
    CompletedLesson,
    MilestoneTick,
    LessonQuizAttempt,
    Retake,
    Answer,
    ChallengePlay,
)
"""Every table of Learner data. An import writes none of them. Streaks are counted from the
Challenge plays, so they have no table of their own."""


def learner_data(session: Session) -> dict[str, list[tuple[Any, ...]]]:
    """Every row of `PROGRESS_TABLES`, each as the tuple of its columns."""
    session.expire_all()
    data = {}
    for table in PROGRESS_TABLES:
        columns = [c.key for c in table.__mapper__.column_attrs]
        rows = session.scalars(select(table)).all()
        data[table.__tablename__] = sorted(
            (tuple(getattr(row, c) for c in columns) for row in rows), key=repr
        )
    return data


# --- Progress carries over ---------------------------------------------------------------------


def test_an_import_changes_no_learner_data(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    """Completed Lessons, Milestone ticks, quiz attempts, Retakes, Daily Challenge plays and
    every answer (so every Missed Question) are exactly as they were."""
    before = learner_data(session)
    assert before["completed_lessons"] and before["milestone_ticks"] and before["retakes"]
    assert before["challenge_plays"]
    assert missed_in(session, "w01-l02")

    import_version_2(session, make_content)

    assert learner_data(session) == before


def test_the_streak_survives_an_import(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    def streak() -> Any:
        response = learner.get(f"{STACK}/challenges/today")
        assert response.status_code == 200, response.text
        return response.json()["streak"]

    assert streak() == 1

    import_version_2(session, make_content)

    assert streak() == 1


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


@pytest.mark.parametrize(
    ("completed", "states"),
    [
        ((), ["unlocked", "locked", "locked", "locked"]),
        (("w01-l01",), ["updated", "unlocked", "locked", "locked"]),
        (("w01-l01", "w01-l02"), ["updated", "updated", "unlocked", "locked"]),
        (("w01-l01", "w01-l02", "w01-l03"), ["updated", "updated", "completed", "unlocked"]),
        (
            ("w01-l01", "w01-l02", "w01-l03", "w02-l01"),
            ["updated", "updated", "completed", "completed"],
        ),
    ],
    ids=["none", "before-the-removed-lesson", "the-removed-lesson", "past-it", "all"],
)
def test_each_learners_unlocked_lesson_is_still_correct(
    session: Session,
    admin: TestClient,
    signed_in: ClientFactory,
    make_content: ContentFactory,
    completed: tuple[str, ...],
    states: list[str],
) -> None:
    """Learners at every point of version 1's path. The added Lesson is Unlocked for a Learner
    who stood just before it, and behind (Updated) for everyone past it; the changed w01-l01 is
    Updated for everyone who completed it."""
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    email = f"learner-{len(completed)}@example.com"
    admin.post("/invitations", json={"email": email}).raise_for_status()
    client = signed_in(email)
    onboard(client)
    complete_lessons(session, *completed, email=email)

    import_version_2(session, make_content)

    lessons = ["w01-l01", "w01-new", "w01-l03", "w02-l01"]
    assert lesson_states(client) == dict(zip(lessons, states, strict=True))


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


# --- The removed Lesson's Questions -----------------------------------------------------------


def test_the_removed_lessons_questions_stay_in_the_bank_and_no_quiz_draws_them(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)

    kept = session.scalars(
        select(Question).where(Question.id.startswith("w01-l02-")).order_by(Question.id)
    ).all()
    assert [(q.id, q.lesson_id, q.retired_reason) for q in kept] == [
        (f"w01-l02-q{n:02}", None, None) for n in range(1, 9)
    ]
    assert learner.post(quiz_url("w01-l02")).status_code == 404
    fail_the_third_lesson_s_quiz(learner)
    drawn = start(learner, quiz_url("w01-l03"))
    assert all(q["id"].startswith("w01-l03-") for q in drawn["questions"])


# --- Re-tagged and later Questions ------------------------------------------------------------


def owed(session: Session) -> list[str]:
    return updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack")


def reimport_version_2(
    session: Session, make_content: ContentFactory, banks: dict[str, Any]
) -> None:
    """Import version 2 again with a changed Question Bank: the bank grows without a new
    version, as writing a Daily Challenge does."""
    result = import_folder(
        session,
        make_content(as_version(V2, version_2), extra_banks=banks, changelog=V2_CHANGELOG),
    )
    assert result.status == "unchanged"


def mc(question_id: str, lesson: str, concept: str) -> dict[str, Any]:
    question: dict[str, Any] = copy.deepcopy(V2_BANKS["w01-new"]["questions"][0])
    question.update(id=question_id, lesson=lesson, concept=concept)
    return question


def test_a_question_re_tagged_to_a_completed_lesson_is_new_unless_the_learner_answered_it(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    """Version 2 re-tags two of the removed Lesson's Questions to w01-l01: one the Learner
    answered in w01-l02's quiz, and one they never saw. Only the unseen one is owed."""
    answered = set(
        session.scalars(select(Answer.question_id).where(Answer.question_id.startswith("w01-l02")))
    )
    banks = copy.deepcopy(V2_BANKS)
    questions = banks["w01-l02"]["questions"]
    seen = next(q for q in questions if q["id"] in answered)
    unseen = next(q for q in questions if q["id"] not in answered)
    seen["lesson"] = unseen["lesson"] = "w01-l01"

    import_version_2(session, make_content, banks)

    first_lesson = [q for q in owed(session) if not q.startswith("w01-new")]
    assert sorted(first_lesson) == sorted(["w01-l01-q09", unseen["id"]])


def test_a_question_added_to_an_updated_lesson_without_a_new_version_is_new_too(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)
    banks = copy.deepcopy(V2_BANKS)
    banks["w01-new"]["questions"].append(mc("w01-l01-q10", "w01-l01", "new-a"))

    reimport_version_2(session, make_content, banks)

    assert owed(session)[:2] == ["w01-l01-q09", "w01-l01-q10"]


def test_a_question_re_tagged_away_from_an_updated_lesson_is_no_longer_owed(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)
    assert "w01-new-q01" in owed(session)
    banks = copy.deepcopy(V2_BANKS)
    questions = banks["w01-new"]["questions"]
    questions[0]["lesson"] = "w01-l03"
    questions.append(mc("w01-new-q09", "w01-new", "new-a"))

    reimport_version_2(session, make_content, banks)

    assert "w01-new-q01" not in owed(session)
    assert "w01-new-q09" in owed(session)


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

    fresh = start(learner, quiz_url("w01-l03"))
    assert fresh["attempt_id"] != resumed["attempt_id"]
    assert fresh["version"] == V2


def test_a_quiz_in_progress_on_the_removed_lesson_finishes_and_completes_it_on_the_old_version(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    """Passing it makes w01-l02 a Completed Lesson of version 1: it goes in the Learner's
    history, and they reach w01-l03 past it."""
    clock.set(MORNING)
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    onboard(api)
    complete_lessons(session, "w01-l01")
    quiz = start(api, quiz_url("w01-l02"))
    import_version_2(session, make_content)

    result = submit(api, quiz, answer_all(quiz), quiz_url("w01-l02"))
    assert result.status_code == 200, result.text
    assert result.json()["lesson_completed"] is True

    assert [(r["id"], r["version"]) for r in week_map(api)["removed_lessons"]] == [("w01-l02", V1)]
    assert lesson_states(api) == {
        "w01-l01": "updated",
        "w01-new": "updated",
        "w01-l03": "unlocked",
        "w02-l01": "locked",
    }


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


# --- Review --------------------------------------------------------------------------------


def fail_the_third_lesson_s_quiz(client: TestClient) -> list[str]:
    """Submit the w01-l03 quiz started before the update with its first two answers wrong:
    below the Pass Mark. The two Missed Questions, in the order asked."""
    resumed = start(client, quiz_url("w01-l03"))
    submit(client, resumed, answer_all(resumed, wrong=2), quiz_url("w01-l03"))
    return [q["id"] for q in resumed["questions"][:2]]


def test_the_updated_lessons_new_questions_come_after_the_missed_questions(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    """The Missed Questions first, first missed first: the one missed in the removed w01-l02
    stays missed. Then the Updated Lessons' new Questions in Syllabus order: w01-l01's q09, then
    the added Lesson's bank, up to ten. The removed Lesson's other Questions aren't spaced
    repeats: no Lesson has them now."""
    [missed_in_l02] = missed_in(session, "w01-l02")
    import_version_2(session, make_content)
    missed_in_l03 = fail_the_third_lesson_s_quiz(learner)

    questions = asked(learner)

    assert questions == [
        missed_in_l02,
        *missed_in_l03,
        "w01-l01-q09",
        *[f"w01-new-q{n:02}" for n in range(1, 7)],
    ]


def test_the_next_set_asks_the_new_questions_the_first_had_no_room_for(
    session: Session, make_content: ContentFactory, learner: TestClient, clock: FakeClock
) -> None:
    """Once the first set is answered, the next leads with the added Lesson's q07 and q08, and
    none of the first set's Questions come back the same day."""
    import_version_2(session, make_content)
    fail_the_third_lesson_s_quiz(learner)
    clock.advance(minutes=10)
    first = asked(learner)
    for question_id in first:
        answer_right(learner, question_id)

    second = asked(learner)

    assert second[:2] == ["w01-new-q07", "w01-new-q08"]
    assert not set(first) & set(second)


def test_a_new_question_waits_in_review_until_the_learner_answers_it(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    import_version_2(session, make_content)
    owed_before = updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack")
    assert owed_before[0] == "w01-l01-q09"
    assert "w01-l01-q09" in {q["id"] for q in review_set(learner)}

    assert answer(learner, "w01-l01-q09", "b").status_code == 200

    owed = updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack")
    assert owed == owed_before[1:]


def test_nothing_is_owed_before_a_new_version(learner: TestClient, session: Session) -> None:
    assert updated_lessons.updated_question_ids(session, learner_id(session), "mini-stack") == []


# --- The importer ------------------------------------------------------------------------------


def test_each_version_lists_the_questions_tagged_to_its_lessons(
    session: Session, make_content: ContentFactory
) -> None:
    import_folder(session, make_content(as_version(V1, version_1), extra_banks=V1_BANKS))
    import_version_2(session, make_content)

    rows = session.execute(
        select(Lesson.id, Syllabus.version, Lesson.question_ids).join(
            Syllabus, Syllabus.pk == Lesson.syllabus_pk
        )
    ).all()
    tagged = {(lesson, version): ids for lesson, version, ids in rows}
    first_eight = [f"w01-l01-q{n:02}" for n in range(1, 9)]
    assert tagged[("w01-l01", V1)] == first_eight
    assert tagged[("w01-l01", V2)] == [*first_eight, "w01-l01-q09"]
    assert tagged[("w01-l02", V1)] == [f"w01-l02-q{n:02}" for n in range(1, 9)]


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
    # w01-l01 only gained a Question: that is in `question_ids`, not the fingerprint.
    assert by_version[("w01-l01", V1)] == by_version[("w01-l01", V2)]


def import_version_2_editing(
    session: Session,
    make_content: ContentFactory,
    edit: Callable[..., None],
    *changes: dict[str, Any],
) -> None:
    """Import a version 2 that only applies `edit(syllabus, bank)` to version 1, with the
    changelog `changes`."""

    def version(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        version_1(syllabus, bank)
        edit(syllabus, bank)

    result = import_folder(
        session,
        make_content(
            as_version(V2, version),
            extra_banks=V1_BANKS,
            changelog=make_changelog(V2, V1, *changes),
        ),
    )
    assert (result.status, result.is_current) == ("imported", True)


def test_a_completed_lesson_whose_title_changed_is_updated(
    session: Session, make_content: ContentFactory, learner: TestClient
) -> None:
    def retitle(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["weeks"][0]["lessons"][0]["title"] = "First lesson, rewritten"

    import_version_2_editing(
        session, make_content, retitle, changelog_entry("lesson", "w01-l01", "changed")
    )

    assert lesson_states(learner)["w01-l01"] == "updated"
    assert lesson_states(learner)["w01-l02"] == "completed"
    assert owed(session) == []


def test_a_completed_lesson_that_only_lost_a_question_is_not_updated(
    session: Session, make_content: ContentFactory, api: TestClient
) -> None:
    """w01-l01 has nine Questions in version 1; version 2 only retires one. That leaves it
    nothing new for Review, so it stays Completed."""

    def nine_questions(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        version_1(syllabus, bank)
        bank["questions"].append(mc("w01-l01-q09", "w01-l01", "concept-a"))

    def retire_one(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        nine_questions(syllabus, bank)
        bank["questions"][0]["retired"] = {"reason": "Out of date."}

    import_folder(session, make_content(as_version(V1, nine_questions), extra_banks=V1_BANKS))
    onboard(api)
    complete_lessons(session, "w01-l01")
    result = import_folder(
        session,
        make_content(
            as_version(V2, retire_one), extra_banks=V1_BANKS, changelog=make_changelog(V2, V1)
        ),
    )
    assert (result.status, result.is_current) == ("imported", True)

    assert lesson_states(api)["w01-l01"] == "completed"
    assert owed(session) == []


def fingerprints(session: Session) -> dict[str, str | None]:
    return {lesson: h for lesson, h in session.execute(select(Lesson.id, Lesson.content_hash))}


def test_an_import_fills_in_missing_fingerprints(
    session: Session, make_content: ContentFactory
) -> None:
    folder = make_content(as_version(V1, version_1), extra_banks=V1_BANKS)
    import_folder(session, folder)
    stored = fingerprints(session)
    for lesson in session.scalars(select(Lesson)):
        lesson.content_hash = None
    session.flush()

    assert import_folder(session, folder).status == "unchanged"

    assert fingerprints(session) == stored
