"""The shared error envelope.

These tests pin the wire format that both developers' modules rely on, so a
change to error rendering cannot silently break clients.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.exceptions import (
    AppError,
    AuthenticationError,
    ConflictError,
    ErrorCode,
    NotFoundError,
    PermissionDeniedError,
    build_error_payload,
)

pytestmark = pytest.mark.contract


def _assert_envelope(body: dict, expected_code: str) -> None:
    assert set(body) == {"error"}, "the payload must contain exactly one 'error' key"
    error = body["error"]
    assert set(error) == {"code", "message", "details", "request_id"}
    assert error["code"] == expected_code
    assert isinstance(error["message"], str) and error["message"]
    assert isinstance(error["details"], list)


# ---------------------------------------------------------------------------
# Framework-generated errors
# ---------------------------------------------------------------------------
def test_unknown_path_returns_the_shared_envelope(client: TestClient) -> None:
    response = client.get("/this-route-does-not-exist")

    assert response.status_code == 404
    _assert_envelope(response.json(), ErrorCode.NOT_FOUND)


def test_wrong_method_returns_405_in_the_envelope(client: TestClient) -> None:
    response = client.delete("/health")

    assert response.status_code == 405
    _assert_envelope(response.json(), ErrorCode.METHOD_NOT_ALLOWED)


def test_error_response_includes_the_correlation_id(client: TestClient) -> None:
    response = client.get("/nope", headers={"X-Request-ID": "corr-1234"})

    assert response.json()["error"]["request_id"] == "corr-1234"


# ---------------------------------------------------------------------------
# Deliberately raised AppErrors
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("exception", "expected_status", "expected_code"),
    [
        (NotFoundError("Department not found."), 404, ErrorCode.NOT_FOUND),
        (AuthenticationError(), 401, ErrorCode.UNAUTHORIZED),
        (PermissionDeniedError(), 403, ErrorCode.FORBIDDEN),
        (ConflictError("Email already registered."), 409, ErrorCode.CONFLICT),
    ],
)
def test_app_errors_render_with_the_right_status_and_code(
    settings: Settings,
    exception: AppError,
    expected_status: int,
    expected_code: str,
) -> None:
    from app.main import create_app

    test_app: FastAPI = create_app(settings)

    @test_app.get("/_boom")
    async def boom() -> None:
        raise exception

    with TestClient(test_app) as local_client:
        response = local_client.get("/_boom")

    assert response.status_code == expected_status
    _assert_envelope(response.json(), expected_code)


def test_authentication_error_sets_the_www_authenticate_header(
    settings: Settings,
) -> None:
    from app.main import create_app

    test_app = create_app(settings)

    @test_app.get("/_unauth")
    async def unauth() -> None:
        raise AuthenticationError()

    with TestClient(test_app) as local_client:
        response = local_client.get("/_unauth")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


def test_app_error_details_are_passed_through(settings: Settings) -> None:
    from app.main import create_app

    test_app = create_app(settings)

    @test_app.get("/_detailed")
    async def detailed() -> None:
        raise ConflictError(
            "Department name already in use.",
            details=[
                {
                    "field": "body.name",
                    "message": "already exists",
                    "type": "unique_violation",
                }
            ],
        )

    with TestClient(test_app) as local_client:
        body = local_client.get("/_detailed").json()

    assert body["error"]["details"][0]["field"] == "body.name"


# ---------------------------------------------------------------------------
# Unhandled exceptions must not leak internals
# ---------------------------------------------------------------------------
def test_unhandled_exception_returns_an_opaque_500(settings: Settings) -> None:
    from app.main import create_app

    test_app = create_app(settings)

    @test_app.get("/_crash")
    async def crash() -> None:
        raise RuntimeError("connection string mysql://root:hunter2@db/secret failed")

    with TestClient(test_app, raise_server_exceptions=False) as local_client:
        response = local_client.get("/_crash")

    assert response.status_code == 500
    _assert_envelope(response.json(), ErrorCode.INTERNAL_ERROR)

    raw = response.text
    assert "hunter2" not in raw, "the client must not receive exception text"
    assert "Traceback" not in raw
    assert "RuntimeError" not in raw


# ---------------------------------------------------------------------------
# Payload helper
# ---------------------------------------------------------------------------
def test_build_error_payload_shape() -> None:
    payload = build_error_payload(
        code=ErrorCode.VALIDATION_ERROR,
        message="Request validation failed.",
        details=[{"field": "body.email", "message": "invalid", "type": "value_error"}],
        request_id="abc",
    )

    assert payload == {
        "error": {
            "code": "validation_error",
            "message": "Request validation failed.",
            "details": [
                {"field": "body.email", "message": "invalid", "type": "value_error"}
            ],
            "request_id": "abc",
        }
    }


def test_app_error_defaults_are_sane() -> None:
    assert NotFoundError().status_code == 404
    assert ConflictError().status_code == 409
    assert PermissionDeniedError().status_code == 403
    assert AuthenticationError().status_code == 401
    # Base class keeps a safe, non-descriptive default message.
    assert "unexpected" in AppError().message.lower()
