"""Logging configuration and per-request correlation IDs.

Every log line carries the ID of the request that produced it, which makes a
single user-visible failure traceable across services. The same ID is returned
to the client in the ``X-Request-ID`` header and in ``error.request_id``.

A redaction filter strips anything that looks like a password, bearer token or
secret from formatted log messages. It is a safety net, not a licence to log
credentials: never pass secrets to a logger in the first place.
"""

from __future__ import annotations

import logging
import logging.config
import re
import uuid
from contextvars import ContextVar
from typing import Any, Final

#: Correlation ID for the request currently being handled. A ContextVar keeps
#: the value isolated per task, so concurrent requests never mix IDs.
_request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

REQUEST_ID_HEADER: Final[str] = "X-Request-ID"

_CONFIGURED = False


# ---------------------------------------------------------------------------
# Request-ID helpers
# ---------------------------------------------------------------------------
def new_request_id() -> str:
    """Generate a fresh correlation ID."""
    return uuid.uuid4().hex


def set_request_id(request_id: str | None) -> object:
    """Bind ``request_id`` to the current context; returns a reset token."""
    return _request_id_ctx.set(request_id)


def reset_request_id(token: Any) -> None:
    """Restore the previous correlation ID using a token from :func:`set_request_id`."""
    try:
        _request_id_ctx.reset(token)
    except (ValueError, LookupError):  # pragma: no cover - defensive
        _request_id_ctx.set(None)


def get_request_id() -> str | None:
    """Return the current request's correlation ID, if any."""
    return _request_id_ctx.get()


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------
class RequestIdFilter(logging.Filter):
    """Expose the correlation ID to format strings as ``%(request_id)s``."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or "-"
        return True


class RedactSecretsFilter(logging.Filter):
    """Mask credential-looking substrings in the final log message.

    A safety net for accidental exposure, not a licence to log credentials.
    Substitutions are applied in a fixed order, because an earlier rule can
    otherwise consume the token an later rule needs to see:

    1. ``Bearer <token>`` - must run before the key/value rule, which would
       otherwise match ``Authorization: Bearer`` and redact only the literal
       word "Bearer", leaving the token in the clear.
    2. ``scheme://user:password@host`` - connection strings.
    3. ``key=value`` / ``"key": "value"`` for a known set of sensitive keys.
    """

    _REDACTED = "***REDACTED***"

    #: Sensitive key names, longest-first so that ``secret_key`` is preferred
    #: over ``secret`` and ``access_token`` over ``token``.
    _SENSITIVE_KEYS = (
        "client_secret",
        "refresh_token",
        "access_token",
        "authorization",
        "secret_key",
        "password",
        "passwd",
        "api_key",
        "apikey",
        "secret",
        "token",
        "pwd",
    )

    _SUBSTITUTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
        # 1. Bearer / Basic credentials in an Authorization header value.
        (
            re.compile(r"(?i)\b(bearer|basic)\s+([A-Za-z0-9._\-+/=]+)"),
            rf"\1 {_REDACTED}",
        ),
        # 2. Credentials embedded in a connection URL. Group 1 already holds
        #    "scheme://user", so the replacement only rewrites the password.
        (
            re.compile(r"(?i)\b([a-z0-9+.\-]+://[^:/\s@]+):([^@/\s]+)@"),
            rf"\1:{_REDACTED}@",
        ),
        # 3. key=value and "key": "value". Group 2 absorbs an optional closing
        #    quote on the key plus the separator, so JSON-ish text survives.
        (
            re.compile(
                r"(?i)\b(" + "|".join(_SENSITIVE_KEYS) + r")\b"
                r"([\"']?\s*[:=]\s*)"
                r"(\"[^\"]*\"|'[^']*'|[^\s,;)}\]]+)"
            ),
            rf"\1\2{_REDACTED}",
        ),
    )

    def filter(self, record: logging.LogRecord) -> bool:
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - broken % args
            return True

        redacted = message
        for pattern, replacement in self._SUBSTITUTIONS:
            redacted = pattern.sub(replacement, redacted)

        if redacted != message:
            # Replace msg/args wholesale so downstream formatting cannot
            # resurrect the original value.
            record.msg = redacted
            record.args = ()
        return True


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_CONSOLE_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | [%(request_id)s] | %(message)s"


def build_logging_config(level: str) -> dict[str, Any]:
    """Return a ``logging.config.dictConfig`` dictionary for the given level."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_id": {"()": RequestIdFilter},
            "redact_secrets": {"()": RedactSecretsFilter},
        },
        "formatters": {
            "console": {
                "format": _CONSOLE_FORMAT,
                "datefmt": "%Y-%m-%dT%H:%M:%S%z",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": "ext://sys.stdout",
                "formatter": "console",
                "filters": ["request_id", "redact_secrets"],
            }
        },
        "root": {"handlers": ["console"], "level": level},
        "loggers": {
            "app": {"handlers": ["console"], "level": level, "propagate": False},
            "uvicorn": {"handlers": ["console"], "level": level, "propagate": False},
            "uvicorn.error": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
            "uvicorn.access": {
                "handlers": ["console"],
                "level": level,
                "propagate": False,
            },
        },
    }


def configure_logging(*, debug: bool = False, force: bool = False) -> None:
    """Install the application logging configuration.

    Idempotent: repeated calls are ignored unless ``force`` is set, so
    importing the app factory more than once (as the tests do) will not stack
    duplicate handlers.
    """
    global _CONFIGURED
    if _CONFIGURED and not force:
        return

    level = "DEBUG" if debug else "INFO"
    logging.config.dictConfig(build_logging_config(level))
    _CONFIGURED = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a module logger under the ``app`` namespace."""
    if not name or name == "app":
        return logging.getLogger("app")
    if name.startswith("app."):
        return logging.getLogger(name)
    return logging.getLogger(f"app.{name}")
