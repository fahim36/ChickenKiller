"""The placement selector covers essential Concepts without seen fallbacks."""

import random

import pytest

from app.content.placement import PlacementLesson
from app.placement_selection import FreshCoverageUnavailable, draw_lesson


def blueprint() -> PlacementLesson:
    return PlacementLesson(
        lesson="w01-l01",
        count=5,
        essential_concepts=["a", "b", "c"],
        questions=[f"q{i}" for i in range(8)],
        rationale="Core teaching objectives",
    )


def test_fresh_draw_covers_every_essential_concept() -> None:
    concepts = {f"q{i}": "abc"[i % 3] for i in range(8)}
    for seed in range(20):
        drawn = draw_lesson(blueprint(), concepts, {"q0", "q1"}, random.Random(seed))
        assert len(drawn) == len(set(drawn)) == 5
        assert not {"q0", "q1"}.intersection(drawn)
        assert {concepts[qid] for qid in drawn} == {"a", "b", "c"}


def test_sparse_essential_coverage_cannot_be_hidden_by_many_fillers() -> None:
    concepts = {f"q{i}": "a" if i < 6 else "b" for i in range(8)}
    with pytest.raises(FreshCoverageUnavailable):
        draw_lesson(blueprint(), concepts, set(), random.Random(1))


def test_insufficient_fresh_questions_never_falls_back_to_seen() -> None:
    concepts = {f"q{i}": "abc"[i % 3] for i in range(8)}
    with pytest.raises(FreshCoverageUnavailable):
        draw_lesson(blueprint(), concepts, {"q0", "q1", "q2", "q3"}, random.Random(1))
