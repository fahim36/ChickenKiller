"""Placement draws must prove the reviewed coverage, never relax freshness."""

import random
from collections.abc import Collection, Mapping

from app.content.placement import PlacementLesson


class FreshCoverageUnavailable(Exception):
    """There is no valid fresh draw for a reviewed Lesson blueprint."""


def draw_lesson(
    blueprint: PlacementLesson,
    concepts: Mapping[str, str],
    unavailable: Collection[str],
    rng: random.Random,
) -> list[str]:
    """One Question per essential Concept, then fresh fillers to the reviewed count.

    `concepts` contains only active suitable Questions in the teaching Lesson. Unavailable
    includes delivered Questions and ones already assigned to another unfinished practice.
    """
    pool = [qid for qid in blueprint.questions if qid in concepts and qid not in unavailable]
    if len(pool) < blueprint.count:
        raise FreshCoverageUnavailable(blueprint.lesson)
    picked: list[str] = []
    for concept in blueprint.essential_concepts:
        candidates = [qid for qid in pool if concepts[qid] == concept]
        if not candidates:
            raise FreshCoverageUnavailable(blueprint.lesson)
        picked.append(rng.choice(candidates))
    remaining = [qid for qid in pool if qid not in picked]
    picked.extend(rng.sample(remaining, blueprint.count - len(picked)))
    rng.shuffle(picked)
    return picked
