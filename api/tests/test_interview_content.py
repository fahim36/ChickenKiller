"""Reviewed prompts reject malformed follow-ups before publication."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.content.interviews import InterviewPrompt, check_prompts


def prompt() -> dict[str, object]:
    return {
        "id": "race-condition",
        "stack": "dotnet",
        "concept": "concurrency",
        "lesson": "w01-l01",
        "version": 1,
        "scenario": "Two requests update a balance.",
        "rubric": ["Explain the race and an atomic update."],
        "misconceptions": ["A process-local lock protects every replica."],
        "sources": [
            {
                "url": "https://learn.microsoft.com/",
                "title": "Documentation",
                "publisher": "Microsoft",
                "accessed": "2026-10-11",
                "claim": "Concurrency requires coordination.",
            }
        ],
        "follow_ups": [
            {
                "id": "replicas",
                "scenario": "What changes with replicas?",
                "rubric": ["Coordinate at the shared data store."],
            }
        ],
    }


def test_reviewed_prompt_requires_unique_follow_up_ids() -> None:
    data = prompt()
    follow = data["follow_ups"]
    assert isinstance(follow, list)
    data["follow_ups"] = follow * 2
    with pytest.raises(ValidationError, match="unique"):
        InterviewPrompt.model_validate(data)


def test_reviewed_prompt_rejects_missing_rubric_and_unknown_fields() -> None:
    data = prompt()
    data["rubric"] = []
    data["generated_question"] = True
    with pytest.raises(ValidationError):
        InterviewPrompt.model_validate(data)


def test_reviewed_prompt_round_trips_snapshot() -> None:
    reviewed = InterviewPrompt.model_validate(prompt())
    assert InterviewPrompt.model_validate_json(reviewed.model_dump_json()) == reviewed


def test_teaching_lesson_must_match_concept(tmp_path: Path) -> None:
    stack = tmp_path / "dotnet"
    (stack / "interviews").mkdir(parents=True)
    (stack / "interviews" / "prompt.json").write_text(json.dumps(prompt()), encoding="utf-8")
    with pytest.raises(ValueError, match="must teach"):
        check_prompts(stack, {"concurrency"}, {"w01-l01", "w01-l02"}, {("concurrency", "w01-l02")})
