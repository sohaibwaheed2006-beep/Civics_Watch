"""Health endpoint behaviour."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import REQUEST_ID_HEADER

pytestmark = pytest.mark.smoke


def test_health_returns_200_and_ok_status(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"


def test_health_reports_app_identity(client: TestClient, settings: Settings) -> None:
    body = client.get("/health").json()

    assert body["app_name"] == settings.APP_NAME
    assert body["environment"] == settings.APP_ENV
    assert body["version"]
    assert body["timestamp"]


def test_health_does_not_leak_configuration(client: TestClient) -> None:
    """A public liveness probe must not expose secrets or infrastructure."""
    raw = client.get("/health").text.lower()

    for forbidden in (
        "secret",
        "password",
        "database_url",
        "mysql",
        "token",
        "cors",
        "upload_dir",
    ):
        assert forbidden not in raw, f"/health leaked {forbidden!r}"


def test_health_response_carries_request_id_header(client: TestClient) -> None:
    response = client.get("/health")

    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id
    assert len(request_id) >= 8


def test_health_echoes_a_supplied_request_id(client: TestClient) -> None:
    """A trace started upstream survives into our response."""
    response = client.get("/health", headers={REQUEST_ID_HEADER: "trace-abc-123"})

    assert response.headers[REQUEST_ID_HEADER] == "trace-abc-123"


def test_health_rejects_a_hostile_request_id(client: TestClient) -> None:
    """An unsafe inbound ID is replaced rather than echoed."""
    response = client.get(
        "/health", headers={REQUEST_ID_HEADER: "bad id\twith junk;"}
    )

    assert response.headers[REQUEST_ID_HEADER] != "bad id\twith junk;"


def test_root_index_points_at_docs_and_api(
    client: TestClient, settings: Settings
) -> None:
    body = client.get("/").json()

    assert body["api_v1"] == settings.API_V1_PREFIX
    assert body["health"] == "/health"
    assert body["docs"] == "/docs"


def test_health_only_allows_get(client: TestClient) -> None:
    assert client.post("/health").status_code == 405
