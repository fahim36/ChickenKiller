"""Prompt delivery is recorded independently from submitted answer evidence."""

from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import question_exposure
from app.content.importer import import_folder
from app.models import Answer, QuestionExposure
from tests.conftest import (
    ContentFactory,
    FakeClock,
    challenge,
    complete_lessons,
    onboard,
    write_challenges,
)
from tests.test_lesson_quiz import learner_id


def test_quiz_delivery_without_answer_is_idempotent_and_private(
    session: Session, api: TestClient, admin: TestClient, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())
    onboard(api)
    assert admin.get("/admin/placement-coverage").status_code == 200
    assert session.scalar(select(func.count()).select_from(QuestionExposure)) == 0
    url = "/stacks/mini-stack/lessons/w01-l01/quiz"
    response = api.post(url)
    assert response.status_code == 200
    ids = {q["id"] for q in response.json()["questions"]}
    assert len(ids) == 6
    assert question_exposure.seen(session, learner_id(session), "mini-stack") == ids
    assert session.scalar(select(func.count()).select_from(Answer)) == 0
    api.post(url).raise_for_status()
    assert session.scalar(select(func.count()).select_from(QuestionExposure)) == 6
    assert question_exposure.seen(session, 999999, "mini-stack") == set()


def test_challenge_and_review_delivery_do_not_score_or_complete(
    session: Session, api: TestClient, make_content: ContentFactory, clock: FakeClock
) -> None:
    clock.set(datetime(2026, 1, 1, 10, tzinfo=UTC))
    path = make_content()
    write_challenges(path.parent, challenge(1))
    import_folder(session, path)
    onboard(api)
    today = api.get("/stacks/mini-stack/challenges/today")
    assert today.status_code == 200
    ids = {q["id"] for q in today.json()["challenge"]["questions"]}
    assert ids <= question_exposure.seen(session, learner_id(session), "mini-stack")
    assert today.json()["streak"] == 0
    assert session.scalar(select(func.count()).select_from(Answer)) == 0
    complete_lessons(session, "w01-l01")
    review = api.get("/review")
    assert review.status_code == 200
    reviewed = {q["id"] for q in review.json()["questions"]}
    assert reviewed <= question_exposure.seen(session, learner_id(session), "mini-stack")
    archive = api.get("/stacks/mini-stack/challenges/1")
    assert archive.status_code == 200
    assert archive.json()["challenge"]["score"] is None
