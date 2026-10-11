"""The 32 researched variants import and answer through normal Review eligibility."""

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.config import REPO_ROOT
from app.content.importer import import_folder
from app.content.loader import read_bank
from tests.conftest import FakeClock, complete_lessons, onboard

VARIANTS = {
    "agentic-ai-engineer": {
        "w01-l01-q13",
        "w01-l01-q14",
        "w01-l02-q11",
        "w01-l02-q12",
        "w02-l03-q15",
        "w02-l03-q16",
        "w02-l04-q16",
        "w02-l04-q17",
    },
    "android-developer": {
        "w01-l01-q12",
        "w01-l01-q13",
        "w02-l02-q12",
        "w02-l02-q13",
        "w02-l03-q12",
        "w02-l03-q13",
        "w02-l04-q12",
        "w02-l04-q13",
    },
    "full-stack-web-dev": {
        "w01-l03-q11",
        "w01-l03-q12",
        "w02-l02-q11",
        "w02-l02-q12",
        "w02-l03-q11",
        "w02-l03-q12",
        "w02-l04-q11",
        "w02-l04-q12",
    },
    "fullstack-dotnet-developer": {
        "w01-l01-q12",
        "w01-l01-q13",
        "w01-l03-q12",
        "w01-l03-q13",
        "w02-l01-q12",
        "w02-l01-q13",
        "w02-l03-q12",
        "w02-l03-q13",
    },
}


@pytest.mark.parametrize("stack_id", VARIANTS)
def test_new_variants_import_and_answer_in_review(
    session: Session, api: TestClient, clock: FakeClock, stack_id: str
) -> None:
    stack_dir = REPO_ROOT / "content" / stack_id
    bank, problems = read_bank(stack_dir)
    assert not problems
    questions = {q.id: q for q in bank.live_questions()}
    variants = VARIANTS[stack_id]
    import_folder(session, stack_dir / "v2026-10-10")
    onboard(api, stack_id)
    clock.set(datetime(2026, 10, 11, 12, tzinfo=UTC))
    assert api.get("/review").json()["questions"] == []
    lessons = {questions[qid].lesson for qid in variants}
    assert None not in lessons
    complete_lessons(
        session, *(lesson for lesson in sorted(lessons, key=str) if lesson), stack_id=stack_id
    )
    for qid in sorted(variants):
        q = questions[qid]
        assert q.type in {"multiple_choice", "multiple_select"}
        response = api.post(
            "/review/answers",
            json={
                "stack_id": stack_id,
                "question_id": qid,
                "answer": q.answer if q.type == "multiple_choice" else q.answers,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["correct"] is True
