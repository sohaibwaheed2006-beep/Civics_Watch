"""Authentication business logic.

Owns the rules and raises :class:`~app.core.exceptions.AppError` subclasses on
failure. Imports no FastAPI symbols and builds no HTTP responses, so each rule
is directly unit-testable.

Transactions: every function here takes the request's ``Session`` and commits
its own unit of work, so the boundary is visible at the call site. A failure
leaves the session for ``get_db`` to roll back.
"""

from __future__ import annotations

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.core.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    NotFoundError,
)
from app.core.logging import get_logger
from app.core.security import (
    access_token_expires_in_seconds,
    create_access_token,
    hash_password,
    needs_rehash,
    verify_password,
)
from app.models.user import User
from app.repositories import user_repository
from app.schemas.auth import ChangePasswordRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserProfileUpdate

logger = get_logger(__name__)

__all__ = [
    "register_citizen",
    "authenticate",
    "issue_access_token",
    "load_active_user",
    "update_own_profile",
    "change_password",
]

#: Returned for both an unknown email and a wrong password, so the endpoint
#: cannot be used to discover which addresses are registered.
_INVALID_CREDENTIALS = "Incorrect email or password."


def register_citizen(db: Session, payload: RegisterRequest) -> User:
    """Create a citizen account.

    The role is hard-coded here rather than read from the request: public
    registration can never mint an admin or a worker.

    Raises
    ------
    ConflictError
        The email is already registered (409).
    """
    if user_repository.email_exists(db, payload.email):
        raise ConflictError("An account with this email already exists.")

    try:
        user = user_repository.create(
            db,
            full_name=payload.full_name,
            email=payload.email,
            password_hash=hash_password(payload.password),
            role=UserRole.CITIZEN,
            phone=payload.phone,
            is_active=True,
            is_verified=False,
            department_id=None,
        )
        db.commit()
    except IntegrityError:
        # The pre-check above loses a race only if two registrations for the
        # same address commit concurrently; the unique index is the real
        # guarantee, so translate its violation rather than leaking a 500.
        db.rollback()
        raise ConflictError("An account with this email already exists.") from None

    logger.info("Registered citizen id=%s", user.id)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    """Verify credentials and return the matching active user.

    Raises
    ------
    AuthenticationError
        Unknown email, wrong password, or a deactivated account (401). The
        message is identical in all three cases.
    """
    user = user_repository.get_by_email(db, email)

    if user is None:
        logger.info("Login failed: no account for the supplied email")
        raise AuthenticationError(_INVALID_CREDENTIALS)

    if not verify_password(password, user.password_hash):
        logger.info("Login failed: wrong password for user id=%s", user.id)
        raise AuthenticationError(_INVALID_CREDENTIALS)

    if not user.is_active:
        # Same message as a bad password: a deactivated account should not be
        # distinguishable from one that never existed.
        logger.info("Login refused: user id=%s is inactive", user.id)
        raise AuthenticationError(_INVALID_CREDENTIALS)

    # Transparently upgrade a hash made with older cost parameters.
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
        db.commit()
        logger.info("Upgraded password hash parameters for user id=%s", user.id)

    logger.info("Login succeeded for user id=%s", user.id)
    return user


def issue_access_token(user: User) -> TokenResponse:
    """Mint an access token for an already-authenticated user."""
    return TokenResponse(
        access_token=create_access_token(user.id),
        token_type="bearer",
        expires_in=access_token_expires_in_seconds(),
    )


def load_active_user(db: Session, user_id: int) -> User:
    """Resolve a token subject to a live, active user.

    Called on every authenticated request: current stored state decides
    whether access is granted, so deactivating a user takes effect
    immediately even though their token is still cryptographically valid.

    Raises
    ------
    AuthenticationError
        The user no longer exists or has been deactivated (401).
    """
    user = user_repository.get_by_id(db, user_id)

    if user is None:
        logger.info("Token subject %s no longer exists", user_id)
        raise AuthenticationError("Could not validate credentials.")

    if not user.is_active:
        logger.info("Token subject %s is inactive", user_id)
        raise AuthenticationError("This account has been deactivated.")

    return user


def update_own_profile(
    db: Session, user_id: int, payload: UserProfileUpdate
) -> User:
    """Apply a self-service profile update.

    Only the fields the client actually sent are written
    (``exclude_unset=True``), which is what makes ``phone: null`` mean "clear
    it" while an omitted ``phone`` means "leave it alone".

    The writable set is constrained twice: the schema forbids unknown fields,
    and only ``full_name``/``phone`` are forwarded here. Role, status,
    verification and department cannot be reached through this path.
    """
    changes = payload.model_dump(exclude_unset=True)
    allowed = {
        name: value
        for name, value in changes.items()
        if name in {"full_name", "phone"}
    }

    if not allowed:
        raise BadRequestError("No updatable fields were provided.")

    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User not found.")

    for name, value in allowed.items():
        setattr(user, name, value)
    db.commit()

    logger.info("Updated profile for user id=%s fields=%s", user_id, sorted(allowed))
    return user


def change_password(
    db: Session, user_id: int, payload: ChangePasswordRequest
) -> None:
    """Replace a user's password after confirming the current one.

    Raises
    ------
    BadRequestError
        The supplied ``current_password`` is wrong (400).

    A 400 is used deliberately rather than a 401: the request *was*
    authenticated, and a 401 would prompt most clients to discard a perfectly
    valid session.
    """
    user = user_repository.get_by_id(db, user_id)
    if user is None:
        raise NotFoundError("User not found.")

    if not verify_password(payload.current_password, user.password_hash):
        logger.info(
            "Password change refused for user id=%s: wrong current password", user_id
        )
        raise BadRequestError("The current password is incorrect.")

    user.password_hash = hash_password(payload.new_password)
    db.commit()
    logger.info("Password changed for user id=%s", user_id)
