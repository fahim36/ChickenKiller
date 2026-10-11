"""Placement coverage is Admin-only; learner placement is added separately."""

from typing import Any

from fastapi import APIRouter

from app.deps import AdminLearner, SessionDep
from app.placement_coverage import coverage

router = APIRouter()


@router.get("/admin/placement-coverage")
def admin_coverage(admin: AdminLearner, session: SessionDep) -> list[dict[str, Any]]:
    return coverage(session)
