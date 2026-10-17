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

import hashlib
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
    "TOKEN_TYPE_PASSWORD_RESET",
    "create_access_token",
    "decode_access_token",
    "create_password_reset_token",
    "decode_password_reset_token",
    "password_hash_fingerprint",
    "hash_password",
    "verify_password",
    "needs_rehash",
    "access_token_expires_in_seconds",
]

#: Signing algorithm. Symmetric HS256 is appropriate while a single service
#: both issues and validates the tokens.
ALGORITHM: Final[str] = "HS256"

#: Values of the ``type`` claim. Validated on decode so that a token minted for
#: one purpose can never be replayed for another (an access token used as a
#: reset token, say).
TOKEN_TYPE_ACCESS: Final[str] = "access"
TOKEN_TYPE_PASSWORD_RESET: Final[str] = "password_reset"


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


# ---------------------------------------------------------------------------
# Single-purpose links (password reset, email verification)
# ---------------------------------------------------------------------------
# These tokens travel in a URL and are consumed by anonymous endpoints, so they
# differ from access tokens in two ways:
#   * ``decode_*`` returns ``None`` on any problem instead of raising. The
#     calling service decides the HTTP status (a dead reset link is a 400, not
#     the 401 an access-token failure warrants).
#   * The ``type`` claim is checked strictly, so the three token families can
#     never be swapped for one another.
def password_hash_fingerprint(password_hash: str) -> str:
    """A short, non-reversible marker tying a reset token to one password.

    Embedding it lets a reset token self-invalidate the moment the password
    changes: once the hash differs, the stored fingerprint no longer matches,
    so a used (or stale) link cannot reset the password a second time. It is a
    digest of an already-irreversible Argon2 hash, so it exposes nothing.
    """
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def create_password_reset_token(
    user_id: int,
    password_hash: str,
    *,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Mint a signed, single-use password-reset token for ``user_id``.

    The token carries a fingerprint of the current password hash so that it is
    invalidated automatically once the password is changed.
    """
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    lifetime = expires_delta or timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + lifetime,
        "type": TOKEN_TYPE_PASSWORD_RESET,
        "pwf": password_hash_fingerprint(password_hash),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)


def decode_password_reset_token(
    token: str, *, settings: Settings | None = None
) -> tuple[int, str] | None:
    """Validate a reset token and return ``(user_id, password_fingerprint)``.

    Returns ``None`` for any failure - bad signature, expiry, wrong ``type`` or
    a malformed subject - so the caller can answer with a single, enumeration-
    safe "this link is invalid or has expired" message. The caller must still
    compare the returned fingerprint against the user's *current* password hash
    to reject a link that has already been used.
    """
    payload = _decode_link_token(token, TOKEN_TYPE_PASSWORD_RESET, settings=settings)
    if payload is None:
        return None
    fingerprint = payload.get("pwf")
    subject = payload.get("sub")
    if not isinstance(fingerprint, str):
        return None
    try:
        return int(subject), fingerprint
    except (TypeError, ValueError):
        return None


def _decode_link_token(
    token: str, expected_type: str, *, settings: Settings | None = None
) -> dict[str, Any] | None:
    """Decode and type-check a single-purpose link token.

    Backs the password-reset decoder. Returns the claims on success, ``None``
    on any JWT error or a ``type`` mismatch.
    """
    settings = settings or get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
    except jwt.InvalidTokenError:
        logger.info("Rejected an invalid %s token", expected_type)
        return None
    if payload.get("type") != expected_type:
        logger.info(
            "Rejected a %r token where %r was expected",
            payload.get("type"),
            expected_type,
        )
        return None
    return payload
