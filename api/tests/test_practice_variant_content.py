"""Ticket 07: imported variants become usable through ordinary Review eligibility."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import REPO_ROOT
from app.content.importer import import_folder
from app.content.loader import read_bank
from tests.conftest import FakeClock, complete_lessons, onboard

VARIANTS = {
    "agentic-ai-engineer": {"w01-l01-q11", "w01-l01-q12", "c001-q09", "c001-q10"},
    "android-developer": {"w04-l01-q12", "w04-l01-q13", "w04-l02-q12", "w04-l02-q13"},
    "full-stack-web-dev": {"c065-q07", "c065-q08", "c065-q09", "c065-q10"},
    "fullstack-dotnet-developer": {"w09-l03-q12", "w09-l03-q13", "w06-l04-q12", "w06-l04-q13"},
}
CHALLENGE_DAYS = {
    "agentic-ai-engineer": [(20, 24)],
    "full-stack-web-dev": [(20, 11), (21, 12)],
}


@pytest.mark.parametrize("stack_id", VARIANTS)
def test_variants_are_answerable_in_eligible_review_after_import(
    session: Session, api: TestClient, clock: FakeClock, stack_id: str
) -> None:
    stack_dir = REPO_ROOT / "content" / stack_id
    bank, problems = read_bank(stack_dir)
    assert not problems
    questions = {q.id: q for q in bank.live_questions()}
    variants = VARIANTS[stack_id]
    # Import the reviewed release through the production content importer, not a fake bank.
    import_folder(session, stack_dir / "v2026-10-10")
    onboard(api, stack_id)
    clock.set(datetime(2026, 10, 10, 12, tzinfo=UTC))
    assert api.get("/review").json()["questions"] == []

    def given(qid: str) -> str | list[str]:
        q = questions[qid]
        if q.type == "multiple_choice":
            return q.answer
        assert q.type == "multiple_select"
        return q.answers

    lesson_ids = {lesson_id for qid in variants if (lesson_id := questions[qid].lesson) is not None}
    complete_lessons(session, *sorted(lesson_ids), stack_id=stack_id)
    for day, number in CHALLENGE_DAYS.get(stack_id, []):
        clock.set(datetime(2026, 10, day, 12, tzinfo=UTC))
        challenge = api.get(f"/stacks/{stack_id}/challenges/today").json()["challenge"]
        assert challenge["number"] == number
        for question in challenge["questions"]:
            response = api.post(
                f"/stacks/{stack_id}/challenges/{number}/answers",
                json={"question_id": question["id"], "answer": given(question["id"])},
            )
            assert response.status_code == 200, response.text
            assert response.json()["outcome"] == "correct"

    clock.set(datetime(2026, 10, 24, 12, tzinfo=UTC))
    # Review accepts any currently due Question, even beyond its first ten-item page.
    # Completing a later Lesson also makes earlier Lessons eligible, so that page can
    # contain older material; do not bypass eligibility or fabricate Answer evidence.
    for question in api.get("/review").json()["questions"]:
        assert "answer" not in question and "answers" not in question
    for qid in sorted(variants):
        response = api.post(
            "/review/answers",
            json={"stack_id": stack_id, "question_id": qid, "answer": given(qid)},
        )
        assert response.status_code == 200, response.text
        assert response.json()["correct"] is True
        # Correctly answered repeats are no longer due on the same UTC Day.
        repeated = api.post(
            "/review/answers",
            json={"stack_id": stack_id, "question_id": qid, "answer": given(qid)},
        )
        assert repeated.status_code == 409, repeated.text
