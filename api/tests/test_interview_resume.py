"""Changed content and Stack status preserve history while refusing new work."""

import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import InterviewContent, InterviewSession, LearnerStack
from tests.conftest import ContentFactory, FakeClock
from tests.test_interview_audio import setup
from tests.test_interview_feedback import FEEDBACK, enable


def test_changed_reviewed_content_keeps_snapshot_but_refuses_new_work(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": "Use a token."}
    ).raise_for_status()
    enable(api)
    original = api.get(path).json()["prompts"][0]
    content = session.scalar(select(InterviewContent))
    assert content is not None
    content.document = {**content.document, "version": 2, "scenario": "New content."}
    session.commit()
    history = api.get(path).json()
    assert history["prompts"][0] == original
    assert history["practice_state"] == "content_changed"
    with patch("app.interview_provider.feedback") as provider:
        assert (
            api.post(
                path + "/feedback",
                json={
                    "prompt_id": "race-condition",
                    "confirmed": True,
                    "operation_id": str(uuid.uuid4()),
                },
            ).status_code
            == 409
        )
        provider.assert_not_called()
    assert (
        api.post(path + "/turns", json={"parent_id": "race-condition", "kind": "retry"}).status_code
        == 409
    )
    assert api.delete(path).status_code == 204


def test_inactive_stack_keeps_owner_history_and_refuses_new_response(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    record = session.scalar(select(LearnerStack))
    assert record is not None
    record.active = False
    session.commit()
    assert api.get(path).json()["practice_state"] == "inactive_stack"
    assert api.get("/me/interviews").status_code == 200
    assert (
        api.post(
            path + "/responses", json={"prompt_id": "race-condition", "text": "Preserve."}
        ).status_code
        == 409
    )
    assert api.get(path).json()["responses"] == {}


def test_late_feedback_does_not_save_result_after_session_lifetime(
    api: TestClient, session: Session, make_content: ContentFactory, clock: FakeClock
) -> None:
    path = setup(api, session, make_content)
    api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": "Use a token."}
    ).raise_for_status()
    enable(api)
    row = session.scalar(select(InterviewSession))
    assert row is not None
    row.expires_at = clock.now + timedelta(seconds=1)
    session.commit()
    with (
        patch(
            "app.interview_feedback.time", SimpleNamespace(monotonic=Mock(side_effect=[100, 102]))
        ),
        patch("app.interview_provider.feedback", return_value=FEEDBACK),
    ):
        result = api.post(
            path + "/feedback",
            json={
                "prompt_id": "race-condition",
                "confirmed": True,
                "operation_id": str(uuid.uuid4()),
            },
        )
    assert result.json()["state"] == "session_unavailable"
    assert result.json()["feedback"] is None
    clock.advance(seconds=2)
    assert api.get(path).status_code == 404
