"""Importing the Stack's Question Bank (#15): Questions with their Sources, retirements and
re-tags. The bank is append-only, so re-running an import changes nothing, and an edited
Question is refused."""

from datetime import date
from typing import Any

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.content.importer import import_folder
from app.content.loader import ContentError
from app.models import Concept, Question, QuestionMaterial, QuestionSource, Syllabus
from tests.conftest import (
    ContentFactory,
    as_version,
    changelog_entry,
    make_bank,
    make_changelog,
    mc_question,
    source,
)

Q01 = "w01-l01-q01"


def question(session: Session, qid: str = Q01) -> Question:
    return session.scalars(select(Question).where(Question.id == qid)).one()


def snapshot(session: Session) -> list[tuple[Any, ...]]:
    session.expire_all()
    rows = session.scalars(select(Question).order_by(Question.id)).all()
    return [
        (
            q.pk,
            q.id,
            q.lesson_id,
            q.position,
            q.retired_reason,
            q.replaced_by,
            q.retired_on,
            [(s.position, s.url, s.accessed) for s in q.sources],
            [(m.material_pk, m.position) for m in q.material_links],
        )
        for q in rows
    ]


def retire_q01(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
    bank["questions"][0]["retired"] = {
        "reason": "The API changed.",
        "replaced_by": "w01-l01-q09",
        "on": "2026-01-02",
    }
    bank["questions"].append(mc_question("w01-l01-q09", "concept-a"))


def test_questions_are_loaded_with_their_sources(
    session: Session, make_content: ContentFactory
) -> None:
    def two_sources(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["sources"].append(source(2, "2025-12-31"))

    result = import_folder(session, make_content(two_sources))

    assert len(result.bank.added) == 8
    q01 = question(session)
    assert (q01.stack_id, q01.lesson_id, q01.concept.id, q01.retired) == (
        "mini-stack",
        "w01-l01",
        "concept-a",
        False,
    )
    assert [(s.url, s.title, s.publisher, s.accessed, s.claim) for s in q01.sources] == [
        (
            "https://example.com/docs/page-1",
            "Docs page 1",
            "Example",
            date(2026, 1, 1),
            "What the Question relies on.",
        ),
        (
            "https://example.com/docs/page-2",
            "Docs page 2",
            "Example",
            date(2025, 12, 31),
            "What the Question relies on.",
        ),
    ]
    assert session.scalar(select(func.count()).select_from(QuestionSource)) == 9


def test_a_retirement_is_loaded(session: Session, make_content: ContentFactory) -> None:
    import_folder(session, make_content())

    result = import_folder(session, make_content(retire_q01))

    assert (result.status, result.bank.added, result.bank.retired) == (
        "unchanged",
        ["w01-l01-q09"],
        [Q01],
    )
    q01 = question(session)
    assert (q01.retired, q01.retired_reason, q01.replaced_by, q01.retired_on) == (
        True,
        "The API changed.",
        "w01-l01-q09",
        date(2026, 1, 2),
    )


def test_a_retag_is_loaded(session: Session, make_content: ContentFactory) -> None:
    import_folder(session, make_content())

    def retag(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["lesson"] = None
        bank["questions"].append(mc_question("w01-l01-q09", "concept-a"))  # keeps w01-l01 at 8

    result = import_folder(session, make_content(retag))

    assert result.bank.retagged == [Q01]
    assert question(session).lesson_id is None


def test_rerunning_the_import_changes_nothing(
    session: Session, make_content: ContentFactory
) -> None:
    folder = make_content(retire_q01, extra_banks={"w01-l02": make_bank("w01-l02", "second")})
    import_folder(session, folder)
    before = snapshot(session)

    again = import_folder(session, folder)

    assert (again.status, bool(again.bank)) == ("unchanged", False)
    assert snapshot(session) == before
    assert session.scalar(select(func.count()).select_from(Concept)) == 8


def test_an_edited_question_is_refused(session: Session, make_content: ContentFactory) -> None:
    import_folder(session, make_content())

    def edit(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"][0]["prompt"] = "Quietly edited?"

    with pytest.raises(ContentError, match="already imported with different content: a Question"):
        import_folder(session, make_content(edit))
    assert question(session).prompt == "Question 1?"


def test_a_retirement_is_never_undone(session: Session, make_content: ContentFactory) -> None:
    import_folder(session, make_content(retire_q01))

    def unretire(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        bank["questions"].append(mc_question("w01-l01-q09", "concept-a"))

    with pytest.raises(ContentError, match="already retired: a retirement is final"):
        import_folder(session, make_content(unretire))


def test_a_question_left_out_of_the_files_stays(
    session: Session, make_content: ContentFactory
) -> None:
    """The content check refuses deleting a committed Question; the import never deletes one."""
    import_folder(session, make_content(retire_q01))

    def without_q01(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        retire_q01(syllabus, bank)
        del bank["questions"][0]

    import_folder(session, make_content(without_q01))

    assert question(session).retired


def test_question_materials_follow_the_current_syllabus(
    session: Session, make_content: ContentFactory
) -> None:
    import_folder(session, make_content())

    def newer(syllabus: dict[str, Any], bank: dict[str, Any]) -> None:
        syllabus["weeks"][0]["lessons"][0]["title"] = "Revised"

    changelog = make_changelog(
        "v2026-02-01", "v2026-01-01", changelog_entry("lesson", "w01-l01", "changed")
    )
    import_folder(session, make_content(as_version("v2026-02-01", newer), changelog=changelog))

    current = session.scalars(select(Syllabus.pk).where(Syllabus.version == "v2026-02-01")).one()
    q01 = question(session)
    assert [m.id for m in q01.materials] == ["mat-docs"]
    assert {m.syllabus_pk for m in q01.materials} == {current}
    assert session.scalar(select(func.count()).select_from(QuestionMaterial)) == 6
