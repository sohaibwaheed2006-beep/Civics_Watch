"""Application error types and the single source of truth for error responses.

Every failure leaving the API - whether raised deliberately by a service, by
FastAPI's request validation, or by an unexpected bug - is rendered with the
same JSON envelope::

    {
      "error": {
        "code": "not_found",
        "message": "Department not found",
        "details": [ {"field": "body.name", "message": "...", "type": "..."} ],
        "request_id": "3f0e...": str | null
      }
    }

Services raise the :class:`AppError` subclasses below and never build HTTP
responses themselves; routers stay thin and the wire format stays consistent.
"""

from __future__ import annotations

import http
from typing import Any, Iterable, Mapping

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import get_logger, get_request_id

logger = get_logger(__name__)

__all__ = [
    "AppError",
    "BadRequestError",
    "AuthenticationError",
    "PermissionDeniedError",
    "NotFoundError",
    "ConflictError",
    "UnprocessableEntityError",
    "InternalServerError",
    "ErrorCode",
    "build_error_payload",
    "register_exception_handlers",
]


class ErrorCode:
    """Stable, machine-readable error codes returned in ``error.code``.

    Clients should branch on these rather than on human-readable messages.
    """

    BAD_REQUEST = "bad_request"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    NOT_FOUND = "not_found"
    METHOD_NOT_ALLOWED = "method_not_allowed"
    CONFLICT = "conflict"
    VALIDATION_ERROR = "validation_error"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    UNSUPPORTED_MEDIA_TYPE = "unsupported_media_type"
    TOO_MANY_REQUESTS = "too_many_requests"
    INTERNAL_ERROR = "internal_error"
    SERVICE_UNAVAILABLE = "service_unavailable"


#: Maps bare HTTP status codes onto our stable error codes, so that exceptions
#: raised as plain ``HTTPException`` still produce a well-formed envelope.
_STATUS_TO_CODE: dict[int, str] = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT,
    413: ErrorCode.PAYLOAD_TOO_LARGE,
    415: ErrorCode.UNSUPPORTED_MEDIA_TYPE,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.TOO_MANY_REQUESTS,
    500: ErrorCode.INTERNAL_ERROR,
    503: ErrorCode.SERVICE_UNAVAILABLE,
}


def _code_for_status(status_code: int) -> str:
    if status_code in _STATUS_TO_CODE:
        return _STATUS_TO_CODE[status_code]
    try:
        return http.HTTPStatus(status_code).phrase.lower().replace(" ", "_")
    except ValueError:  # pragma: no cover - non-standard status code
        return ErrorCode.INTERNAL_ERROR


# ---------------------------------------------------------------------------
# Exception hierarchy
# ---------------------------------------------------------------------------
class AppError(Exception):
    """Base class for every expected, client-facing application failure.

    Parameters
    ----------
    message:
        Human-readable, safe to show to the caller. Must never contain
        secrets, password material or internal stack detail.
    details:
        Optional per-field breakdown, mirroring the validation error shape.
    code:
        Overrides the default error code for the status.
    headers:
        Extra response headers (e.g. ``WWW-Authenticate`` on a 401).
    """

    status_code: int = 500
    code: str = ErrorCode.INTERNAL_ERROR
    message: str = "An unexpected error occurred."

    def __init__(
        self,
        message: str | None = None,
        *,
        details: list[dict[str, Any]] | None = None,
        code: str | None = None,
        status_code: int | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or []
        self.code = code or self.code
        self.status_code = status_code or self.status_code
        self.headers = dict(headers) if headers else None
        super().__init__(self.message)

    def to_payload(self, request_id: str | None = None) -> dict[str, Any]:
        return build_error_payload(
            code=self.code,
            message=self.message,
            details=self.details,
            request_id=request_id,
        )


class BadRequestError(AppError):
    """400 - the request is malformed or semantically unusable."""

    status_code = 400
    code = ErrorCode.BAD_REQUEST
    message = "The request could not be processed."


class AuthenticationError(AppError):
    """401 - missing, malformed or expired credentials.

    Keep the message generic: never reveal whether an email exists.
    """

    status_code = 401
    code = ErrorCode.UNAUTHORIZED
    message = "Not authenticated."

    def __init__(self, message: str | None = None, **kwargs: Any) -> None:
        kwargs.setdefault("headers", {"WWW-Authenticate": "Bearer"})
        super().__init__(message, **kwargs)


class PermissionDeniedError(AppError):
    """403 - authenticated, but not allowed to perform this operation."""

    status_code = 403
    code = ErrorCode.FORBIDDEN
    message = "You do not have permission to perform this action."


class NotFoundError(AppError):
    """404 - the addressed resource does not exist."""

    status_code = 404
    code = ErrorCode.NOT_FOUND
    message = "Resource not found."


class ConflictError(AppError):
    """409 - uniqueness violation or an illegal state transition."""

    status_code = 409
    code = ErrorCode.CONFLICT
    message = "The request conflicts with the current state of the resource."


class UnprocessableEntityError(AppError):
    """422 - well-formed request that fails a business rule."""

    status_code = 422
    code = ErrorCode.VALIDATION_ERROR
    message = "The request could not be validated."


class InternalServerError(AppError):
    """500 - unexpected server-side failure."""

    status_code = 500
    code = ErrorCode.INTERNAL_ERROR
    message = "An internal server error occurred."


# ---------------------------------------------------------------------------
# Payload construction
# ---------------------------------------------------------------------------
def build_error_payload(
    *,
    code: str,
    message: str,
    details: Iterable[Mapping[str, Any]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build the canonical error envelope."""
    return {
        "error": {
            "code": code,
            "message": message,
            "details": [dict(item) for item in (details or [])],
            "request_id": request_id,
        }
    }


def _json_error(
    *,
    status_code: int,
    code: str,
    message: str,
    details: Iterable[Mapping[str, Any]] | None = None,
    request_id: str | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=build_error_payload(
            code=code, message=message, details=details, request_id=request_id
        ),
        headers=dict(headers) if headers else None,
    )


def _normalize_validation_errors(
    errors: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Flatten pydantic/FastAPI validation errors into ``error.details``.

    ``loc`` tuples are joined with dots (``body.address.street``) so clients
    can map a failure straight onto a form field. The raw offending ``input``
    is dropped: it can contain the submitted password.
    """
    normalized: list[dict[str, Any]] = []
    for err in errors:
        location = err.get("loc") or ()
        field = ".".join(str(part) for part in location) or "__request__"
        normalized.append(
            {
                "field": field,
                "message": str(err.get("msg", "Invalid value.")),
                "type": str(err.get("type", "value_error")),
            }
        )
    return normalized


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------
async def app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render a deliberately raised :class:`AppError`."""
    assert isinstance(exc, AppError)  # narrowed by the registration below
    request_id = get_request_id()

    log = logger.warning if exc.status_code < 500 else logger.error
    log(
        "Handled %s on %s %s -> %s (%s)",
        type(exc).__name__,
        request.method,
        request.url.path,
        exc.status_code,
        exc.code,
    )
    return _json_error(
        status_code=exc.status_code,
        code=exc.code,
        message=exc.message,
        details=exc.details,
        request_id=request_id,
        headers=exc.headers,
    )


async def http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Render FastAPI/Starlette ``HTTPException``s in our envelope.

    This also covers framework-generated 404s for unmatched paths and 405s for
    wrong methods, so *every* response body is shaped consistently.
    """
    assert isinstance(exc, StarletteHTTPException)
    detail = exc.detail
    message = detail if isinstance(detail, str) else _code_for_status(exc.status_code)
    details: list[dict[str, Any]] = []
    if not isinstance(detail, str) and detail is not None:
        details = [{"field": "__request__", "message": str(detail), "type": "http_error"}]

    return _json_error(
        status_code=exc.status_code,
        code=_code_for_status(exc.status_code),
        message=message,
        details=details,
        request_id=get_request_id(),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Render request-validation failures as 422 with per-field details."""
    assert isinstance(exc, RequestValidationError)
    return _json_error(
        status_code=422,
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed.",
        details=_normalize_validation_errors(exc.errors()),
        request_id=get_request_id(),
    )


async def pydantic_validation_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Catch model-level ``ValidationError``s raised outside request parsing.

    A pydantic error escaping a service is a server-side bug (bad internal
    data), so it is reported as 500 without echoing the offending values.
    """
    assert isinstance(exc, PydanticValidationError)
    logger.error(
        "Unhandled pydantic ValidationError on %s %s: %d error(s)",
        request.method,
        request.url.path,
        exc.error_count(),
        exc_info=True,
    )
    return _json_error(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message=InternalServerError.message,
        request_id=get_request_id(),
    )


async def unhandled_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """Last-resort handler: log the traceback, return an opaque 500.

    Stack traces and exception text are written to the server log only - the
    client receives nothing that could leak internals.
    """
    logger.exception(
        "Unhandled %s on %s %s",
        type(exc).__name__,
        request.method,
        request.url.path,
    )
    return _json_error(
        status_code=500,
        code=ErrorCode.INTERNAL_ERROR,
        message=InternalServerError.message,
        request_id=get_request_id(),
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Attach every error handler to ``app``.

    Called once from the application factory. Order is irrelevant: Starlette
    dispatches on the most specific registered exception class.
    """
    app.add_exception_handler(AppError, app_error_handler)
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(PydanticValidationError, pydantic_validation_handler)
    app.add_exception_handler(Exception, unhandled_exception_handler)
