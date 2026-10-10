"""Report domain tests (Developer 2).

Covers the citizen workflow, authorization, status transitions, assignments,
votes, photos, notifications, deadline math and analytics.
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.enums import ReportCategory, ReportPriority, ReportStatus, UserRole
from app.models.report import Report
from app.models.status_history import StatusHistory
from app.services import deadline_service, duplicate_detection_service
from app.services.ai_service import suggest_category, suggest_priority


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_REPORT: dict[str, Any] = {
    "title": "Massive pothole on 5th street",
    "description": "A dangerous pothole has formed near the intersection.",
    "category": "road_damage",
    "latitude": 40.7128,
    "longitude": -74.0060,
    "location_text": "5th & Main",
}


def _post_report(
    client: TestClient, api_prefix: str, headers: dict[str, str],
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    body = dict(VALID_REPORT)
    if overrides:
        body.update(overrides)
    response = client.post(
        f"{api_prefix}/reports", json=body, headers=headers
    )
    assert response.status_code == 201, response.text
    return response.json()


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------
class TestCreateReport:
    def test_citizen_can_create(
        self, client, api_prefix, auth_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        assert data["status"] == ReportStatus.SUBMITTED.value
        assert data["category"] == ReportCategory.ROAD_DAMAGE.value
        assert data["vote_count"] == 0
        assert data["deadline_at"] is not None

    def test_requires_authentication(self, client, api_prefix) -> None:
        response = client.post(f"{api_prefix}/reports", json=VALID_REPORT)
        assert response.status_code == 401

    @pytest.mark.parametrize(
        "lat,lon",
        [(91, 0), (-91, 0), (0, 181), (0, -181), (100, 200)],
    )
    def test_invalid_coordinates_rejected(
        self, client, api_prefix, auth_headers, lat, lon
    ) -> None:
        body = dict(VALID_REPORT, latitude=lat, longitude=lon)
        response = client.post(
            f"{api_prefix}/reports", json=body, headers=auth_headers
        )
        assert response.status_code == 422

    def test_invalid_category_rejected(
        self, client, api_prefix, auth_headers
    ) -> None:
        body = dict(VALID_REPORT, category="not_a_category")
        response = client.post(
            f"{api_prefix}/reports", json=body, headers=auth_headers
        )
        assert response.status_code == 422

    def test_citizen_cannot_set_status_or_priority(
        self, client, api_prefix, auth_headers
    ) -> None:
        body = dict(VALID_REPORT, status="resolved", priority="urgent")
        response = client.post(
            f"{api_prefix}/reports", json=body, headers=auth_headers
        )
        # extra="forbid" on the schema -> 422
        assert response.status_code == 422

    def test_initial_history_recorded(
        self, client, api_prefix, auth_headers, db: Session
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        history = (
            db.query(StatusHistory)
            .filter(StatusHistory.report_id == data["id"])
            .all()
        )
        assert len(history) == 1
        assert history[0].new_status == ReportStatus.SUBMITTED
        assert history[0].old_status is None


# ---------------------------------------------------------------------------
# List, get, filters, privacy
# ---------------------------------------------------------------------------
class TestListAndGet:
    def test_my_reports_isolated(
        self, client, api_prefix, auth_headers, make_user, login
    ) -> None:
        _post_report(client, api_prefix, auth_headers)
        # A second citizen should not see the first's reports under /my.
        other = make_user(email="bob@example.com", full_name="Bob")
        other_headers = login(other.email)
        response = client.get(
            f"{api_prefix}/reports/my", headers=other_headers
        )
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_map_endpoint_returns_minimal_fields(
        self, client, api_prefix, auth_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        response = client.get(
            f"{api_prefix}/reports/map", headers=auth_headers
        )
        assert response.status_code == 200
        markers = response.json()
        assert any(m["id"] == data["id"] for m in markers)
        for m in markers:
            assert set(m.keys()) == {
                "id",
                "category",
                "status",
                "priority",
                "latitude",
                "longitude",
            }

    def test_filter_by_status(
        self, client, api_prefix, auth_headers, admin_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        # Admin moves to under_review.
        client.post(
            f"{api_prefix}/reports/{data['id']}/status",
            json={"status": "under_review"},
            headers=admin_headers,
        )
        response = client.get(
            f"{api_prefix}/reports?status=submitted", headers=admin_headers
        )
        assert response.status_code == 200
        ids = [item["id"] for item in response.json()["items"]]
        assert data["id"] not in ids


# ---------------------------------------------------------------------------
# Status workflow
# ---------------------------------------------------------------------------
class TestStatusWorkflow:
    def test_valid_transition(
        self, client, api_prefix, auth_headers, admin_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/status",
            json={"status": "under_review", "note": "triaging"},
            headers=admin_headers,
        )
        assert r.status_code == 200
        assert r.json()["status"] == "under_review"

    def test_invalid_transition_rejected(
        self, client, api_prefix, auth_headers, admin_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        # submitted -> resolved is not allowed by the matrix.
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/status",
            json={"status": "resolved"},
            headers=admin_headers,
        )
        assert r.status_code == 409

    def test_citizen_cannot_change_status(
        self, client, api_prefix, auth_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/status",
            json={"status": "under_review"},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_citizen_can_reopen_own_resolved(
        self, client, api_prefix, auth_headers, admin_headers,
        make_user, login, make_department, db
    ) -> None:
        # Submit, then run through the matrix as admin: submitted -> under_review
        # -> assigned -> in_progress -> resolved. Then the owner reopens.
        dept = make_department(name="Roads & Pavements")
        worker = make_user(
            email="w@example.com", role=UserRole.WORKER, department_id=dept.id
        )
        data = _post_report(client, api_prefix, auth_headers)
        rid = data["id"]
        client.post(
            f"{api_prefix}/reports/{rid}/status",
            json={"status": "under_review"},
            headers=admin_headers,
        )
        # Admin assigns the worker.
        client.post(
            f"{api_prefix}/reports/{rid}/assign",
            json={"worker_id": worker.id},
            headers=admin_headers,
        )
        worker_headers = login(worker.email)
        client.post(
            f"{api_prefix}/reports/{rid}/status",
            json={"status": "in_progress"},
            headers=worker_headers,
        )
        client.post(
            f"{api_prefix}/reports/{rid}/status",
            json={"status": "resolved"},
            headers=worker_headers,
        )
        r = client.post(
            f"{api_prefix}/reports/{rid}/status",
            json={"status": "reopened"},
            headers=auth_headers,
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "reopened"

    def test_every_transition_writes_history(
        self, client, api_prefix, auth_headers, admin_headers, db: Session
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        client.post(
            f"{api_prefix}/reports/{data['id']}/status",
            json={"status": "under_review"},
            headers=admin_headers,
        )
        rows = (
            db.query(StatusHistory)
            .filter(StatusHistory.report_id == data["id"])
            .order_by(StatusHistory.created_at.asc())
            .all()
        )
        assert len(rows) == 2
        assert rows[0].new_status == ReportStatus.SUBMITTED
        assert rows[1].old_status == ReportStatus.SUBMITTED
        assert rows[1].new_status == ReportStatus.UNDER_REVIEW


# ---------------------------------------------------------------------------
# Assignment
# ---------------------------------------------------------------------------
class TestAssignment:
    def test_admin_can_assign_worker(
        self, client, api_prefix, auth_headers, admin_headers,
        make_user, make_department
    ) -> None:
        dept = make_department(name="Roads & Pavements")
        worker = make_user(
            email="w@example.com", role=UserRole.WORKER, department_id=dept.id
        )
        data = _post_report(client, api_prefix, auth_headers)
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/assign",
            json={"worker_id": worker.id},
            headers=admin_headers,
        )
        assert r.status_code == 201, r.text
        assert r.json()["active"] is True

    def test_cannot_assign_non_worker(
        self, client, api_prefix, auth_headers, admin_headers, make_user
    ) -> None:
        citizen = make_user(email="c@example.com", role=UserRole.CITIZEN)
        data = _post_report(client, api_prefix, auth_headers)
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/assign",
            json={"worker_id": citizen.id},
            headers=admin_headers,
        )
        assert r.status_code == 422

    def test_citizen_cannot_assign(
        self, client, api_prefix, auth_headers, make_user
    ) -> None:
        worker = make_user(email="w@example.com", role=UserRole.WORKER)
        data = _post_report(client, api_prefix, auth_headers)
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/assign",
            json={"worker_id": worker.id},
            headers=auth_headers,
        )
        assert r.status_code == 403

    def test_reassignment_closes_previous(
        self, client, api_prefix, auth_headers, admin_headers,
        make_user, make_department, db
    ) -> None:
        dept = make_department(name="Roads & Pavements")
        worker_a = make_user(
            email="a@example.com", role=UserRole.WORKER, department_id=dept.id
        )
        worker_b = make_user(
            email="b@example.com", role=UserRole.WORKER, department_id=dept.id
        )
        data = _post_report(client, api_prefix, auth_headers)
        rid = data["id"]
        client.post(
            f"{api_prefix}/reports/{rid}/assign",
            json={"worker_id": worker_a.id},
            headers=admin_headers,
        )
        client.post(
            f"{api_prefix}/reports/{rid}/assign",
            json={"worker_id": worker_b.id},
            headers=admin_headers,
        )
        from app.models.assignment import Assignment
        rows = (
            db.query(Assignment)
            .filter(Assignment.report_id == rid)
            .order_by(Assignment.id.asc())
            .all()
        )
        assert len(rows) == 2
        assert rows[0].active is False
        assert rows[0].unassigned_at is not None
        assert rows[1].active is True


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------
class TestVotes:
    def test_vote_add_and_remove(
        self, client, api_prefix, auth_headers, make_user, login
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        voter = make_user(email="v@example.com")
        headers = login(voter.email)

        r = client.post(
            f"{api_prefix}/reports/{data['id']}/vote", headers=headers
        )
        assert r.status_code == 201
        assert r.json()["count"] == 1

        # Idempotent re-vote.
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/vote", headers=headers
        )
        assert r.status_code == 201
        assert r.json()["count"] == 1

        r = client.delete(
            f"{api_prefix}/reports/{data['id']}/vote", headers=headers
        )
        assert r.status_code == 200
        assert r.json()["count"] == 0

    def test_cannot_vote_on_own_report(
        self, client, api_prefix, auth_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/vote", headers=auth_headers
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Photos
# ---------------------------------------------------------------------------
# A minimal 1x1 JPEG (SOI, APP0 JFIF, SOF0, DQT, DHT, SOS, EOI). The sniffer
# only checks the SOI prefix, so this is sufficient.
_FAKE_JPEG = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707"
    "0709090808"
) + b"\x00" * 32 + b"\xff\xd9"


class TestPhotos:
    def test_upload_and_list(
        self, client, api_prefix, auth_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        files = {"file": ("photo.jpg", BytesIO(_FAKE_JPEG), "image/jpeg")}
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/photos",
            files=files,
            headers=auth_headers,
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["content_type"] == "image/jpeg"
        assert "url" in body
        assert "storage_key" not in body  # internal path never leaked

        r = client.get(
            f"{api_prefix}/reports/{data['id']}/photos",
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert len(r.json()) == 1

    def test_reject_non_image(
        self, client, api_prefix, auth_headers
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        files = {"file": ("evil.txt", BytesIO(b"not an image"), "text/plain")}
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/photos",
            files=files,
            headers=auth_headers,
        )
        assert r.status_code == 400

    def test_other_user_cannot_upload(
        self, client, api_prefix, auth_headers, make_user, login
    ) -> None:
        data = _post_report(client, api_prefix, auth_headers)
        other = make_user(email="z@example.com")
        other_headers = login(other.email)
        files = {"file": ("photo.jpg", BytesIO(_FAKE_JPEG), "image/jpeg")}
        r = client.post(
            f"{api_prefix}/reports/{data['id']}/photos",
            files=files,
            headers=other_headers,
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------
class TestNotifications:
    def test_submission_creates_notification(
        self, client, api_prefix, auth_headers
    ) -> None:
        _post_report(client, api_prefix, auth_headers)
        r = client.get(
            f"{api_prefix}/notifications/unread-count", headers=auth_headers
        )
        assert r.status_code == 200
        assert r.json()["unread"] >= 1

    def test_mark_read_isolated_by_user(
        self, client, api_prefix, auth_headers, make_user, login
    ) -> None:
        _post_report(client, api_prefix, auth_headers)
        # Another user may not read the first user's notifications.
        other = make_user(email="other@example.com")
        other_headers = login(other.email)
        page = client.get(
            f"{api_prefix}/notifications", headers=auth_headers
        ).json()
        notif_id = page["items"][0]["id"]
        r = client.patch(
            f"{api_prefix}/notifications/{notif_id}/read",
            headers=other_headers,
        )
        assert r.status_code == 403


# ---------------------------------------------------------------------------
# Pure service units
# ---------------------------------------------------------------------------
class TestDeadlineService:
    def test_urgent_shorter_than_low(self, make_department) -> None:
        dept = make_department(default_sla_hours=72)
        urgent = deadline_service.compute_deadline(
            priority=ReportPriority.URGENT, department=dept
        )
        low = deadline_service.compute_deadline(
            priority=ReportPriority.LOW, department=dept
        )
        assert urgent < low


class TestDuplicateDetection:
    def test_haversine_zero(self) -> None:
        assert duplicate_detection_service.haversine_meters(
            40.0, -74.0, 40.0, -74.0
        ) == pytest.approx(0.0, abs=1e-6)

    def test_similarity_identical(self) -> None:
        assert duplicate_detection_service.similarity_score(
            "pothole on 5th", "pothole on 5th"
        ) == pytest.approx(1.0)


class TestAiService:
    def test_deterministic_road(self) -> None:
        suggestion = suggest_category("Pothole on road", "big pothole here")
        assert suggestion is not None
        assert suggestion.category == ReportCategory.ROAD_DAMAGE

    def test_urgent_keyword_escalates_priority(self) -> None:
        p = suggest_priority(
            category=ReportCategory.GARBAGE,
            title="DANGER - overflowing bin",
            description="urgent cleanup needed",
        )
        assert p == ReportPriority.URGENT


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------
class TestAnalytics:
    def test_overview_available_to_admin(
        self, client, api_prefix, admin_headers, auth_headers
    ) -> None:
        _post_report(client, api_prefix, auth_headers)
        r = client.get(
            f"{api_prefix}/analytics/overview", headers=admin_headers
        )
        assert r.status_code == 200
        body = r.json()
        assert body["total_reports"] >= 1
        assert "open_reports" in body
        assert "overdue_reports" in body

    def test_citizen_blocked_from_analytics(
        self, client, api_prefix, auth_headers
    ) -> None:
        r = client.get(
            f"{api_prefix}/analytics/overview", headers=auth_headers
        )
        assert r.status_code == 403
