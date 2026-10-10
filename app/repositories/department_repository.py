"""Department persistence.

Query construction only; the calling service owns the transaction boundary.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.models.department import Department
from app.models.user import User

__all__ = [
    "get_by_id",
    "get_by_name",
    "name_exists",
    "create",
    "list_departments",
    "count_departments",
    "count_assigned_users",
    "SORTABLE_FIELDS",
]

#: Columns a client may sort the department list by.
SORTABLE_FIELDS: dict[str, object] = {
    "id": Department.id,
    "name": Department.name,
    "default_sla_hours": Department.default_sla_hours,
    "created_at": Department.created_at,
    "updated_at": Department.updated_at,
}

DEFAULT_SORT_FIELD = "name"


def _normalize_name(name: str) -> str:
    return name.strip()


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def get_by_id(db: Session, department_id: int) -> Department | None:
    return db.get(Department, department_id)


def get_by_name(db: Session, name: str) -> Department | None:
    """Fetch by name, case-insensitively.

    Uniqueness is enforced case-insensitively at the application level so that
    "Roads" and "roads" cannot both exist, which would be confusing in a
    picker. MySQL's default collation is already case-insensitive; this keeps
    the behaviour identical on SQLite.
    """
    statement = select(Department).where(
        func.lower(Department.name) == _normalize_name(name).lower()
    )
    return db.execute(statement).scalar_one_or_none()


def name_exists(db: Session, name: str, *, exclude_id: int | None = None) -> bool:
    """Whether another department already uses this name.

    ``exclude_id`` lets an update keep its own name without self-conflicting.
    """
    statement = (
        select(func.count())
        .select_from(Department)
        .where(func.lower(Department.name) == _normalize_name(name).lower())
    )
    if exclude_id is not None:
        statement = statement.where(Department.id != exclude_id)
    return bool(db.execute(statement).scalar_one())


def count_assigned_users(db: Session, department_id: int) -> int:
    """How many users still point at this department.

    Used to decide between deactivating and deleting.
    """
    statement = (
        select(func.count())
        .select_from(User)
        .where(User.department_id == department_id)
    )
    return int(db.execute(statement).scalar_one())


def _apply_filters(
    statement: Select, *, is_active: bool | None, search: str | None
) -> Select:
    if is_active is not None:
        statement = statement.where(Department.is_active.is_(is_active))
    if search:
        statement = statement.where(Department.name.ilike(f"%{search.strip()}%"))
    return statement


def count_departments(
    db: Session, *, is_active: bool | None = None, search: str | None = None
) -> int:
    statement = _apply_filters(
        select(func.count()).select_from(Department),
        is_active=is_active,
        search=search,
    )
    return int(db.execute(statement).scalar_one())


def list_departments(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 20,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    descending: bool = False,
) -> Sequence[Department]:
    """One page of departments, with ``id`` as a stable tie-breaker."""
    statement = _apply_filters(
        select(Department), is_active=is_active, search=search
    )

    column = SORTABLE_FIELDS.get(sort_by or DEFAULT_SORT_FIELD)
    if column is None:
        column = SORTABLE_FIELDS[DEFAULT_SORT_FIELD]

    order = column.desc() if descending else column.asc()  # type: ignore[union-attr]
    statement = (
        statement.order_by(order, Department.id.asc()).offset(offset).limit(limit)
    )

    return db.execute(statement).scalars().all()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def create(
    db: Session,
    *,
    name: str,
    description: str | None = None,
    default_sla_hours: int,
    is_active: bool = True,
) -> Department:
    """Add a department to the session and flush it."""
    department = Department(
        name=_normalize_name(name),
        description=description,
        default_sla_hours=default_sla_hours,
        is_active=is_active,
    )
    db.add(department)
    db.flush()
    return department
