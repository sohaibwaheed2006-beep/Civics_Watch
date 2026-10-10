"""User administration business logic.

Owns the rules for listing users and changing roles, including the guard that
keeps at least one administrator able to log in.
"""

from __future__ import annotations

from typing import Sequence

from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.logging import get_logger
from app.models.user import User
from app.repositories import department_repository, user_repository
from app.schemas.user import UserRoleUpdate

logger = get_logger(__name__)

__all__ = ["list_users", "get_user", "update_user_role"]


def list_users(
    db: Session,
    *,
    offset: int,
    limit: int,
    role: UserRole | None = None,
    department_id: int | None = None,
    is_active: bool | None = None,
    search: str | None = None,
    sort_by: str | None = None,
    descending: bool = False,
) -> tuple[Sequence[User], int]:
    """One page of users plus the total matching count.

    Both queries apply identical filters, so the reported total always agrees
    with the page contents.
    """
    total = user_repository.count_users(
        db,
        role=role,
        department_id=department_id,
        is_active=is_active,
        search=search,
    )
    items = user_repository.list_users(
        db,
        offset=offset,
        limit=limit,
        role=role,
        department_id=department_id,
        is_active=is_active,
        search=search,
        sort_by=sort_by,
        descending=descending,
    )
    return items, total


def get_user(db: Session, user_id: int) -> User:
    """Fetch one user.

    Raises
    ------
    NotFoundError
        No user with that ID (404).
    """
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User not found.")
    return user


def update_user_role(
    db: Session, *, actor: User, user_id: int, payload: UserRoleUpdate
) -> User:
    """Change a user's role, and optionally their department.

    Rules enforced here:

    1. **No self-demotion.** An admin cannot change their own role. Removing
       your own access by accident is a support incident, and the check also
       stops the sole admin from locking everyone out.
    2. **The last active admin is protected.** Demoting the only remaining
       active administrator would leave the system with no one able to manage
       it, so it is refused.
    3. **A worker's department must exist and be active.** Assigning someone
       to a retired or non-existent department would silently break report
       routing.
    4. **Only workers keep a department.** Promoting to admin or demoting to
       citizen clears the assignment, so a stale link cannot linger.

    Raises
    ------
    NotFoundError
        The target user, or the requested department, does not exist (404).
    PermissionDeniedError
        The actor is trying to change their own role (403).
    ConflictError
        The change would remove the last active administrator, or the target
        department is inactive (409).
    """
    target = user_repository.get_by_id(db, user_id)
    if target is None:
        raise NotFoundError("User not found.")

    if target.id == actor.id:
        raise PermissionDeniedError(
            "You cannot change your own role. Ask another administrator."
        )

    new_role = payload.role
    role_changed = target.role != new_role

    # Guard 2: would this leave nobody able to administer the system?
    if role_changed and target.role == UserRole.ADMIN:
        remaining = user_repository.count_active_admins(
            db, exclude_user_id=target.id
        )
        if remaining == 0:
            raise ConflictError(
                "This is the last active administrator; promote another "
                "administrator before changing this role."
            )

    # Resolve the department assignment.
    department_id = target.department_id
    if "department_id" in payload.model_fields_set:
        department_id = payload.department_id

    if new_role == UserRole.WORKER:
        if department_id is not None:
            department = department_repository.get_by_id(db, department_id)
            if department is None:
                raise NotFoundError(f"Department {department_id} not found.")
            if not department.is_active:
                raise ConflictError(
                    "Cannot assign a worker to an inactive department."
                )
    else:
        # Guard 4: citizens and admins hold no department.
        department_id = None

    target.role = new_role
    target.department_id = department_id
    db.commit()

    logger.info(
        "Admin id=%s set user id=%s role=%s department_id=%s",
        actor.id,
        target.id,
        new_role.value,
        department_id,
    )
    return target
