"""FastAPI application entry point.

Run locally from the ``backend/`` directory::

    .venv\\Scripts\\python -m uvicorn app.main:app --reload     # Windows
    python -m uvicorn app.main:app --reload                     # macOS / Linux

``main`` is intentionally a thin wiring layer: configuration lives in
``app.core.config``, error rendering in ``app.core.exceptions``, routes in
``app.api.v1``. Business logic belongs in ``app.services``.

Phase 1 scope
-------------
No database is configured, created or required. The application boots with no
``DATABASE_URL`` present. The persistence layer (SQLAlchemy engine, session
factory, models, Alembic) is introduced in Phase 2 and will be wired into the
``lifespan`` hook below.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, status
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger
from app.core.middleware import RequestContextMiddleware
from app.db import registry  # noqa: F401  (registers models on Base.metadata)
from app.db.session import check_database_connection, dispose_engine
from app.schemas.common import ErrorResponse, HealthResponse

logger = get_logger(__name__)

#: API version identifier reported by ``/health`` and the OpenAPI document.
API_VERSION = "1.0.0"

#: Responses added to every operation in the OpenAPI schema, so the documented
#: error shape matches what the handlers in ``app.core.exceptions`` produce.
#: Numeric literals are used deliberately: Starlette renamed the 422 constant
#: (``..._UNPROCESSABLE_ENTITY`` -> ``..._UNPROCESSABLE_CONTENT``), and the
#: status code itself is the stable contract.
COMMON_ERROR_RESPONSES: dict[int | str, dict[str, object]] = {
    422: {
        "model": ErrorResponse,
        "description": "Request validation failed.",
    },
    500: {
        "model": ErrorResponse,
        "description": "Unexpected server error.",
    },
}

DESCRIPTION = """
Backend API for the **Neighborhood Issue Reporter** - residents report local
problems, and municipal staff triage, assign and resolve them.

### Current status: Phase 1

The application skeleton, configuration, error handling and routing are in
place. Domain routes are added in Phase 2, when the MySQL persistence layer is
introduced. `GET /health` is live and can be used to verify a deployment.

### Error format

Every non-2xx response uses a single envelope:

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found.",
    "details": [],
    "request_id": "9f1c2b7a4e6d4f0b8c3a1d2e5f6a7b8c"
  }
}
```

`error.code` is stable and safe to branch on. `request_id` matches the
`X-Request-ID` response header and the server log line for that request.
"""


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup and shutdown hooks.

    The database check is advisory: a failure is logged as a warning and the
    application still starts. That is deliberate - ``/health`` must keep
    answering so an orchestrator can report *why* the service is unhealthy,
    rather than the container dying in a restart loop with the reason buried
    in a crash log.
    """
    settings: Settings = app.state.settings

    logger.info(
        "Starting %s | env=%s | debug=%s | api_prefix=%s | version=%s",
        settings.APP_NAME,
        settings.APP_ENV,
        settings.DEBUG,
        settings.API_V1_PREFIX,
        API_VERSION,
    )
    logger.info(
        "CORS origins: %s%s",
        ", ".join(settings.cors_origins) or "(none)",
        " (credentials disabled: wildcard origin)" if settings.allow_all_origins else "",
    )

    if not settings.database_configured:
        logger.warning(
            "DATABASE_URL still holds the placeholder value. Set it in .env "
            "and run 'alembic upgrade head' before using any data endpoint."
        )
    # Log the masked URL only - never the raw value, which carries a password.
    logger.info("Database target: %s", settings.database_url_safe)
    if check_database_connection():
        logger.info("Database connection verified")
    else:
        logger.warning(
            "Database unreachable at startup. /health stays up; endpoints "
            "that need data will fail until the connection works."
        )

    yield

    dispose_engine()
    logger.info("Shutting down %s", settings.APP_NAME)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure a FastAPI application.

    Exposed as a factory (rather than only a module-level ``app``) so tests can
    construct isolated instances with overridden settings.
    """
    settings = settings or get_settings()
    configure_logging(debug=settings.DEBUG)

    docs_url = "/docs" if settings.docs_enabled else None
    redoc_url = "/redoc" if settings.docs_enabled else None
    openapi_url = "/openapi.json" if settings.docs_enabled else None

    app = FastAPI(
        title=settings.APP_NAME,
        description=DESCRIPTION,
        version=API_VERSION,
        debug=settings.DEBUG,
        docs_url=docs_url,
        redoc_url=redoc_url,
        openapi_url=openapi_url,
        lifespan=lifespan,
        responses=COMMON_ERROR_RESPONSES,
        swagger_ui_parameters={"persistAuthorization": True},
        contact={"name": "Neighborhood Issue Reporter team"},
        license_info={"name": "MIT"},
    )

    # Make settings reachable from request handlers via ``request.app.state``.
    app.state.settings = settings

    _configure_middleware(app, settings)
    register_exception_handlers(app)
    _register_routes(app, settings)

    return app


def _configure_middleware(app: FastAPI, settings: Settings) -> None:
    """Install middleware.

    Starlette runs middleware in reverse registration order, so the
    correlation-ID middleware is added last to make it the outermost layer:
    every log line, including those from CORS handling, then carries a request
    ID.
    """
    allow_all = settings.allow_all_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        # A wildcard origin and credentialed requests are mutually exclusive
        # per the CORS spec; browsers reject the combination outright.
        allow_credentials=not allow_all,
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept", "X-Request-ID"],
        expose_headers=["X-Request-ID", "X-Response-Time-ms"],
        max_age=600,
    )
    app.add_middleware(RequestContextMiddleware, log_requests=True)


def _register_routes(app: FastAPI, settings: Settings) -> None:
    """Mount the health probe, the root index and the versioned API router."""

    @app.get(
        "/health",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        tags=["System"],
        summary="Health check",
        description=(
            "Liveness probe for load balancers and uptime monitoring. Reports "
            "only the application name, environment and version - never "
            "secrets, connection strings or credentials."
        ),
    )
    async def health() -> HealthResponse:
        return HealthResponse(
            app_name=settings.APP_NAME,
            environment=settings.APP_ENV,
            version=API_VERSION,
        )

    @app.get(
        "/",
        tags=["System"],
        summary="API index",
        description="Service discovery: where to find the docs and the API root.",
    )
    async def root() -> dict[str, str | None]:
        return {
            "name": settings.APP_NAME,
            "version": API_VERSION,
            "environment": settings.APP_ENV,
            "api_v1": settings.API_V1_PREFIX,
            "health": "/health",
            "docs": app.docs_url,
            "openapi": app.openapi_url,
        }

    # The single mount point for v1. Domain routers attach to ``api_router``
    # inside app/api/v1/router.py, never here, so the prefix applies once.
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)


#: ASGI application used by uvicorn: ``uvicorn app.main:app``.
app = create_app()
