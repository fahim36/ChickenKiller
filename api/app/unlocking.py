"""The lock-state rule: which of a Syllabus's Lessons are Completed, Updated, Unlocked or Locked.

A plain function with no database or HTTP, so the rule is tested directly
(tests/test_unlocking.py). The Week map and the Lesson Quiz guard both get their states from
here, through `progress.lesson_states`.

- The **Unlocked Lesson** is the next Lesson after the Learner's furthest Completed Lesson, in
  the current Syllabus order. So pacing follows completion only, never the calendar.
- When a later version removed a Completed Lesson, the Learner has still **reached** the Lesson
  that came after it (`reached_ids`, #13, worked out by `updated_lessons.standing`): the Unlocked
  Lesson is never before it, and every Lesson before it is behind the Learner. So when the
  furthest Completed Lesson is removed, the next Lesson after it that survived unlocks.
- While a **Pending Review Round** exists, the Unlocked Lesson is locked too (#9).
- Every Lesson after the Unlocked Lesson is a **Locked Lesson**.
- An **Updated Lesson** (#13) is either a Completed Lesson that changed since the version it
  was completed in (`changed_ids`), or a Lesson behind the Learner's position that isn't
  Completed, which only a Syllabus Update can put there. It never becomes the Unlocked Lesson
  and never locks anything: its new Questions go into the Daily Review instead.
- Completed Lessons that a later Syllabus version removed are ignored: they stay in the
  Learner's history but are not on the path.
"""

from collections.abc import Collection, Sequence
from typing import Literal

LessonState = Literal["completed", "updated", "unlocked", "locked"]


def lesson_states(
    lesson_ids: Sequence[str],
    completed_ids: Collection[str],
    *,
    changed_ids: Collection[str] = (),
    reached_ids: Collection[str] = (),
    pending_review_round: bool = False,
) -> dict[str, LessonState]:
    """Each Lesson's state, keyed by permanent ID, in Syllabus order.

    - `lesson_ids` are the current Syllabus's Lessons in order;
    - `completed_ids` the Learner's Completed Lessons on that Stack (any version);
    - `changed_ids` the Completed Lessons whose content differs from the version they were
      completed in (only Completed ones count);
    - `reached_ids` Lessons the Learner has reached without completing them: each follows a
      Completed Lesson a later version removed.
    """
    unlocked = max(
        [i + 1 for i, lesson in enumerate(lesson_ids) if lesson in completed_ids]
        + [i for i, lesson in enumerate(lesson_ids) if lesson in reached_ids],
        default=0,
    )
    states: dict[str, LessonState] = {}
    for i, lesson in enumerate(lesson_ids):
        if lesson in completed_ids:
            states[lesson] = "updated" if lesson in changed_ids else "completed"
        elif i < unlocked:
            states[lesson] = "updated"
        elif i == unlocked and not pending_review_round:
            states[lesson] = "unlocked"
        else:
            states[lesson] = "locked"
    return states
