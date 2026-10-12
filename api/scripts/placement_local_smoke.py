"""Isolated localhost API smoke; signed fixture identity, no authentication bypass."""

# Set the isolated database before importing application configuration.
# ruff: noqa: E402
import os
import sys
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "api"))
url = "postgresql+psycopg://learning:learning@127.0.0.1:5433/placement_local?connect_timeout=10"
os.environ["DATABASE_URL"] = url
os.environ["TEST_DATABASE_URL"] = url
import httpx
import uvicorn
from alembic import command
from cryptography.hazmat.primitives.asymmetric import rsa

from app.auth import TokenVerifier
from app.content.importer import import_folder
from app.db import SessionLocal
from app.main import create_app
from tests.conftest import (
    AUTH_SETTINGS,
    LocalKeys,
    _create_database_if_missing,
    alembic_config,
    make_content,
    make_token,
)
from tests.test_placement_coverage import fixture_plan

_create_database_if_missing(url)
command.upgrade(alembic_config(url), "head")
folder = root / ".scratch" / "placement-quizzes" / "local-fixture"
folder.mkdir(parents=True, exist_ok=True)
factory = make_content.__wrapped__(folder)
fixture, _ = fixture_plan(factory)
with SessionLocal() as session:
    import_folder(session, fixture)
    for stack in [
        "agentic-ai-engineer",
        "android-developer",
        "full-stack-web-dev",
        "fullstack-dotnet-developer",
    ]:
        import_folder(session, root / "content" / stack / "v2026-10-10")
    session.commit()
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
tokens = make_token.__wrapped__(key)
app = create_app(TokenVerifier(replace(AUTH_SETTINGS, open_signup=True), LocalKeys(key)))
server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=8011, log_level="warning"))
thread = threading.Thread(target=server.run, daemon=True)
thread.start()
try:
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.1)
    with httpx.Client(base_url="http://127.0.0.1:8011") as client:
        assert client.get("/admin/placement-coverage").status_code == 401
        learner = {"Authorization": "Bearer " + tokens("placement-dummy@example.com")}
        admin = {"Authorization": "Bearer " + tokens("admin@example.com")}
        assert client.get("/admin/placement-coverage", headers=learner).status_code == 403
        response = client.get("/admin/placement-coverage", headers=admin)
        assert response.status_code == 200, response.text
        assert response.json()[0]["weeks"][0]["status"] == "valid"
        client.put(
            "/me/active-stacks", headers=learner, json={"stack_ids": ["mini-stack"]}
        ).raise_for_status()
        quiz = client.post("/stacks/mini-stack/lessons/w01-l01/quiz", headers=learner)
        quiz.raise_for_status()
        from sqlalchemy import select

        from app.models import Learner, QuestionExposure

        with SessionLocal() as session:
            dummy = session.scalar(
                select(Learner).where(Learner.email == "placement-dummy@example.com")
            )
            assert dummy is not None
            exposed = set(
                session.scalars(
                    select(QuestionExposure.question_id).where(
                        QuestionExposure.learner_id == dummy.id
                    )
                )
            )
            assert {q["id"] for q in quiz.json()["questions"]} <= exposed
        print("Local HTTP dummy learner quiz delivery saved exposure without submitted answers")
        fresh = {
            "Authorization": "Bearer "
            + tokens("placement-flow-" + uuid.uuid4().hex + "@example.com")
        }
        client.put(
            "/me/active-stacks", headers=fresh, json={"stack_ids": ["mini-stack"]}
        ).raise_for_status()
        entry = "/stacks/mini-stack/weeks/w01/placement"
        assert client.get(entry, headers=fresh).json()["available"] is True
        with ThreadPoolExecutor(max_workers=2) as pool:
            concurrent = list(pool.map(lambda _: client.post(entry, headers=fresh), range(2)))
        assert all(response.status_code == 201 for response in concurrent)
        assert len({response.json()["id"] for response in concurrent}) == 1
        attempt = concurrent[0]
        attempt.raise_for_status()
        row = attempt.json()
        assert len(row["questions"]) == 10
        assert "answer" not in row["questions"][0]
        path = "/me/placements/" + row["id"]
        question = row["questions"][0]
        answer = ["a", "c"] if question["type"] == "multiple_select" else "a"
        client.post(
            path + "/save", headers=fresh, json={"question_id": question["id"], "answer": answer}
        ).raise_for_status()
        assert client.get(path, headers=fresh).json()["responses"][question["id"]] == answer
        assert client.get(path, headers=admin).status_code == 404
        second = row["questions"][1]
        second_answer = ["a", "c"] if second["type"] == "multiple_select" else "a"
        with ThreadPoolExecutor(max_workers=2) as pool:
            updates = list(
                pool.map(
                    lambda item: client.post(
                        path + "/save",
                        headers=fresh,
                        json={"question_id": item[0], "answer": item[1]},
                    ),
                    [(question["id"], answer), (second["id"], second_answer)],
                )
            )
        assert all(update.status_code == 200 for update in updates)
        responses = client.get(path, headers=fresh).json()["responses"]
        assert responses[question["id"]] == answer and responses[second["id"]] == second_answer
        with ThreadPoolExecutor(max_workers=2) as pool:
            endings = [
                pool.submit(client.post, path + "/abandon", headers=fresh),
                pool.submit(
                    client.post,
                    path + "/save",
                    headers=fresh,
                    json={"question_id": question["id"], "answer": answer},
                ),
            ]
            assert all(item.result().status_code == 200 for item in endings)
        assert client.get(path, headers=fresh).json()["state"] == "abandoned"
        print("Local HTTP placement start/save/resume/private-owner/abandon passed")
        for passing in [True, False]:
            headers = {
                "Authorization": "Bearer " + tokens("ps-" + uuid.uuid4().hex + "@example.com")
            }
            client.put(
                "/me/active-stacks", headers=headers, json={"stack_ids": ["mini-stack"]}
            ).raise_for_status()
            started = client.post(entry, headers=headers).json()
            submit_path = "/me/placements/" + started["id"]
            from app.models import Answer, CompletedLesson, PlacementAttempt

            with SessionLocal() as session:
                private = session.get_one(PlacementAttempt, uuid.UUID(started["id"]))
                questions = private.questions
                owner_id = private.learner_id
            for index, q in enumerate(questions):
                if index in ({0, 5} if passing else {0, 1}):
                    continue
                answer = q["answers"] if q["type"] == "multiple_select" else q["answer"]
                client.post(
                    submit_path + "/save",
                    headers=headers,
                    json={"question_id": q["id"], "answer": answer},
                ).raise_for_status()
            with ThreadPoolExecutor(max_workers=2) as pool:
                future_submit = pool.submit(client.post, submit_path + "/submit", headers=headers)
                future_save = pool.submit(
                    client.post,
                    submit_path + "/save",
                    headers=headers,
                    json={"question_id": questions[2]["id"], "answer": None},
                )
                assert future_save.result().status_code == 200
                first_submission = future_submit.result()
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [
                    pool.submit(client.post, submit_path + "/submit", headers=headers)
                    for _ in range(2)
                ]
                submitted = [future.result() for future in futures]
            assert all(r.status_code == 200 for r in submitted)
            assert submitted[0].json() == submitted[1].json()
            result = submitted[0].json()
            assert result == first_submission.json()
            assert result["result"]["correct"] in {7, 8}
            expected_pass = passing and result["result"]["correct"] == 8
            assert result["result"]["passed"] is expected_pass
            with SessionLocal() as session:
                assert (
                    len(list(session.scalars(select(Answer).where(Answer.learner_id == owner_id))))
                    == 10
                )
                assert len(
                    list(
                        session.scalars(
                            select(CompletedLesson).where(CompletedLesson.learner_id == owner_id)
                        )
                    )
                ) == (2 if expected_pass else 0)
            assert client.get(submit_path, headers=headers).json() == result
        print("Local HTTP duplicate concurrent submission pass/fail and atomic completion passed")
        pilot_headers = {
            "Authorization": "Bearer " + tokens("pilot-" + uuid.uuid4().hex[:12] + "@example.com")
        }
        stacks = [
            "agentic-ai-engineer",
            "android-developer",
            "full-stack-web-dev",
            "fullstack-dotnet-developer",
        ]
        client.put(
            "/me/active-stacks", headers=pilot_headers, json={"stack_ids": stacks}
        ).raise_for_status()
        for stack in stacks:
            response = client.post(f"/stacks/{stack}/weeks/w01/placement", headers=pilot_headers)
            response.raise_for_status()
            assert len(response.json()["questions"]) == (
                25 if stack == "agentic-ai-engineer" else 20
            )
        print("Local HTTP shipped Week1 fresh draws passed for all four Stacks")
        print(
            "Local HTTP instance 127.0.0.1:8011: unauthenticated401, "
            "dummy Learner403, Admin valid coverage200 passed"
        )
finally:
    server.should_exit = True
    thread.join(timeout=10)
