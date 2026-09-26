"""The lock-state rule (app/unlocking.py): which Lessons are Completed, Unlocked or Locked."""

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


def test_a_pending_review_round_locks_the_unlocked_lesson_too() -> None:
    assert lesson_states(SYLLABUS, {"w01-l01"}, pending_review_round=True) == {
        "w01-l01": "completed",
        "w01-l02": "locked",
        "w01-l03": "locked",
        "w02-l01": "locked",
    }


def test_a_pending_review_round_does_not_undo_completed_lessons() -> None:
    states = lesson_states(SYLLABUS, set(SYLLABUS), pending_review_round=True)

    assert set(states.values()) == {"completed"}


def test_completed_lessons_no_longer_in_the_syllabus_are_ignored() -> None:
    """A Lesson a later Syllabus version removed stays in the Learner's history only."""
    assert lesson_states(SYLLABUS, {"w01-l01", "removed-lesson"}) == {
        "w01-l01": "completed",
        "w01-l02": "unlocked",
        "w01-l03": "locked",
        "w02-l01": "locked",
    }


def test_the_unlocked_lesson_follows_the_furthest_completed_lesson() -> None:
    """A Lesson a Syllabus Update adds behind the Learner never becomes their Unlocked Lesson
    (#13 shows it as an Updated Lesson); until then it counts as locked."""
    states = lesson_states(SYLLABUS, {"w01-l01", "w01-l03"})

    assert states == {
        "w01-l01": "completed",
        "w01-l02": "locked",
        "w01-l03": "completed",
        "w02-l01": "unlocked",
    }


def test_the_states_come_back_in_syllabus_order() -> None:
    assert list(lesson_states(SYLLABUS, {"w01-l01"})) == SYLLABUS
