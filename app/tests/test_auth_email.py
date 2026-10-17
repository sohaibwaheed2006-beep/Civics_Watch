"""Password-reset email flow.

Covers the two routes that back SMTP password recovery:
``POST /auth/forgot-password`` and ``POST /auth/reset-password``.

Email delivery itself is not exercised here - SMTP is unconfigured in the test
environment, so the background send is a no-op. These tests pin the *token*
behaviour, which is where the security-relevant logic lives: reset requests
must not leak which emails exist, a link must be single-use, and a link must
never be swappable for a token of another type.
"""

from __future__ import annotations

from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.security import (
    create_access_token,
    create_password_reset_token,
)
from app.models.user import User


def _user(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    assert user is not None
    return user


# ---------------------------------------------------------------------------
# POST /forgot-password
# ---------------------------------------------------------------------------
def test_forgot_password_returns_200_for_a_known_email(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": citizen_payload["email"]},
    )

    assert response.status_code == 200, response.text
    assert "message" in response.json()


def test_forgot_password_response_is_the_same_for_an_unknown_email(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    """The endpoint must not reveal whether an address has an account."""
    known = client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": citizen_payload["email"]},
    )
    unknown = client.post(
        f"{api_prefix}/auth/forgot-password",
        json={"email": "nobody@example.com"},
    )

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()


def test_forgot_password_rejects_an_invalid_email(
    client: TestClient, api_prefix: str
) -> None:
    response = client.post(
        f"{api_prefix}/auth/forgot-password", json={"email": "not-an-email"}
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /reset-password
# ---------------------------------------------------------------------------
def test_reset_password_sets_a_new_working_password(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    user = _user(db, int(registered_citizen["id"]))
    token = create_password_reset_token(user.id, user.password_hash)

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": token, "new_password": "a-brand-new-password"},
    )
    assert response.status_code == 200, response.text

    with_new = client.post(
        f"{api_prefix}/auth/login",
        json={"email": citizen_payload["email"], "password": "a-brand-new-password"},
    )
    with_old = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": citizen_payload["password"],
        },
    )

    assert with_new.status_code == 200, with_new.text
    assert with_old.status_code == 401


def test_a_reset_link_is_single_use(
    client: TestClient,
    api_prefix: str,
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    """Once used, the same link must not reset the password again.

    The token is tied to the password hash it was minted against; completing a
    reset changes the hash, so the link no longer matches.
    """
    user = _user(db, int(registered_citizen["id"]))
    token = create_password_reset_token(user.id, user.password_hash)

    first = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": token, "new_password": "a-brand-new-password"},
    )
    assert first.status_code == 200, first.text

    second = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": token, "new_password": "yet-another-password"},
    )
    assert second.status_code == 400
    assert second.json()["error"]["code"] == "bad_request"


def test_reset_password_rejects_an_expired_token(
    client: TestClient,
    api_prefix: str,
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    user = _user(db, int(registered_citizen["id"]))
    expired = create_password_reset_token(
        user.id, user.password_hash, expires_delta=timedelta(minutes=-5)
    )

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": expired, "new_password": "a-brand-new-password"},
    )

    assert response.status_code == 400


def test_reset_password_rejects_a_token_of_the_wrong_type(
    client: TestClient,
    api_prefix: str,
    registered_citizen: dict[str, object],
) -> None:
    """An access token must not be usable as a reset token."""
    access = create_access_token(int(registered_citizen["id"]))

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": access, "new_password": "a-brand-new-password"},
    )

    assert response.status_code == 400


def test_reset_password_rejects_a_too_short_new_password(
    client: TestClient,
    api_prefix: str,
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    user = _user(db, int(registered_citizen["id"]))
    token = create_password_reset_token(user.id, user.password_hash)

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": token, "new_password": "short"},
    )

    assert response.status_code == 422


def test_reset_password_fails_for_an_inactive_user(
    client: TestClient,
    api_prefix: str,
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    user = _user(db, int(registered_citizen["id"]))
    token = create_password_reset_token(user.id, user.password_hash)

    db.query(User).filter(User.id == user.id).update({"is_active": False})
    db.commit()

    response = client.post(
        f"{api_prefix}/auth/reset-password",
        json={"token": token, "new_password": "a-brand-new-password"},
    )

    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Registration no longer sends a verification email / requires confirmation
# ---------------------------------------------------------------------------
def test_a_freshly_registered_user_can_log_in_immediately(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    """No email confirmation gate: register, then sign in right away."""
    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": citizen_payload["password"],
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


# ---------------------------------------------------------------------------
# OpenAPI
# ---------------------------------------------------------------------------
def test_password_reset_routes_are_documented(
    client: TestClient, api_prefix: str
) -> None:
    paths = client.get("/openapi.json").json()["paths"]

    assert f"{api_prefix}/auth/forgot-password" in paths
    assert f"{api_prefix}/auth/reset-password" in paths
    # The email-verification routes were removed.
    assert f"{api_prefix}/auth/verify-email" not in paths
    assert f"{api_prefix}/auth/resend-verification" not in paths
