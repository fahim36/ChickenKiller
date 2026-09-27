"""The lock-state rule (app/unlocking.py): which Lessons are Completed, Updated, Unlocked or
Locked. Lock states depend only on Completed Lessons (and, after a Syllabus Update, how the
Syllabus changed since): the rule takes nothing else, so neither the calendar, Milestone ticks
nor Review can lock a Lesson (test_week_map.py and test_review.py check that over the API)."""

from app.unlocking import lesson_states

SYLLABUS = ["w01-l01", "w01-l02", "w01-l03", "w02-l01"]


def test_a_new_learner_has_only_the_first_lesson_unlocked() -> None:
    assert lesson_states(SYLLABUS, set()) == {
        "w01-l01": "unlocked",
        "w01-l02": "locked",
        "w01-l03": "locked",
        "w02-l01": "locked",
    }


def test_the_lesson_after_the_last_completed_lesson_is_unlocked() -> None:
    assert lesson_states(SYLLABUS, {"w01-l01", "w01-l02"}) == {
        "w01-l01": "completed",
        "w01-l02": "completed",
        "w01-l03": "unlocked",
        "w02-l01": "locked",
    }


def test_unlocking_crosses_into_the_next_week() -> None:
    states = lesson_states(SYLLABUS, {"w01-l01", "w01-l02", "w01-l03"})

    assert states["w02-l01"] == "unlocked"


def test_with_every_lesson_completed_nothing_is_unlocked_or_locked() -> None:
    assert set(lesson_states(SYLLABUS, set(SYLLABUS)).values()) == {"completed"}


def test_completed_lessons_no_longer_in_the_syllabus_are_ignored() -> None:
    """A Lesson a later Syllabus version removed stays in the Learner's history only."""
    assert lesson_states(SYLLABUS, {"w01-l01", "removed-lesson"}) == {
        "w01-l01": "completed",
        "w01-l02": "unlocked",
        "w01-l03": "locked",
        "w02-l01": "locked",
    }


def test_the_unlocked_lesson_follows_the_furthest_completed_lesson() -> None:
    """A Lesson a Syllabus Update adds behind the Learner never becomes their Unlocked Lesson:
    it is an Updated Lesson."""
    states = lesson_states(SYLLABUS, {"w01-l01", "w01-l03"})

    assert states == {
        "w01-l01": "completed",
        "w01-l02": "updated",
        "w01-l03": "completed",
        "w02-l01": "unlocked",
    }


# --- After a Syllabus Update (#13) ------------------------------------------------------------


def test_a_completed_lesson_that_changed_since_it_was_completed_is_updated() -> None:
    states = lesson_states(SYLLABUS, {"w01-l01", "w01-l02"}, changed_ids={"w01-l01"})

    assert states == {
        "w01-l01": "updated",
        "w01-l02": "completed",
        "w01-l03": "unlocked",
        "w02-l01": "locked",
    }


def test_an_updated_lesson_locks_nothing() -> None:
    """Updated Lessons, changed or added behind the Learner, never hold back the Unlocked
    Lesson."""
    states = lesson_states(SYLLABUS, {"w01-l01", "w01-l03"}, changed_ids={"w01-l03"})

    assert states["w01-l02"] == "updated"
    assert states["w01-l03"] == "updated"
    assert states["w02-l01"] == "unlocked"


def test_a_change_to_a_lesson_the_learner_has_not_completed_is_not_an_update() -> None:
    states = lesson_states(SYLLABUS, {"w01-l01"}, changed_ids={"w01-l02", "w01-l03"})

    assert states["w01-l02"] == "unlocked"
    assert states["w01-l03"] == "locked"


def test_a_lesson_added_ahead_of_the_learner_is_simply_locked() -> None:
    added_ahead = ["w01-l01", "w01-l02", "new-lesson", "w01-l03"]

    states = lesson_states(added_ahead, {"w01-l01"})

    assert states["w01-l02"] == "unlocked"
    assert states["new-lesson"] == "locked"


def test_when_the_furthest_completed_lesson_is_removed_the_next_surviving_lesson_unlocks() -> None:
    """The Learner completed w01-l01 to w01-l03, then a version removed w01-l03 and added
    `replacement` in its place. The Lesson that followed w01-l03 is `reached_ids`: it unlocks,
    and every Lesson before it is behind the Learner."""
    after_removal = ["w01-l01", "w01-l02", "replacement", "w02-l01", "w02-l02"]

    states = lesson_states(
        after_removal, {"w01-l01", "w01-l02", "w01-l03"}, reached_ids={"w02-l01"}
    )

    assert states == {
        "w01-l01": "completed",
        "w01-l02": "completed",
        "replacement": "updated",
        "w02-l01": "unlocked",
        "w02-l02": "locked",
    }


def test_a_reached_lesson_never_moves_the_learner_back() -> None:
    states = lesson_states(SYLLABUS, {"w01-l01", "w01-l02", "w01-l03"}, reached_ids={"w01-l02"})

    assert states["w02-l01"] == "unlocked"


def test_without_a_reached_lesson_a_removed_completed_lesson_is_just_ignored() -> None:
    assert lesson_states(["w01-l01", "w01-l02", "w02-l01"], {"w01-l01", "w01-l03"}) == {
        "w01-l01": "completed",
        "w01-l02": "unlocked",
        "w02-l01": "locked",
    }


def test_the_states_come_back_in_syllabus_order() -> None:
    assert list(lesson_states(SYLLABUS, {"w01-l01"})) == SYLLABUS
