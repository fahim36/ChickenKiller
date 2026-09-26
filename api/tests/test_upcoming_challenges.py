"""Importing a Stack's Daily Challenges (#16), and the Admin page's count of how far ahead they
are written. An Upcoming Challenge may still change at import; a released one (its Day has
passed) never does. Learners never see an Upcoming Challenge's Questions: the Admin page only
counts Days."""

from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.content.loader import ContentError
from app.models import DailyChallenge
from tests.conftest import (
    ContentFactory,
    FakeClock,
    challenge,
    write_challenges,
)

OTHER = ["w01-l01-q02", "w01-l01-q04", "w01-l01-q08"]


def stored(session: Session) -> list[tuple[int, date, list[str]]]:
    session.expire_all()
    return [
        (c.number, c.day, c.question_ids)
        for c in session.scalars(select(DailyChallenge).order_by(DailyChallenge.number))
    ]


@pytest.fixture
def folder(make_content: ContentFactory) -> Path:
    """The test Stack with Challenges #1 to #4 (2026-01-01 to 2026-01-04)."""
    path = make_content()
    write_challenges(path.parent, *(challenge(n) for n in range(1, 5)))
    return path


def test_challenges_are_imported(session: Session, folder: Path) -> None:
    result = import_folder(session, folder, today=date(2026, 1, 1))

    assert result.challenges.added == [1, 2, 3, 4]
    assert stored(session)[0] == (
        1,
        date(2026, 1, 1),
        ["w01-l01-q01", "w01-l01-q03", "w01-l01-q07"],
    )
    assert [n for n, _, _ in stored(session)] == [1, 2, 3, 4]


def test_rerunning_the_import_changes_nothing(session: Session, folder: Path) -> None:
    import_folder(session, folder, today=date(2026, 1, 1))
    before = stored(session)

    again = import_folder(session, folder, today=date(2026, 1, 3))

    assert not again.challenges
    assert stored(session) == before


def test_an_upcoming_challenge_can_change_or_go(session: Session, folder: Path) -> None:
    import_folder(session, folder, today=date(2026, 1, 1))
    write_challenges(folder.parent, *(challenge(n) for n in (1, 2)), challenge(3, questions=OTHER))

    result = import_folder(session, folder, today=date(2026, 1, 2))  # the Day before #3

    assert (result.challenges.updated, result.challenges.removed) == ([3], [4])
    assert [(n, q) for n, _, q in stored(session)][2:] == [(3, OTHER)]


@pytest.mark.parametrize("change", ["edit", "delete"])
@pytest.mark.parametrize("today", [date(2026, 1, 2), date(2026, 1, 3)])
def test_a_released_challenge_is_refused_if_it_changed(
    session: Session, folder: Path, change: str, today: date
) -> None:
    """#2 (2026-01-02) is released from 00:00 UTC on its own Day, and frozen from then on."""
    import_folder(session, folder, today=date(2026, 1, 1))
    session.commit()
    before = stored(session)
    edited = [] if change == "delete" else [challenge(2, questions=OTHER)]
    write_challenges(folder.parent, challenge(1), *edited, challenge(3), challenge(4))

    with pytest.raises(ContentError) as refused:
        import_folder(session, folder, today=today)

    [problem] = refused.value.problems
    assert problem.item == "#2"
    assert "released" in problem.message
    session.rollback()
    assert stored(session) == before


def test_a_challenge_missed_by_an_earlier_import_is_still_added(
    session: Session, folder: Path
) -> None:
    """Committed while upcoming, but imported only after its Day: it was checked at commit."""
    result = import_folder(session, folder, today=date(2026, 1, 9))

    assert result.challenges.added == [1, 2, 3, 4]


def test_an_import_refuses_a_challenge_that_breaks_the_rules(
    session: Session, make_content: ContentFactory
) -> None:
    path = make_content()
    write_challenges(path.parent, challenge(1, questions=["w01-l01-q01", "nope", "w01-l01-q07"]))

    with pytest.raises(ContentError):
        import_folder(session, path, today=date(2026, 1, 1))


# --- The Admin page -------------------------------------------------------------------------------


def ahead(client: TestClient) -> Any:
    response = client.get("/admin/challenges")
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    ("today", "days_left", "warning"),
    [(date(2026, 1, 1), 4, False), (date(2026, 1, 2), 3, False), (date(2026, 1, 3), 2, True)],
)
def test_the_admin_sees_how_far_ahead_challenges_are_written(
    session: Session,
    folder: Path,
    admin: TestClient,
    clock: FakeClock,
    today: date,
    days_left: int,
    warning: bool,
) -> None:
    import_folder(session, folder, today=date(2026, 1, 1))
    clock.set(datetime(today.year, today.month, today.day, 23, 59, tzinfo=UTC))

    assert ahead(admin) == [
        {
            "stack_id": "mini-stack",
            "stack_name": "Mini Stack",
            "written_through": "2026-01-04",
            "days_left": days_left,
            "warning": warning,
        }
    ]


def test_a_stack_with_no_challenges_warns(
    session: Session, make_content: ContentFactory, admin: TestClient
) -> None:
    import_folder(session, make_content())

    [row] = ahead(admin)

    assert (row["written_through"], row["days_left"], row["warning"]) == (None, 0, True)


def test_only_the_admin_sees_it(session: Session, folder: Path, api: TestClient) -> None:
    import_folder(session, folder, today=date(2026, 1, 1))

    assert api.get("/admin/challenges").status_code == 403
