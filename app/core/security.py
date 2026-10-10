"""Security primitives: JWT access tokens and credential comparison.

Phase 2 scope
-------------
Access tokens only. No refresh tokens, no revocation list, no email
verification - those are deliberately out of scope.

Passwords are hashed with Argon2id, the current password-hashing
recommendation. The earlier phase stored plain text as a temporary shortcut;
now that credentials are written to a persistent database, that shortcut is
gone - plaintext at rest is the one mistake that cannot be undone after the
fact.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Final

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationError
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "ALGORITHM",
    "TOKEN_TYPE_ACCESS",
    "create_access_token",
    "decode_access_token",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "access_token_expires_in_seconds",
]

#: Signing algorithm. Symmetric HS256 is appropriate while a single service
#: both issues and validates the tokens.
ALGORITHM: Final[str] = "HS256"

#: Value of the ``type`` claim. Validated on decode so that a token minted for
#: another purpose can never be replayed as an access token.
TOKEN_TYPE_ACCESS: Final[str] = "access"


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------
#: Argon2id hasher using argon2-cffi's maintained defaults. The resulting hash
#: string embeds the algorithm, version and parameters, so tuning the cost
#: later does not invalidate existing hashes.
_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password for storage.

    Returns an Argon2id hash (``$argon2id$v=19$...``), including a
    per-password random salt. Hashing the same password twice therefore
    produces different strings, which is why stored hashes must only ever be
    compared through :func:`verify_password`.
    """
    return _password_hasher.hash(password)


def verify_password(plain_password: str, password_hash: str) -> bool:
    """Check a submitted password against a stored Argon2 hash.

    Returns ``False`` rather than raising on a mismatch or an unreadable hash,
    so a corrupt row cannot turn a failed login into a 500. Argon2's own
    verification is constant-time with respect to the hash.
    """
    try:
        return _password_hasher.verify(password_hash, plain_password)
    except VerifyMismatchError:
        return False
    except (InvalidHashError, VerificationError):
        # The stored value is not a usable Argon2 hash - for example a row left
        # over from the earlier plaintext phase. Refuse the login and flag it;
        # that user needs a password reset.
        logger.warning("Stored password hash is unreadable or not Argon2")
        return False


def needs_rehash(password_hash: str) -> bool:
    """Whether a stored hash was made with outdated parameters.

    Lets a successful login transparently upgrade an old hash to the current
    cost settings.
    """
    try:
        return _password_hasher.check_needs_rehash(password_hash)
    except (InvalidHashError, VerificationError):
        return False


# ---------------------------------------------------------------------------
# Access tokens
# ---------------------------------------------------------------------------
def access_token_expires_in_seconds(settings: Settings | None = None) -> int:
    """Access-token lifetime in seconds, for the ``expires_in`` response field."""
    settings = settings or get_settings()
    return settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def create_access_token(
    user_id: int,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed access token for ``user_id``.

    Claims
    ------
    ``sub``
        The user ID, as a string (the JWT spec requires a string subject).
    ``exp``
        Expiry, derived from ``ACCESS_TOKEN_EXPIRE_MINUTES``.
    ``iat``
        Issued-at, so a token's age is auditable.
    ``type``
        ``"access"`` - checked on decode.
    """
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + lifetime,
        "type": TOKEN_TYPE_ACCESS,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_access_token(token: str, *, settings: Settings | None = None) -> int:
    """Validate ``token`` and return the user ID it refers to.

    Rejects, with a generic 401 in every case:

    - a bad or missing signature
    - an expired token
    - a token whose ``type`` is not ``access``
    - a malformed or non-integer ``sub``

    The authoritative user record is always re-read from storage by the
    caller; a role claim is never trusted on its own.
    """
    settings = settings or get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.ExpiredSignatureError:
        logger.info("Rejected an expired access token")
        raise AuthenticationError("Token has expired.") from None
    except jwt.InvalidTokenError:
        # Covers bad signature, malformed structure, missing claims.
        # The token itself is never logged.
        logger.info("Rejected an invalid access token")
        raise AuthenticationError("Could not validate credentials.") from None

    if payload.get("type") != TOKEN_TYPE_ACCESS:
        logger.info("Rejected a token of type %r", payload.get("type"))
        raise AuthenticationError("Could not validate credentials.")

    subject = payload.get("sub")
    try:
        return int(subject)
    except (TypeError, ValueError):
        logger.info("Rejected a token with a non-numeric subject")
        raise AuthenticationError("Could not validate credentials.") from None
