"""The lock-state rule: which of a Syllabus's Lessons are Completed, Unlocked or Locked.

A plain function with no database or HTTP, so the rule is tested directly
(tests/test_unlocking.py). The Week map and the Lesson Quiz guard both get their states from
here, through `progress.lesson_states_for`.

- The **Unlocked Lesson** is the next Lesson after the Learner's last Completed Lesson, in
  Syllabus order. "Last" means furthest along, so pacing follows completion only, never the
  calendar.
- While a **Pending Review Round** exists, the Unlocked Lesson is locked too (#9 supplies it).
- Every Lesson after the Unlocked Lesson is a **Locked Lesson**.
- A Lesson behind the Learner's position that isn't Completed can only appear when a Syllabus
  Update adds one there. It never becomes the Unlocked Lesson; #13 shows it as an Updated
  Lesson, and until then it counts as locked.
- Completed Lessons that a later Syllabus version removed are ignored: they stay in the
  Learner's history but are not on the path.
"""

from collections.abc import Collection, Sequence
from typing import Literal

LessonState = Literal["completed", "unlocked", "locked"]


def lesson_states(
    lesson_ids: Sequence[str],
    completed_ids: Collection[str],
    *,
    pending_review_round: bool = False,
) -> dict[str, LessonState]:
    """Each Lesson's state, keyed by permanent ID, in Syllabus order.

    `lesson_ids` are the current Syllabus's Lessons in order; `completed_ids` the Learner's
    Completed Lessons on that Stack.
    """
    furthest = max(
        (i for i, lesson in enumerate(lesson_ids) if lesson in completed_ids), default=-1
    )
    unlocked = furthest + 1
    states: dict[str, LessonState] = {}
    for i, lesson in enumerate(lesson_ids):
        if lesson in completed_ids:
            states[lesson] = "completed"
        elif i == unlocked and not pending_review_round:
            states[lesson] = "unlocked"
        else:
            states[lesson] = "locked"
    return states
