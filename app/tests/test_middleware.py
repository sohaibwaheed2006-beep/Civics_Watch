"""Request correlation middleware and log redaction."""

from __future__ import annotations

import logging

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import (
    REQUEST_ID_HEADER,
    RedactSecretsFilter,
    RequestIdFilter,
    get_request_id,
)


class _CapturingHandler(logging.Handler):
    """Collects records, with the application's filters applied."""

    def __init__(self) -> None:
        super().__init__(level=logging.DEBUG)
        self.records: list[logging.LogRecord] = []
        self.addFilter(RequestIdFilter())
        self.addFilter(RedactSecretsFilter())

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)

    @property
    def messages(self) -> list[str]:
        return [record.getMessage() for record in self.records]


@pytest.fixture
def captured_logs() -> list[logging.LogRecord]:
    """Capture records from the ``app`` logger tree.

    ``caplog`` cannot be used here: the ``app`` logger sets
    ``propagate=False``, so its records never reach the root handler that
    ``caplog`` installs.
    """
    handler = _CapturingHandler()
    app_logger = logging.getLogger("app")
    app_logger.addHandler(handler)
    previous_level = app_logger.level
    app_logger.setLevel(logging.DEBUG)
    try:
        yield handler.records
    finally:
        app_logger.removeHandler(handler)
        app_logger.setLevel(previous_level)


# ---------------------------------------------------------------------------
# Correlation ID propagation
# ---------------------------------------------------------------------------
def test_request_log_line_carries_the_request_id(
    client: TestClient, captured_logs: list[logging.LogRecord]
) -> None:
    """Regression guard: the ID must not be reset before the access log runs."""
    response = client.get("/health", headers={REQUEST_ID_HEADER: "log-trace-7"})

    assert response.headers[REQUEST_ID_HEADER] == "log-trace-7"

    access_lines = [
        record
        for record in captured_logs
        if record.name == "app.core.middleware" and "/health" in record.getMessage()
    ]
    assert access_lines, "the middleware emitted no access log line"
    assert all(
        getattr(record, "request_id", None) == "log-trace-7" for record in access_lines
    ), [getattr(r, "request_id", None) for r in access_lines]


def test_request_state_exposes_the_request_id(settings: Settings) -> None:
    """Endpoints and dependencies can read the ID off ``request.state``."""
    from app.main import create_app

    probe_app = create_app(settings)

    @probe_app.get("/_state")
    async def read_state(request: Request) -> dict[str, str | None]:
        return {
            "from_state": request.state.request_id,
            "from_contextvar": get_request_id(),
        }

    with TestClient(probe_app) as probe_client:
        response = probe_client.get(
            "/_state", headers={REQUEST_ID_HEADER: "state-trace-9"}
        )

    body = response.json()
    assert body["from_state"] == "state-trace-9"
    assert body["from_contextvar"] == "state-trace-9"


def test_each_request_gets_a_distinct_generated_id(client: TestClient) -> None:
    first = client.get("/health").headers[REQUEST_ID_HEADER]
    second = client.get("/health").headers[REQUEST_ID_HEADER]

    assert first != second


def test_response_time_header_is_present_and_numeric(client: TestClient) -> None:
    value = client.get("/health").headers["X-Response-Time-ms"]

    assert float(value) >= 0


def test_request_id_is_not_leaked_between_requests(client: TestClient) -> None:
    """After a request completes, the context variable is cleared."""
    client.get("/health", headers={REQUEST_ID_HEADER: "transient"})

    assert get_request_id() is None


@pytest.mark.parametrize(
    "hostile",
    [
        "has spaces",
        "semi;colon",
        "new\nline",
        "tab\there",
        "x" * 200,
        "",
    ],
)
def test_unsafe_inbound_ids_are_replaced(client: TestClient, hostile: str) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: hostile})

    returned = response.headers[REQUEST_ID_HEADER]
    assert returned != hostile
    assert returned.isalnum()


@pytest.mark.parametrize("safe", ["abc123", "trace-1_2.3", "A" * 128])
def test_safe_inbound_ids_are_preserved(client: TestClient, safe: str) -> None:
    response = client.get("/health", headers={REQUEST_ID_HEADER: safe})

    assert response.headers[REQUEST_ID_HEADER] == safe


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("message", "secret"),
    [
        ("login attempt password=hunter2 for user 4", "hunter2"),
        ('payload {"password": "s3cr3t!"} rejected', "s3cr3t!"),
        ("SECRET_KEY=super-long-signing-value", "super-long-signing-value"),
        ("header Authorization: Bearer eyJhbGciOi.JzdWIiOiI.xyz", "eyJhbGciOi"),
        ("access_token=abc.def.ghi issued", "abc.def.ghi"),
        ("connecting to mysql+pymysql://root:dbpass@127.0.0.1/app", "dbpass"),
    ],
)
def test_redaction_filter_masks_credentials(message: str, secret: str) -> None:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )

    assert RedactSecretsFilter().filter(record) is True
    assert secret not in record.getMessage()
    assert "***REDACTED***" in record.getMessage()


def test_redaction_leaves_ordinary_messages_untouched() -> None:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="GET /health -> 200 in 1.09ms",
        args=(),
        exc_info=None,
    )

    RedactSecretsFilter().filter(record)

    assert record.getMessage() == "GET /health -> 200 in 1.09ms"


def test_request_id_filter_defaults_to_a_dash_outside_a_request() -> None:
    record = logging.LogRecord(
        name="app.test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="startup",
        args=(),
        exc_info=None,
    )

    RequestIdFilter().filter(record)

    assert record.request_id == "-"  # type: ignore[attr-defined]
