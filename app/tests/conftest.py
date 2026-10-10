"""Shared pytest fixtures.

The environment is pinned *before* ``app`` is imported so a developer's local
``.env`` cannot change test outcomes. ``Settings`` reads the process
environment first, and environment variables take precedence over the ``.env``
file, so setting them here is sufficient.

Database
--------
Tests run against a throwaway in-memory SQLite database, so the suite needs no
MySQL server. Schema is created with ``Base.metadata.create_all`` - acceptable
here because the database is discarded immediately. Alembic remains the only
supported way to change a real schema; ``test_migrations.py`` covers that the
migration and the models agree.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path
from typing import Iterator

import pytest

# A temporary *file* database, not ``:memory:``. The application's lifespan
# shutdown calls ``dispose_engine()``, and disposing the pool of an in-memory
# SQLite database destroys the database with it - so the schema would vanish
# after the first test that used the ``client`` fixture. A file survives
# disposal; the engine simply opens a fresh connection to it.
_TEST_DB_DIR = tempfile.mkdtemp(prefix="nir-tests-")
_TEST_DB_PATH = Path(_TEST_DB_DIR) / "test.db"

# --- Deterministic environment (must precede any `app` import) -------------
os.environ["APP_ENV"] = "test"
os.environ["APP_NAME"] = "Neighborhood Issue Reporter API"
os.environ["DEBUG"] = "false"
os.environ["API_V1_PREFIX"] = "/api/v1"
os.environ["SECRET_KEY"] = "test-only-secret-key-not-used-in-any-real-env"
os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = "60"
os.environ["CORS_ORIGINS"] = "http://localhost:3000,http://localhost:5173"
os.environ["UPLOAD_DIR"] = "uploads"
os.environ["MAX_UPLOAD_SIZE_MB"] = "5"
# Override whatever .env holds: never touch a real database from a test.
os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{_TEST_DB_PATH.as_posix()}"
os.environ["DB_ECHO"] = "false"

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.core.config import Settings, get_settings  # noqa: E402
from app.core.enums import UserRole  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.registry import target_metadata  # noqa: E402
from app.db.session import (  # noqa: E402
    get_db,
    get_engine,
    get_session_factory,
    reset_engine,
)
from app.main import create_app  # noqa: E402
from app.models.department import Department  # noqa: E402
from app.models.user import User  # noqa: E402


@pytest.fixture(scope="session")
def settings() -> Settings:
    """The settings instance the application under test is built with."""
    get_settings.cache_clear()
    return get_settings()


# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _create_schema(settings: Settings) -> Iterator[None]:
    """Create the schema once, then delete the temporary database.

    ``create_all`` is acceptable here because the database is a throwaway
    file. Alembic remains the only supported way to change a real schema;
    ``test_migrations.py`` checks that the migration and the models agree.
    """
    target_metadata.create_all(bind=get_engine())
    yield
    reset_engine()
    shutil.rmtree(_TEST_DB_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def clean_tables(settings: Settings) -> Iterator[None]:
    """Empty every table around each test.

    The database is shared for the whole session, so without this a user
    created in one test would leak into the next and make results depend on
    execution order.
    """
    engine = get_engine()

    def _wipe() -> None:
        with engine.begin() as connection:
            # Reverse dependency order: users references departments.
            for table in reversed(target_metadata.sorted_tables):
                connection.execute(table.delete())

    _wipe()
    yield
    _wipe()


@pytest.fixture
def db(settings: Settings) -> Iterator[Session]:
    """A session for arranging state and asserting directly against the data."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session")
def app(settings: Settings) -> FastAPI:
    """A single application instance shared across the suite."""
    return create_app(settings)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    """TestClient that runs the lifespan hooks, as a real server would."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def raw_client(app: FastAPI) -> Iterator[TestClient]:
    """TestClient that converts server-side exceptions into 500 responses.

    ``TestClient`` re-raises unhandled exceptions by default, which hides the
    response a real server would return. Use this to assert on 500 bodies.
    """
    with TestClient(app, raise_server_exceptions=False) as test_client:
        yield test_client


@pytest.fixture
def api_prefix(settings: Settings) -> str:
    """The configured ``/api/v1`` prefix, for building request URLs."""
    return settings.API_V1_PREFIX


# ---------------------------------------------------------------------------
# User and auth helpers
# ---------------------------------------------------------------------------
#: Default registration payload used across the auth tests.
CITIZEN_PAYLOAD: dict[str, str] = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "password": "correct-horse-battery",
    "phone": "+1 555 0142",
}

#: Shared password for directly-seeded users.
SEED_PASSWORD = "seeded-user-password"


@pytest.fixture
def citizen_payload() -> dict[str, str]:
    """A fresh copy of the default registration body."""
    return dict(CITIZEN_PAYLOAD)


@pytest.fixture
def make_user(db: Session):
    """Factory that inserts a user directly, bypassing the HTTP layer.

    Needed to create admins and workers: no endpoint grants those roles to a
    self-registering caller, which is the behaviour under test.
    """

    def _make(
        *,
        email: str,
        role: UserRole | str = UserRole.CITIZEN,
        full_name: str = "Test User",
        password: str = SEED_PASSWORD,
        is_active: bool = True,
        is_verified: bool = False,
        department_id: int | None = None,
    ) -> User:
        user = User(
            full_name=full_name,
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=UserRole(role),
            is_active=is_active,
            is_verified=is_verified,
            department_id=department_id,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make


@pytest.fixture
def make_department(db: Session):
    """Factory that inserts a department directly."""

    def _make(
        *,
        name: str = "Roads & Pavements",
        description: str | None = None,
        default_sla_hours: int = 72,
        is_active: bool = True,
    ) -> Department:
        department = Department(
            name=name,
            description=description,
            default_sla_hours=default_sla_hours,
            is_active=is_active,
        )
        db.add(department)
        db.commit()
        db.refresh(department)
        return department

    return _make


@pytest.fixture
def login(client: TestClient, api_prefix: str):
    """Return a bearer-token header factory for an existing account."""

    def _login(email: str, password: str = SEED_PASSWORD) -> dict[str, str]:
        response = client.post(
            f"{api_prefix}/auth/login", json={"email": email, "password": password}
        )
        assert response.status_code == 200, response.text
        return {"Authorization": f"Bearer {response.json()['access_token']}"}

    return _login


@pytest.fixture
def registered_citizen(
    client: TestClient, api_prefix: str, citizen_payload: dict[str, str]
) -> dict[str, object]:
    """Register the default citizen through the API and return the response."""
    response = client.post(f"{api_prefix}/auth/register", json=citizen_payload)
    assert response.status_code == 201, response.text
    return response.json()


@pytest.fixture
def access_token(
    client: TestClient,
    api_prefix: str,
    citizen_payload: dict[str, str],
    registered_citizen: dict[str, object],
) -> str:
    """A valid access token for the registered citizen."""
    response = client.post(
        f"{api_prefix}/auth/login",
        json={
            "email": citizen_payload["email"],
            "password": citizen_payload["password"],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(access_token: str) -> dict[str, str]:
    """Authorization header for the registered citizen."""
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def admin_headers(make_user, login) -> dict[str, str]:
    """Authorization header for an administrator."""
    admin = make_user(email="admin@example.com", role=UserRole.ADMIN, full_name="Admin")
    return login(admin.email)


@pytest.fixture
def worker_headers(make_user, login) -> dict[str, str]:
    """Authorization header for a worker, used for 403 checks."""
    worker = make_user(
        email="worker@example.com", role=UserRole.WORKER, full_name="Worker"
    )
    return login(worker.email)
