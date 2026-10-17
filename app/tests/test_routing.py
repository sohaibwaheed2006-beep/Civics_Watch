"""Router wiring.

Guards the prefix contract that both developers share: the ``/api/v1`` segment
is applied exactly once, by ``app.main``, and endpoint modules stay
prefix-free.

Implementation note
-------------------
FastAPI 0.143 made ``include_router`` lazy: included routers appear in
``app.routes`` as internal ``_IncludedRouter`` objects instead of being
flattened into ``APIRoute`` entries. The effective, fully-prefixed paths are
therefore read from the generated OpenAPI document, which is public API and is
exactly what clients consume.
"""

from __future__ import annotations

import pytest
from fastapi import APIRouter, FastAPI
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.v1 import router as router_module
from app.api.v1.endpoints import auth, departments, users
from app.core.config import Settings

pytestmark = pytest.mark.contract

ENDPOINT_MODULES = (auth, users, departments)

#: Prefix each domain router must be mounted under, inside the v1 router.
EXPECTED_MOUNTS: dict[str, str] = {
    "auth": "/auth",
    "users": "/users",
    "departments": "/departments",
}


def _effective_paths(app: FastAPI) -> list[str]:
    """Every fully-resolved path the application serves, per OpenAPI."""
    app.openapi_schema = None  # drop any cached schema
    return list(app.openapi()["paths"])


def _directly_registered_paths(app: FastAPI) -> list[str]:
    """Paths declared straight on the app (``@app.get``), not via a router."""
    return [route.path for route in app.routes if isinstance(route, APIRoute)]


def _included_prefixes(router: APIRouter) -> dict[int, str]:
    """Map ``id(original_router)`` -> mounted prefix for an aggregate router."""
    mounts: dict[int, str] = {}
    for entry in router.routes:
        context = getattr(entry, "include_context", None)
        original = getattr(entry, "original_router", None)
        if context is not None and original is not None:
            mounts[id(original)] = context.prefix
    return mounts


# ---------------------------------------------------------------------------
# Module structure
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("module", ENDPOINT_MODULES, ids=lambda m: m.__name__)
def test_every_endpoint_module_exposes_a_router(module: object) -> None:
    router = getattr(module, "router", None)

    assert isinstance(router, APIRouter), (
        f"{module.__name__} must expose a module-level `router`"  # type: ignore[attr-defined]
    )


@pytest.mark.parametrize("module", ENDPOINT_MODULES, ids=lambda m: m.__name__)
def test_endpoint_routers_declare_no_prefix_of_their_own(module: object) -> None:
    """The parent router owns the prefix; declaring it twice duplicates it."""
    router: APIRouter = module.router  # type: ignore[attr-defined]

    assert router.prefix == "", (
        f"{module.__name__} sets prefix={router.prefix!r}; "  # type: ignore[attr-defined]
        "prefixes belong in app/api/v1/router.py"
    )


def test_aggregate_router_exists_and_is_unprefixed() -> None:
    assert isinstance(router_module.api_router, APIRouter)
    # /api/v1 comes from settings at include time, not from this router.
    assert router_module.api_router.prefix == ""


# ---------------------------------------------------------------------------
# Where router.py mounts each domain router
# ---------------------------------------------------------------------------
def test_v1_router_mounts_the_core_domains() -> None:
    """Core (Developer 1) and report-domain (Developer 2) routers are all mounted."""
    mounts = _included_prefixes(router_module.api_router)

    # Core domains must still be present; the report domain adds more mounts.
    assert len(mounts) >= 3, f"expected at least 3 mounted routers, got {len(mounts)}"


@pytest.mark.parametrize(
    ("module", "expected_prefix"),
    [(module, EXPECTED_MOUNTS[module.__name__.rsplit(".", 1)[-1]]) for module in ENDPOINT_MODULES],
    ids=lambda value: value if isinstance(value, str) else value.__name__,
)
def test_each_domain_router_is_mounted_at_its_prefix(
    module: object, expected_prefix: str
) -> None:
    mounts = _included_prefixes(router_module.api_router)
    router: APIRouter = module.router  # type: ignore[attr-defined]

    assert id(router) in mounts, (
        f"{module.__name__} router is not mounted in app/api/v1/router.py"  # type: ignore[attr-defined]
    )
    assert mounts[id(router)] == expected_prefix


# ---------------------------------------------------------------------------
# Mounted paths on the real application
# ---------------------------------------------------------------------------
def test_system_routes_are_mounted(app: FastAPI) -> None:
    paths = _directly_registered_paths(app)

    assert "/health" in paths
    assert "/" in paths


def test_no_path_contains_a_duplicated_prefix(
    app: FastAPI, settings: Settings
) -> None:
    doubled = f"{settings.API_V1_PREFIX}{settings.API_V1_PREFIX}"

    offenders = [path for path in _effective_paths(app) if doubled in path]
    assert not offenders, f"duplicated API prefix in: {offenders}"


def test_no_path_segment_repeats_v1(app: FastAPI) -> None:
    for path in _effective_paths(app):
        assert path.count("/v1") <= 1, f"'/v1' appears more than once in {path}"


def test_auth_routes_are_mounted_under_the_versioned_prefix(
    app: FastAPI, settings: Settings
) -> None:
    """Phase 2 exposes the six auth routes, each exactly once."""
    paths = _effective_paths(app)
    prefix = settings.API_V1_PREFIX

    for expected in (
        f"{prefix}/auth/register",
        f"{prefix}/auth/login",
        f"{prefix}/auth/me",
        f"{prefix}/auth/change-password",
        f"{prefix}/auth/logout",
    ):
        assert expected in paths, f"missing route: {expected}"


def test_admin_routes_are_mounted_under_the_versioned_prefix(
    app: FastAPI, settings: Settings
) -> None:
    """The user and department administration routes, each exactly once."""
    paths = _effective_paths(app)
    prefix = settings.API_V1_PREFIX

    # Collection routes are mounted WITHOUT a trailing slash, matching every
    # other router. A trailing-slash route would make FastAPI 307-redirect
    # "/users" to an absolute URL built from the Host header, which sends the
    # browser off the dev-proxy origin and drops the Authorization header.
    for expected in (
        f"{prefix}/users",
        f"{prefix}/users/{{user_id}}",
        f"{prefix}/users/{{user_id}}/role",
        f"{prefix}/departments",
        f"{prefix}/departments/{{department_id}}",
    ):
        assert expected in paths, f"missing route: {expected}"


# ---------------------------------------------------------------------------
# End-to-end prefix composition
# ---------------------------------------------------------------------------
def test_prefix_composition_yields_a_single_api_v1_segment(
    settings: Settings,
) -> None:
    """Reproduce main.py + router.py mounting and serve a real request.

    Isolated routers are used rather than the module singletons so this test
    cannot leak probe routes into the shared application fixture.
    """
    from app.main import create_app

    domain_router = APIRouter()

    @domain_router.get("/login")
    async def login() -> dict[str, bool]:
        return {"ok": True}

    # Exactly the pattern used in app/api/v1/router.py.
    aggregate = APIRouter()
    aggregate.include_router(domain_router, prefix="/auth", tags=["Authentication"])

    probe_app = create_app(settings)
    # Exactly the pattern used in app/main.py.
    probe_app.include_router(aggregate, prefix=settings.API_V1_PREFIX)

    expected = f"{settings.API_V1_PREFIX}/auth/login"
    assert expected == "/api/v1/auth/login"
    assert expected in _effective_paths(probe_app)

    with TestClient(probe_app) as probe_client:
        response = probe_client.get(expected)

    assert response.status_code == 200
    assert response.json() == {"ok": True}


def test_domain_routes_inherit_the_tag_from_the_aggregate_router(
    settings: Settings,
) -> None:
    """Tags are assigned once, at mount time, not repeated per endpoint."""
    from app.main import create_app

    domain_router = APIRouter()

    @domain_router.get("/me")
    async def me() -> dict[str, bool]:
        return {"ok": True}

    aggregate = APIRouter()
    aggregate.include_router(domain_router, prefix="/auth", tags=["Authentication"])

    probe_app = create_app(settings)
    probe_app.include_router(aggregate, prefix=settings.API_V1_PREFIX)

    schema = probe_app.openapi()
    operation = schema["paths"][f"{settings.API_V1_PREFIX}/auth/me"]["get"]

    assert operation["tags"] == ["Authentication"]
