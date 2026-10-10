"""OpenAPI schema generation and the interactive documentation."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings

pytestmark = pytest.mark.smoke


def test_openapi_json_is_served(client: TestClient) -> None:
    response = client.get("/openapi.json")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")


def test_openapi_schema_is_well_formed(
    client: TestClient, settings: Settings
) -> None:
    schema = client.get("/openapi.json").json()

    assert schema["openapi"].startswith("3.")
    assert schema["info"]["title"] == settings.APP_NAME
    assert schema["info"]["version"]
    assert "/health" in schema["paths"]


def test_openapi_generation_does_not_raise(app: FastAPI) -> None:
    """Generate the schema directly: this is where bad type hints surface."""
    schema = app.openapi()

    assert schema["paths"]
    assert "components" in schema


def test_swagger_ui_is_available(client: TestClient) -> None:
    response = client.get("/docs")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "swagger-ui" in response.text.lower()


def test_redoc_is_available(client: TestClient) -> None:
    response = client.get("/redoc")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_health_documents_its_response_model(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/health"]["get"]

    content = operation["responses"]["200"]["content"]["application/json"]
    assert "$ref" in content["schema"]


def test_error_envelope_is_documented(client: TestClient) -> None:
    """Clients should be able to generate the error type from the schema."""
    schema = client.get("/openapi.json").json()

    assert "ErrorResponse" in schema["components"]["schemas"]
    error_body = schema["components"]["schemas"]["ErrorBody"]["properties"]
    assert set(error_body) >= {"code", "message", "details", "request_id"}


def test_docs_are_disabled_in_production() -> None:
    """Interactive docs must not be reachable on a production deployment."""
    from app.main import create_app

    prod_settings = Settings(
        APP_ENV="production",
        DEBUG=False,
        SECRET_KEY="a-real-production-secret-value-for-this-test-only",
    )
    prod_app = create_app(prod_settings)

    with TestClient(prod_app) as prod_client:
        assert prod_client.get("/docs").status_code == 404
        assert prod_client.get("/openapi.json").status_code == 404
        # The liveness probe stays available.
        assert prod_client.get("/health").status_code == 200
