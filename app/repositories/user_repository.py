"""User persistence.

Query construction only. These functions never commit - the calling service
owns the transaction boundary, so a multi-step operation can succeed or fail
as one unit.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.user import User

__all__ = [
    "normalize_email",
    "get_by_id",
    "get_by_email",
    "email_exists",
    "create",
    "list_users",
    "count_users",
    "count_active_admins",
    "SORTABLE_FIELDS",
]

#: Columns a client may sort the user list by. An allow-list, so ``sort_by``
#: can never be interpolated into SQL or used to probe unmapped attributes.
SORTABLE_FIELDS: dict[str, object] = {
    "id": User.id,
    "full_name": User.full_name,
    "email": User.email,
    "role": User.role,
    "created_at": User.created_at,
    "updated_at": User.updated_at,
}

DEFAULT_SORT_FIELD = "id"


def normalize_email(email: str) -> str:
    """Canonical form used for both storage and lookup.

    Lower-cased and trimmed, so ``" Ada@Example.COM "`` and
    ``"ada@example.com"`` resolve to the same account and cannot both be
    registered.
    """
    return email.strip().lower()


# ---------------------------------------------------------------------------
# Reads
# ---------------------------------------------------------------------------
def get_by_id(db: Session, user_id: int) -> User | None:
    """Fetch one user by primary key."""
    return db.get(User, user_id)


def get_by_email(db: Session, email: str) -> User | None:
    """Fetch one user by email, matching on the normalized form."""
    statement = select(User).where(User.email == normalize_email(email))
    return db.execute(statement).scalar_one_or_none()


def email_exists(db: Session, email: str) -> bool:
    """Whether an account already uses this email."""
    statement = select(func.count()).select_from(User).where(
        User.email == normalize_email(email)
    )
    return bool(db.execute(statement).scalar_one())


def count_active_admins(db: Session, *, exclude_user_id: int | None = None) -> int:
    """Number of active administrators, optionally ignoring one user.

    Backs the last-active-admin guard: ``exclude_user_id`` answers "would any
    admin remain if this one were demoted or deactivated?".
    """
    statement = (
        select(func.count())
        .select_from(User)
        .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
    )
    if exclude_user_id is not None:
        statement = statement.where(User.id != exclude_user_id)
    return int(db.execute(statement).scalar_one())


def _apply_user_filters(
    statement: Select,
    *,
    role: UserRole | None,
    department_id: int | None,
    is_active: bool | None,
    search: str | None,
) -> Select:
    """Attach the optional filters shared by the list and count queries.

    Keeping them in one place is what guarantees the page count matches the
    page contents.
    """
    if role is not None:
        statement = statement.where(User.role == role)
    if department_id is not None:
        statement = statement.where(User.department_id == department_id)
    if is_active is not None:
        statement = statement.where(User.is_active.is_(is_active))
    if search:
        pattern = f"%{search.strip()}%"
        statement = statement.where(
            User.full_name.ilike(pattern) | User.email.ilike(pattern)
        )
    return statement


def count_users(
    db: Session,
    *,
    role: UserRole | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
) -> int:
    """Total users matching the filters, ignoring pagination."""
    statement = _apply_user_filters(
        select(func.count()).select_from(User),
        role=role,
        department_id=department_id,
        is_active=is_active,
        search=search,
    )
    return int(db.execute(statement).scalar_one())


def list_users(
    db: Session,
    *,
    offset: int = 0,
    limit: int = 20,
    role: UserRole | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    descending: bool = False,
) -> Sequence[User]:
    """One page of users.

    Ordering always ends with ``User.id`` as a tie-breaker. Without it, rows
    sharing a sort value (two users with the same role, say) could appear on
    two different pages or on none at all.
    """
    statement = _apply_user_filters(
        select(User),
        role=role,
        department_id=department_id,
        is_active=is_active,
        search=search,
    )

    column = SORTABLE_FIELDS.get(sort_by or DEFAULT_SORT_FIELD)
    if column is None:
        column = SORTABLE_FIELDS[DEFAULT_SORT_FIELD]

    order = column.desc() if descending else column.asc()  # type: ignore[union-attr]
    statement = statement.order_by(order, User.id.asc()).offset(offset).limit(limit)

    return db.execute(statement).unique().scalars().all()


# ---------------------------------------------------------------------------
# Writes
# ---------------------------------------------------------------------------
def create(
    db: Session,
    *,
    full_name: str,
    email: str,
    password_hash: str,
    role: UserRole = UserRole.CITIZEN,
    phone: str | None = None,
    is_active: bool = True,
    is_verified: bool = False,
    department_id: int | None = None,
) -> User:
    """Add a user to the session and flush it.

    Flushed, not committed: the INSERT is sent so the generated ``id`` is
    available and a unique-constraint violation surfaces here, but the
    transaction stays open for the service to commit.
    """
    user = User(
        full_name=full_name.strip(),
        email=normalize_email(email),
        password_hash=password_hash,
        role=role,
        phone=phone,
        is_active=is_active,
        is_verified=is_verified,
        department_id=department_id,
    )
    db.add(user)
    db.flush()
    return user
