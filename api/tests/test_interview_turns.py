"""Optional turns are bounded and use only reviewed content and separate evidence."""

import base64
import json
import uuid
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Answer, Concept, InterviewContent, Question
from tests.conftest import ContentFactory, complete_lessons
from tests.test_interview_audio import setup, wav
from tests.test_interview_feedback import FEEDBACK, enable
from tests.test_interviews import seed


def test_self_review_turn_order_duplicate_limits_and_skips(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    follow = {"parent_id": "race-condition", "kind": "follow_up", "follow_up_id": "replicas"}
    retry = {"parent_id": "race-condition", "kind": "retry"}
    assert api.post(path + "/turns", json=follow).status_code == 409
    api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": "Use a token."}
    ).raise_for_status()
    assert (
        api.post(path + "/turns", json={**follow, "follow_up_id": "unreviewed"}).status_code == 409
    )
    row = api.post(path + "/turns", json=follow).json()
    turn = row["turns"][0]
    assert turn["seconds"] == 45 and turn["scenario"] == "What changes with replicas?"
    assert api.post(path + "/turns", json=retry).status_code == 409
    assert api.post(path + "/turns", json={**follow, "parent_id": turn["id"]}).status_code == 409
    skipped = api.post(path + "/responses", json={"prompt_id": turn["id"], "text": None})
    assert skipped.status_code == 200 and skipped.json()["responses"][turn["id"]] is None
    assert api.post(path + "/turns", json=follow).status_code == 409
    row = api.post(path + "/turns", json=retry).json()
    retry_turn = row["turns"][1]
    assert retry_turn["seconds"] == 60
    assert retry_turn["scenario"] == row["prompts"][0]["scenario"]
    assert retry_turn["rubric"] == row["prompts"][0]["rubric"]
    assert (
        api.post(
            path + "/responses", json={"prompt_id": retry_turn["id"], "text": "Atomic update."}
        ).status_code
        == 200
    )
    assert (
        api.post(
            path + "/responses", json={"prompt_id": retry_turn["id"], "text": "Changed."}
        ).status_code
        == 409
    )
    assert api.post(path + "/turns", json=retry).status_code == 409


def test_optional_voice_limits_come_from_server_turn_kind(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": "Use a token."}
    ).raise_for_status()
    for kind, seconds, follow_up in [("follow_up", 45, "replicas"), ("retry", 60, None)]:
        row = api.post(
            path + "/turns",
            json={"parent_id": "race-condition", "kind": kind, "follow_up_id": follow_up},
        ).json()
        turn = row["turns"][-1]
        body = {
            "prompt_id": turn["id"],
            "recording_id": str(uuid.uuid4()),
            "mime": "audio/wav",
            "data": base64.b64encode(wav(seconds + 0.2)).decode(),
        }
        assert api.post(path + "/audio", json=body).status_code == 422
        valid = api.post(path + "/audio", json={**body, "data": base64.b64encode(wav()).decode()})
        assert valid.status_code == 200
        assert (
            api.post(
                path + "/responses",
                json={
                    "prompt_id": turn["id"],
                    "recording_id": valid.json()["id"],
                    "confirmed": True,
                    "text": "Corrected.",
                },
            ).status_code
            == 200
        )


def test_ai_selection_is_reused_and_optional_feedback_cannot_recurse(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    path = setup(api, session, make_content)
    api.post(
        path + "/responses", json={"prompt_id": "race-condition", "text": "Use a token."}
    ).raise_for_status()
    enable(api)
    with patch(
        "app.interview_provider.generate",
        return_value=json.dumps({**FEEDBACK, "follow_up": "replicas"}),
    ) as provider:
        request = {
            "prompt_id": "race-condition",
            "confirmed": True,
            "operation_id": str(uuid.uuid4()),
        }
        assert api.post(path + "/feedback", json=request).json()["state"] == "complete"
        row = api.post(
            path + "/turns",
            json={"parent_id": "race-condition", "kind": "follow_up", "follow_up_id": "replicas"},
        ).json()
        assert provider.call_count == 1
        turn_id = row["turns"][0]["id"]
        api.post(
            path + "/responses", json={"prompt_id": turn_id, "text": "Use a token."}
        ).raise_for_status()
        result = api.post(
            path + "/feedback",
            json={**request, "prompt_id": turn_id, "operation_id": str(uuid.uuid4())},
        )
        assert result.json()["state"] != "complete"
        provider.return_value = json.dumps({**FEEDBACK, "follow_up": None})
        result = api.post(
            path + "/feedback",
            json={
                **request,
                "prompt_id": turn_id,
                "operation_id": str(uuid.uuid4()),
            },
        )
        assert result.json()["state"] == "complete"
        assert (
            api.post(
                path + "/turns",
                json={"parent_id": turn_id, "kind": "follow_up", "follow_up_id": "replicas"},
            ).status_code
            == 409
        )


def test_three_scenarios_support_nine_responses_without_quiz_evidence(
    api: TestClient, session: Session, make_content: ContentFactory
) -> None:
    seed(session, make_content, api)
    original = session.scalar(select(InterviewContent))
    assert original is not None
    questions = session.scalars(select(Question).order_by(Question.id)).all()
    for index, name in enumerate(["extra-a", "extra-b"]):
        concept = Concept(stack_id="mini-stack", id=name, name=name)
        session.add(concept)
        session.flush()
        questions[2 + index * 2].concept_pk = concept.pk
        document = {**original.document, "id": name, "concept": name}
        session.add(InterviewContent(stack_id="mini-stack", id=name, document=document))
    session.flush()
    complete_lessons(session, "w01-l01")
    row = api.post("/stacks/mini-stack/interviews", json={}).json()
    assert len(row["prompts"]) == 3
    path = "/me/interviews/" + row["id"]
    before = session.scalar(select(func.count()).select_from(Answer))
    assert (
        api.post(
            path + "/responses", json={"prompt_id": row["prompts"][1]["id"], "text": "Too early."}
        ).status_code
        == 409
    )
    for parent in row["prompts"]:
        api.post(
            path + "/responses", json={"prompt_id": parent["id"], "text": "Main."}
        ).raise_for_status()
        for kind, follow_up in [("follow_up", "replicas"), ("retry", None)]:
            opened = api.post(
                path + "/turns",
                json={"parent_id": parent["id"], "kind": kind, "follow_up_id": follow_up},
            )
            assert opened.status_code == 200, opened.text
            turn_id = opened.json()["turns"][-1]["id"]
            api.post(
                path + "/responses", json={"prompt_id": turn_id, "text": "Optional."}
            ).raise_for_status()
    assert len(api.get(path).json()["responses"]) == 9
    assert session.scalar(select(func.count()).select_from(Answer)) == before
