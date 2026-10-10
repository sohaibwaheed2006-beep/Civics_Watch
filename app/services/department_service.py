"""Department business logic."""

from __future__ import annotations

from typing import Sequence

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.logging import get_logger
from app.models.department import Department
from app.models.user import User
from app.repositories import department_repository
from app.schemas.department import DepartmentCreate, DepartmentUpdate

logger = get_logger(__name__)

__all__ = ["list_departments", "get_department", "create_department", "update_department"]


def list_departments(
    db: Session,
    *,
    offset: int,
    limit: int,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    descending: bool = False,
) -> tuple[Sequence[Department], int]:
    """One page of departments plus the total matching count."""
    total = department_repository.count_departments(
        db, is_active=is_active, search=search
    )
    items = department_repository.list_departments(
        db,
        offset=offset,
        limit=limit,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        descending=descending,
    )
    return items, total


def get_department(db: Session, department_id: int) -> Department:
    """Fetch one department.

    Raises
    ------
    NotFoundError
        No department with that ID (404).
    """
    department = department_repository.get_by_id(db, department_id)
    if department is None:
        raise NotFoundError("Department not found.")
    return department


def create_department(
    db: Session, *, actor: User, payload: DepartmentCreate
) -> Department:
    """Create a department.

    Raises
    ------
    ConflictError
        A department with that name already exists (409). The name check is
        case-insensitive, so "Roads" and "roads" cannot coexist.
    """
    if department_repository.name_exists(db, payload.name):
        raise ConflictError(f"A department named {payload.name!r} already exists.")

    try:
        department = department_repository.create(
            db,
            name=payload.name,
            description=payload.description,
            default_sla_hours=payload.default_sla_hours,
            is_active=payload.is_active,
        )
        db.commit()
    except IntegrityError:
        # The unique index is the real guarantee; the pre-check above only
        # loses to a concurrent insert of the same name.
        db.rollback()
        raise ConflictError(
            f"A department named {payload.name!r} already exists."
        ) from None

    logger.info(
        "Admin id=%s created department id=%s", actor.id, department.id
    )
    return department


def update_department(
    db: Session, *, actor: User, department_id: int, payload: DepartmentUpdate
) -> Department:
    """Apply a partial update to a department.

    Only the fields the client sent are written, so ``description: null``
    clears the description while an omitted ``description`` leaves it alone.

    Setting ``is_active=false`` is the supported way to retire a department:
    it keeps the row, so workers and historical reports that reference it
    still resolve. Nothing here deletes a department.

    Raises
    ------
    NotFoundError
        No department with that ID (404).
    ConflictError
        The requested name is already taken by another department (409).
    """
    department = department_repository.get_by_id(db, department_id)
    if department is None:
        raise NotFoundError("Department not found.")

    changes = payload.model_dump(exclude_unset=True)

    new_name = changes.get("name")
    if new_name is not None and department_repository.name_exists(
        db, new_name, exclude_id=department_id
    ):
        raise ConflictError(f"A department named {new_name!r} already exists.")

    try:
        for field, value in changes.items():
            setattr(department, field, value)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise ConflictError("That department name is already in use.") from None

    logger.info(
        "Admin id=%s updated department id=%s fields=%s",
        actor.id,
        department_id,
        sorted(changes),
    )
    return department
