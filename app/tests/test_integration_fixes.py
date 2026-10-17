"""Regression tests for the frontend/backend contract fixes.

These cover the routes the React services rely on that were previously missing
or mismatched: worker creation, admin user edits, the vote toggle, and report
search. They lock the contract so the drift that the mock fallback used to hide
cannot silently return.
"""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User


# ---------------------------------------------------------------------------
# POST /users/workers - create a worker account
# ---------------------------------------------------------------------------
def test_admin_can_create_worker(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_department
) -> None:
    dept = make_department(name="Electrical")

    response = client.post(
        f"{api_prefix}/users/workers",
        headers=admin_headers,
        json={
            "full_name": "Field Tech",
            "email": "field.tech@example.com",
            "password": "correct-horse-battery",
            "phone": "+1 555 0100",
            "department_id": dept.id,
        },
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "worker"
    assert body["department_id"] == dept.id
    assert body["is_active"] is True
    assert body["is_verified"] is True
    # The created worker can immediately sign in.
    login = client.post(
        f"{api_prefix}/auth/login",
        json={"email": "field.tech@example.com", "password": "correct-horse-battery"},
    )
    assert login.status_code == 200, login.text


def test_create_worker_rejects_duplicate_email(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_department, make_user
) -> None:
    dept = make_department(name="Plumbing")
    make_user(email="taken@example.com")

    response = client.post(
        f"{api_prefix}/users/workers",
        headers=admin_headers,
        json={
            "full_name": "Field Tech",
            "email": "taken@example.com",
            "password": "correct-horse-battery",
            "department_id": dept.id,
        },
    )
    assert response.status_code == 409, response.text


def test_create_worker_requires_existing_department(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{api_prefix}/users/workers",
        headers=admin_headers,
        json={
            "full_name": "Field Tech",
            "email": "nodept@example.com",
            "password": "correct-horse-battery",
            "department_id": 9999,
        },
    )
    assert response.status_code == 404, response.text


def test_citizen_cannot_create_worker(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str], make_department
) -> None:
    dept = make_department(name="General Works")
    response = client.post(
        f"{api_prefix}/users/workers",
        headers=auth_headers,
        json={
            "full_name": "x",
            "email": "x@example.com",
            "password": "correct-horse-battery",
            "department_id": dept.id,
        },
    )
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# PATCH /users/{id} - admin edit of profile / status / role
# ---------------------------------------------------------------------------
def test_admin_can_edit_user_profile(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_user
) -> None:
    user = make_user(email="edit.me@example.com", full_name="Before")

    response = client.patch(
        f"{api_prefix}/users/{user.id}",
        headers=admin_headers,
        json={"full_name": "After", "phone": "+1 555 0199"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["full_name"] == "After"
    assert body["phone"] == "+1 555 0199"


def test_admin_can_deactivate_user(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_user
) -> None:
    user = make_user(email="deact@example.com")
    response = client.patch(
        f"{api_prefix}/users/{user.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert response.status_code == 200, response.text
    assert response.json()["is_active"] is False


def test_admin_cannot_demote_self(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], db: Session
) -> None:
    me = db.query(User).filter_by(email="admin@example.com").one()
    response = client.patch(
        f"{api_prefix}/users/{me.id}",
        headers=admin_headers,
        json={"role": "citizen"},
    )
    assert response.status_code == 403, response.text


def test_admin_cannot_deactivate_last_admin(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], db: Session
) -> None:
    me = db.query(User).filter_by(email="admin@example.com").one()
    response = client.patch(
        f"{api_prefix}/users/{me.id}",
        headers=admin_headers,
        json={"is_active": False},
    )
    assert response.status_code == 403, response.text


def test_patch_user_rejects_empty_body(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], make_user
) -> None:
    user = make_user(email="empty@example.com")
    response = client.patch(
        f"{api_prefix}/users/{user.id}", headers=admin_headers, json={}
    )
    assert response.status_code == 422, response.text


# ---------------------------------------------------------------------------
# POST /reports/{id}/upvote - vote toggle
# ---------------------------------------------------------------------------
def _create_report(client: TestClient, api_prefix: str, headers: dict[str, str]) -> int:
    response = client.post(
        f"{api_prefix}/reports",
        headers=headers,
        json={
            "title": "Broken streetlight on Elm",
            "description": "The light has been out for a week near the corner.",
            "category": "streetlight",
            "latitude": 40.0,
            "longitude": -74.0,
            "location_text": "Elm & 3rd",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_upvote_toggles_on_and_off(
    client: TestClient,
    api_prefix: str,
    auth_headers: dict[str, str],
    make_user,
    login,
) -> None:
    # Citizen A owns the report; citizen B votes on it.
    report_id = _create_report(client, api_prefix, auth_headers)
    make_user(email="voter@example.com")
    voter = login("voter@example.com")

    on = client.post(f"{api_prefix}/reports/{report_id}/upvote", headers=voter)
    assert on.status_code == 200, on.text
    assert on.json() == {"report_id": report_id, "count": 1, "voted": True}

    off = client.post(f"{api_prefix}/reports/{report_id}/upvote", headers=voter)
    assert off.status_code == 200, off.text
    assert off.json() == {"report_id": report_id, "count": 0, "voted": False}


def test_cannot_upvote_own_report(
    client: TestClient, api_prefix: str, auth_headers: dict[str, str]
) -> None:
    report_id = _create_report(client, api_prefix, auth_headers)
    response = client.post(f"{api_prefix}/reports/{report_id}/upvote", headers=auth_headers)
    assert response.status_code == 403, response.text


# ---------------------------------------------------------------------------
# GET /reports?search= - report search
# ---------------------------------------------------------------------------
def test_report_search_matches_title_and_description(
    client: TestClient, api_prefix: str, admin_headers: dict[str, str], auth_headers
) -> None:
    _create_report(client, api_prefix, auth_headers)  # "Broken streetlight on Elm"
    client.post(
        f"{api_prefix}/reports",
        headers=auth_headers,
        json={
            "title": "Pothole on Main",
            "description": "Deep pothole near the bakery.",
            "category": "road_damage",
            "latitude": 40.1,
            "longitude": -74.1,
            "location_text": "Main St",
        },
    )

    hit = client.get(f"{api_prefix}/reports", headers=admin_headers, params={"search": "pothole"})
    assert hit.status_code == 200, hit.text
    titles = [r["title"] for r in hit.json()["items"]]
    assert titles == ["Pothole on Main"]

    none = client.get(f"{api_prefix}/reports", headers=admin_headers, params={"search": "zzznomatch"})
    assert none.status_code == 200, none.text
    assert none.json()["items"] == []
