"""User and department administration endpoints.

Covers the six routes added in this phase: access control, persistence, and
the guards that stop an administrator locking everyone out.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import UserRole
from app.models.department import Department
from app.models.user import User


# ---------------------------------------------------------------------------
# GET /users/ - access control
# ---------------------------------------------------------------------------
def test_admin_can_list_users(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_user
) -> None:
    make_user(email="one@example.com")
    make_user(email="two@example.com")

    response = client.get(f"{api_prefix}/users/", headers=admin_headers)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["meta"]["total_items"] == 3  # two citizens + the admin
    assert len(body["items"]) == 3


def test_user_list_never_exposes_password_material(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_user
) -> None:
    make_user(email="one@example.com")

    body = client.get(f"{api_prefix}/users/", headers=admin_headers).json()

    for item in body["items"]:
        for leaked in ("password", "password_hash", "hashed_password"):
            assert leaked not in item
    assert "argon2" not in client.get(
        f"{api_prefix}/users/", headers=admin_headers
    ).text


def test_citizen_cannot_list_users(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    response = client.get(f"{api_prefix}/users/", headers=auth_headers)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


def test_worker_cannot_list_users(
    client: TestClient, api_prefix: str, worker_headers: dict[str, str]
) -> None:
    response = client.get(f"{api_prefix}/users/", headers=worker_headers)

    assert response.status_code == 403


def test_listing_users_requires_authentication(
    client: TestClient, api_prefix: str
) -> None:
    response = client.get(f"{api_prefix}/users/")

    assert response.status_code == 401
