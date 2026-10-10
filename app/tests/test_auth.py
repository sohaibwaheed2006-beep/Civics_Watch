"""Authentication endpoint behaviour.

Covers the six Phase 2 routes end-to-end through ``TestClient``, plus the
authorisation invariants that must hold regardless of implementation:
registration cannot choose a role, responses never carry password material,
and token validation follows current stored state.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi.testclient import TestClient

from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import ALGORITHM, create_access_token, verify_password
from app.models.user import User


def _forge_token(payload: dict[str, object], key: str) -> str:
    """Build a token with arbitrary claims, for negative tests."""
    now = datetime.now(timezone.utc)
    claims: dict[str, object] = {
        "iat": now,
        "exp": now + timedelta(minutes=30),
        "type": "access",
    }
    claims.update(payload)
    return jwt.encode(claims, key, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------
def test_registration_succeeds_and_returns_the_user(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str]
) -> None:
    response = client.post(f"{api_prefix}/auth/register", json=citizen_payload)

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["id"] >= 1
    assert body["full_name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert body["phone"] == "+1 555 0142"
    assert body["created_at"]
    assert body["updated_at"]


def test_registration_always_assigns_the_citizen_role(
    registered_citizen: dict[str, object],
) -> None:
    assert registered_citizen["role"] == "citizen"
    assert registered_citizen["is_active"] is True
    assert registered_citizen["is_verified"] is False
    assert registered_citizen["department_id"] is None


def test_registration_response_never_contains_password_material(
    registered_citizen: dict[str, object],
) -> None:
    for leaked in ("password", "password_hash", "hashed_password"):
        assert leaked not in registered_citizen


def test_duplicate_email_is_rejected_with_409(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str]
) -> None:
    first = client.post(f"{api_prefix}/auth/register", json=citizen_payload)
    assert first.status_code == 201

    second = client.post(f"{api_prefix}/auth/register", json=citizen_payload)

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "conflict"


@pytest.mark.parametrize(
    "variant", ["ADA@EXAMPLE.COM", "Ada@Example.Com", "  ada@example.com  "]
)
def test_duplicate_detection_is_case_and_whitespace_insensitive(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    variant: str,
) -> None:
    client.post(f"{api_prefix}/auth/register", json=citizen_payload)

    duplicate = dict(citizen_payload, email=variant)
    response = client.post(f"{api_prefix}/auth/register", json=duplicate)

    assert response.status_code == 409


def test_email_is_normalized_to_lower_case(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str]
) -> None:
    payload = dict(citizen_payload, email="Grace.Hopper@Example.COM")

    body = client.post(f"{api_prefix}/auth/register", json=payload).json()

    assert body["email"] == "grace.hopper@example.com"


def test_phone_is_optional(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str]
) -> None:
    payload = {
        key: value for key, value in citizen_payload.items() if key != "phone"
    }

    response = client.post(f"{api_prefix}/auth/register", json=payload)

    assert response.status_code == 201
    assert response.json()["phone"] is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("email", "not-an-email"),
        ("email", ""),
        ("password", "short"),
        ("full_name", "A"),
        ("full_name", ""),
        ("phone", "not a phone!"),
    ],
)
def test_invalid_registration_input_returns_422(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    field: str,
    value: str,
) -> None:
    payload = dict(citizen_payload, **{field: value})

    response = client.post(f"{api_prefix}/auth/register", json=payload)

    assert response.status_code == 422
    body = response.json()
    assert body["error"]["code"] == "validation_error"
    assert any(field in detail["field"] for detail in body["error"]["details"])


@pytest.mark.parametrize(
    "escalation",
    [
        {"role": "admin"},
        {"role": "worker"},
        {"is_active": True},
        {"is_verified": True},
        {"department_id": 1},
    ],
)
def test_registration_rejects_attempts_to_set_protected_fields(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    escalation: dict[str, object],
) -> None:
    """A citizen cannot grant themselves privileges at signup."""
    payload = dict(citizen_payload, **escalation)

    response = client.post(f"{api_prefix}/auth/register", json=payload)

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_password_is_stored_as_an_argon2_hash(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    db: Session,
) -> None:
    """The database must never hold a recoverable password."""
    client.post(f"{api_prefix}/auth/register", json=citizen_payload)

    stored = db.query(User).filter(User.email == citizen_payload["email"]).one()

    assert stored.password_hash != citizen_payload["password"]
    assert citizen_payload["password"] not in stored.password_hash
    assert stored.password_hash.startswith("$argon2id$")
    # The stored hash still validates the original password.
    assert verify_password(citizen_payload["password"], stored.password_hash)


def test_the_same_password_hashes_differently_for_two_users(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str], db: Session
) -> None:
    """Confirms a per-password salt: identical passwords must not collide."""
    client.post(f"{api_prefix}/auth/register", json=citizen_payload)
    client.post(
        f"{api_prefix}/auth/register",
        json=dict(citizen_payload, email="grace@example.com"),
    )

    hashes = {user.password_hash for user in db.query(User).all()}

    assert len(hashes) == 2


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------
def test_valid_login_returns_a_token(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": citizen_payload["password"],
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["access_token"]
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == 3600


def test_login_token_carries_the_expected_claims(
    access_token: str,
    registered_citizen: dict[str, object],
    settings: Settings,
) -> None:
    claims = jwt.decode(access_token, settings.SECRET_KEY, algorithms=[ALGORITHM])

    assert claims["sub"] == str(registered_citizen["id"])
    assert claims["type"] == "access"
    assert claims["exp"] > claims["iat"]


def test_login_accepts_a_differently_cased_email(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": "ADA@EXAMPLE.COM", "password": citizen_payload["password"]},
    )

    assert response.status_code == 200


def test_login_with_a_wrong_password_returns_401(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": citizen_payload["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_login_with_an_unknown_email_returns_401(
    client: TestClient, api_prefix: str
) -> None:
    response = client.post(
        f"{api_prefix}/auth/login",
        json={"email": "nobody@example.com", "password": "whatever-password"},
    )

    assert response.status_code == 401


def test_login_failures_are_indistinguishable(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    """The error must not reveal whether an email is registered."""
    unknown = client.post(
        f"{api_prefix}/auth/login",
        json={"email": "nobody@example.com", "password": "whatever-password"},
    )
    wrong_password = client.post(
        f"{api_prefix}/auth/login",
        json={"email": citizen_payload["email"], "password": "wrong-password"},
    )

    assert unknown.status_code == wrong_password.status_code
    assert (
        unknown.json()["error"]["message"]
        == wrong_password.json()["error"]["message"]
    )


def test_inactive_user_cannot_log_in(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    db.query(User).filter(User.id == int(registered_citizen["id"])).update({"is_active": False}); db.commit()

    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": citizen_payload["password"],
        },
    )

    assert response.status_code == 401


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------
def test_me_returns_the_profile_for_a_valid_token(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    response = client.get(f"{api_prefix}/auth/me", headers=auth_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == registered_citizen["id"]
    assert body["email"] == "ada@example.com"
    assert body["role"] == "citizen"
    assert "password" not in body


def test_me_requires_a_token(client: TestClient, api_prefix: str) -> None:
    response = client.get(f"{api_prefix}/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_401_includes_the_www_authenticate_header(
    client: TestClient, api_prefix: str
) -> None:
    response = client.get(f"{api_prefix}/auth/me")

    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    ["Bearer not-a-real-jwt", "Bearer ", "Basic dXNlcjpwYXNz", "token abc.def", ""],
)
def test_me_rejects_malformed_authorization_headers(
    client: TestClient, api_prefix: str, header: str
) -> None:
    response = client.get(f"{api_prefix}/auth/me", headers={"Authorization": header})

    assert response.status_code == 401, response.text
    assert response.json()["error"]["code"] == "unauthorized"


def test_me_rejects_an_expired_token(
    client: TestClient, api_prefix: str, registered_citizen: dict[str, object]
) -> None:
    expired = create_access_token(
        int(registered_citizen["id"]), expires_delta=timedelta(minutes=-5)
    )

    response = client.get(
        f"{api_prefix}/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )

    assert response.status_code == 401
    assert "expired" in response.json()["error"]["message"].lower()


def test_me_rejects_a_token_signed_with_another_key(
    client: TestClient, api_prefix: str, registered_citizen: dict[str, object]
) -> None:
    # At least 32 bytes, so PyJWT does not warn about key length and the test
    # exercises signature rejection rather than a weak-key complaint.
    forged = _forge_token(
        {"sub": str(registered_citizen["id"])},
        "an-attackers-own-signing-key-that-is-long-enough",
    )

    response = client.get(
        f"{api_prefix}/auth/me", headers={"Authorization": f"Bearer {forged}"}
    )

    assert response.status_code == 401


def test_me_rejects_a_token_of_the_wrong_type(
    client: TestClient,
    api_prefix: str,
    registered_citizen: dict[str, object],
    settings: Settings,
) -> None:
    """A non-access token must not be replayable as an access token."""
    refresh_shaped = _forge_token(
        {"sub": str(registered_citizen["id"]), "type": "refresh"},
        settings.SECRET_KEY,
    )

    response = client.get(
        f"{api_prefix}/auth/me",
        headers={"Authorization": f"Bearer {refresh_shaped}"},
    )

    assert response.status_code == 401


def test_me_rejects_a_token_with_a_non_numeric_subject(
    client: TestClient, api_prefix: str, settings: Settings
) -> None:
    bad_subject = _forge_token({"sub": "not-a-number"}, settings.SECRET_KEY)

    response = client.get(
        f"{api_prefix}/auth/me", headers={"Authorization": f"Bearer {bad_subject}"}
    )

    assert response.status_code == 401


def test_me_rejects_a_token_for_a_user_that_no_longer_exists(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    db: Session,
) -> None:
    db.query(User).delete(); db.commit()

    response = client.get(f"{api_prefix}/auth/me", headers=auth_headers)

    assert response.status_code == 401


def test_deactivating_a_user_ends_their_session_immediately(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    """Authorisation follows stored state, not the token's claims."""
    before = client.get(f"{api_prefix}/auth/me", headers=auth_headers)
    assert before.status_code == 200

    db.query(User).filter(User.id == int(registered_citizen["id"])).update({"is_active": False}); db.commit()

    after = client.get(f"{api_prefix}/auth/me", headers=auth_headers)
    assert after.status_code == 401


# ---------------------------------------------------------------------------
# PATCH /me
# ---------------------------------------------------------------------------
def test_profile_update_changes_name_and_phone(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{api_prefix}/auth/me",
        headers=auth_headers,
        json={"full_name": "Ada King", "phone": "+44 20 7946 0958"},
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "Ada King"
    assert body["phone"] == "+44 20 7946 0958"


def test_profile_update_persists(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    client.patch(
        f"{api_prefix}/auth/me",
        headers=auth_headers,
        json={"full_name": "Ada King"},
    )

    body = client.get(f"{api_prefix}/auth/me", headers=auth_headers).json()
    assert body["full_name"] == "Ada King"


def test_partial_update_leaves_other_fields_untouched(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{api_prefix}/auth/me", headers=auth_headers, json={"full_name": "Ada K."}
    )

    assert response.json()["phone"] == "+1 555 0142"


def test_phone_can_be_cleared_with_an_explicit_null(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.patch(
        f"{api_prefix}/auth/me", headers=auth_headers, json={"phone": None}
    )

    assert response.status_code == 200, response.text
    assert response.json()["phone"] is None


def test_profile_update_refreshes_updated_at(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    registered_citizen: dict[str, object],
) -> None:
    response = client.patch(
        f"{api_prefix}/auth/me", headers=auth_headers, json={"full_name": "Ada King"}
    )

    assert response.json()["updated_at"] >= str(registered_citizen["updated_at"])


def test_profile_update_requires_a_token(
    client: TestClient, api_prefix: str
) -> None:
    response = client.patch(f"{api_prefix}/auth/me", json={"full_name": "Hacker"})

    assert response.status_code == 401


def test_empty_profile_update_body_is_rejected(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.patch(f"{api_prefix}/auth/me", headers=auth_headers, json={})

    assert response.status_code == 422


@pytest.mark.parametrize(
    "protected",
    [
        {"role": "admin"},
        {"role": "worker"},
        {"is_active": False},
        {"is_verified": True},
        {"department_id": 3},
        {"email": "someone.else@example.com"},
        {"id": 999},
        {"password": "brand-new-password"},
    ],
)
def test_profile_update_cannot_modify_protected_fields(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    protected: dict[str, object],
) -> None:
    """Self-service edits must not reach role, status or identity fields."""
    response = client.patch(
        f"{api_prefix}/auth/me", headers=auth_headers, json=protected
    )

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "validation_error"


def test_role_survives_an_escalation_attempt(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    registered_citizen: dict[str, object],
    db: Session,
) -> None:
    """Even a rejected request must leave no partial change behind."""
    client.patch(
        f"{api_prefix}/auth/me",
        headers=auth_headers,
        json={"full_name": "Ada King", "role": "admin"},
    )

    stored = db.get(User, int(registered_citizen["id"]))
    assert stored is not None
    assert stored.role == "citizen"
    assert stored.full_name == "Ada Lovelace", "the rejected body must not apply"


# ---------------------------------------------------------------------------
# POST /change-password
# ---------------------------------------------------------------------------
def test_password_change_succeeds_with_the_correct_current_password(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    citizen_payload: dict[str, str],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": citizen_payload["password"],
            "new_password": "a-brand-new-password",
        },
    )

    assert response.status_code == 200, response.text
    assert "message" in response.json()


def test_login_uses_the_new_password_after_a_change(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    citizen_payload: dict[str, str],
) -> None:
    client.post(
        f"{api_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": citizen_payload["password"],
            "new_password": "a-brand-new-password",
        },
    )

    with_new = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": "a-brand-new-password",
        },
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


def test_password_change_rejects_a_wrong_current_password(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "not-my-password",
            "new_password": "a-brand-new-password",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "bad_request"


def test_a_failed_password_change_leaves_the_old_password_working(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    citizen_payload: dict[str, str],
) -> None:
    client.post(
        f"{api_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": "not-my-password",
            "new_password": "a-brand-new-password",
        },
    )

    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": citizen_payload["password"],
        },
    )
    assert response.status_code == 200


def test_password_change_requires_a_token(
    client: TestClient, api_prefix: str
) -> None:
    response = client.post(
        f"{api_prefix}/auth/change-password",
        json={
            "current_password": "whatever-password",
            "new_password": "a-brand-new-password",
        },
    )

    assert response.status_code == 401


def test_password_change_rejects_a_too_short_new_password(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    citizen_payload: dict[str, str],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=auth_headers,
        json={"current_password": citizen_payload["password"], "new_password": "abc"},
    )

    assert response.status_code == 422


def test_password_change_rejects_reusing_the_current_password(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    citizen_payload: dict[str, str],
) -> None:
    response = client.post(
        f"{api_prefix}/auth/change-password",
        headers=auth_headers,
        json={
            "current_password": citizen_payload["password"],
            "new_password": citizen_payload["password"],
        },
    )

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------
def test_logout_returns_a_message(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.post(f"{api_prefix}/auth/logout", headers=auth_headers)

    assert response.status_code == 200, response.text
    assert "discard" in response.json()["message"].lower()


def test_logout_requires_a_token(client: TestClient, api_prefix: str) -> None:
    response = client.post(f"{api_prefix}/auth/logout")

    assert response.status_code == 401


def test_token_still_works_after_logout(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    """Documents the stateless-JWT limitation: logout cannot revoke a token.

    The client is responsible for discarding it. If this ever starts failing,
    server-side revocation has been added and the README must be updated.
    """
    client.post(f"{api_prefix}/auth/logout", headers=auth_headers)

    response = client.get(f"{api_prefix}/auth/me", headers=auth_headers)
    assert response.status_code == 200


# ---------------------------------------------------------------------------
# Multi-user isolation
# ---------------------------------------------------------------------------
def test_users_only_see_and_edit_their_own_profile(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str]
) -> None:
    client.post(f"{api_prefix}/auth/register", json=citizen_payload)
    second = dict(citizen_payload, email="grace@example.com", full_name="Grace Hopper")
    client.post(f"{api_prefix}/auth/register", json=second)

    def token_for(email: str) -> str:
        response = client.post(
            f"{api_prefix}/auth/login",
            json={"email": email, "password": citizen_payload["password"]},
        )
        assert response.status_code == 200, response.text
        return response.json()["access_token"]

    ada_headers = {"Authorization": f"Bearer {token_for('ada@example.com')}"}
    grace_headers = {"Authorization": f"Bearer {token_for('grace@example.com')}"}

    client.patch(
        f"{api_prefix}/auth/me", headers=grace_headers, json={"full_name": "Grace M. H."}
    )

    ada = client.get(f"{api_prefix}/auth/me", headers=ada_headers).json()
    grace = client.get(f"{api_prefix}/auth/me", headers=grace_headers).json()

    assert ada["email"] == "ada@example.com"
    assert ada["full_name"] == "Ada Lovelace", "Grace's edit must not touch Ada"
    assert grace["full_name"] == "Grace M. H."
    assert ada["id"] != grace["id"]


def test_auth_endpoints_are_documented_in_openapi(
    client: TestClient, api_prefix: str
) -> None:
    schema = client.get("/openapi.json").json()

    assert f"{api_prefix}/auth/register" in schema["paths"]
    assert f"{api_prefix}/auth/login" in schema["paths"]
    operations = schema["paths"][f"{api_prefix}/auth/me"]
    assert set(operations) >= {"get", "patch"}
