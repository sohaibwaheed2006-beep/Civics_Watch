# Neighborhood Issue Reporter — Fullstack Overview

This repository contains both the **FastAPI Backend Service** and the **React + Vite Frontend Web Application**.

---

# Backend API (FastAPI)

FastAPI backend for a civic issue-reporting service: residents report local
problems, and municipal staff triage, assign and resolve them.

**Status: Phase 2 complete — authentication working, still no database.**

- **Phase 1** — runnable application, configuration, error handling, logging,
  routing structure.
- **Phase 2** — registration, login, JWT access tokens, profile management and
  password change, backed by **temporary in-memory storage**.

Users currently live in a Python dictionary and passwords are stored in plain
text. Both are deliberate development shortcuts — see
[Temporary Phase 2 limitations](#temporary-phase-2-limitations) before using
this anywhere real. MySQL persistence, Alembic migrations and the
user/department admin endpoints arrive in Phase 3.

---

## Requirements

| Tool   | Version                                      |
| ------ | -------------------------------------------- |
| Python | 3.12+ (verified on 3.13.0)                   |
| OS     | Windows, macOS or Linux                      |

No database server is needed yet.

---

## Setup

All commands run from the `backend/` directory.

### 1. Create and activate a virtual environment

**Windows (PowerShell)**

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If activation is blocked by execution policy, either run
`Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` for the current
session, or skip activation and call the interpreter directly:
`.\.venv\Scripts\python.exe -m ...`

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Create the environment file

```powershell
Copy-Item .env.example .env     # Windows
# cp .env.example .env          # macOS / Linux
```

`.env` is git-ignored. The defaults in `.env.example` are sufficient for local
development. Generate a real `SECRET_KEY` before deploying anywhere:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(64))"
```

### 4. Run the server

```powershell
python -m uvicorn app.main:app --reload
```

| Resource       | URL                            |
| -------------- | ------------------------------ |
| API root       | http://127.0.0.1:8000/         |
| Health check   | http://127.0.0.1:8000/health   |
| Swagger UI     | http://127.0.0.1:8000/docs     |
| ReDoc          | http://127.0.0.1:8000/redoc    |
| OpenAPI schema | http://127.0.0.1:8000/openapi.json |

Pick a different port with `--port 8080`.

### 5. Run the tests

```powershell
python -m pytest
```

Run a subset:

```powershell
python -m pytest app/tests/test_auth.py   # authentication flow
python -m pytest -m smoke                 # app boots and serves traffic
python -m pytest -m contract              # shared interfaces both developers rely on
python -m pytest -m phase1                # "no database yet" restrictions
```

The user store is a process-wide singleton, so an autouse fixture in
`conftest.py` empties it around every test. Without that, a user registered in
one test would leak into the next and make results depend on ordering.

---

## Project layout

```
backend/
├── app/
│   ├── main.py                    # app factory, CORS, /health, router mount
│   ├── core/
│   │   ├── config.py              # pydantic-settings Settings + get_settings()
│   │   ├── exceptions.py          # AppError hierarchy + error handlers
│   │   ├── logging.py             # logging config, request IDs, redaction
│   │   ├── middleware.py          # RequestContextMiddleware (pure ASGI)
│   │   └── security.py            # JWT create/decode, password comparison
│   ├── api/
│   │   ├── deps.py                # get_current_user, require_roles, pagination
│   │   └── v1/
│   │       ├── router.py          # mounts every domain router; owns prefixes
│   │       └── endpoints/
│   │           ├── auth.py        # the six auth routes
│   │           ├── users.py       # router defined, routes land in Phase 3
│   │           └── departments.py # router defined, routes land in Phase 3
│   ├── schemas/
│   │   ├── common.py              # APIModel, ErrorResponse, Page[T], health
│   │   ├── auth.py                # register/login/token/change-password
│   │   └── user.py                # UserRole, UserRead, UserProfileUpdate
│   ├── services/
│   │   └── auth_service.py        # registration, login, profile, password
│   ├── repositories/
│   │   └── user_repository.py     # TEMPORARY in-memory user store
│   └── tests/
│       ├── conftest.py
│       ├── test_auth.py
│       ├── test_config.py
│       ├── test_errors.py
│       ├── test_health.py
│       ├── test_middleware.py
│       ├── test_openapi.py
│       ├── test_phase1_no_database.py
│       └── test_routing.py
├── uploads/                       # upload target (contents git-ignored)
├── .env.example
├── .gitignore
├── pytest.ini
├── requirements.txt
└── README.md
```

### Layer boundaries

| Layer          | Responsibility                                          |
| -------------- | ------------------------------------------------------- |
| `api/`         | HTTP only: validate, delegate, serialise                |
| `services/`    | Business rules; raises `AppError`, never touches HTTP    |
| `repositories/`| Storage access; never commits                            |
| `schemas/`     | Request/response validation                             |
| `core/`        | Cross-cutting concerns; imports nothing from `api`/`services` |

`main.py` stays a wiring layer — no business logic belongs there.

A request flows `endpoint → service → repository`. Endpoints never reach into
the repository directly, and `auth_service` imports no FastAPI symbols, so
every rule in it is unit-testable without an HTTP client.

---

## Configuration

Settings are read from the environment first, then `.env`, then the defaults in
`app/core/config.py`. Access them through `get_settings()`, which caches one
validated instance per process.

| Variable                      | Default                             | Notes                                               |
| ----------------------------- | ----------------------------------- | --------------------------------------------------- |
| `APP_NAME`                    | `Neighborhood Issue Reporter API`   | Shown in docs and `/health`                         |
| `APP_ENV`                     | `local`                             | `local`/`development`/`test`/`staging`/`production` |
| `DEBUG`                       | `true`                              | Verbose logging; turn off in production             |
| `API_V1_PREFIX`               | `/api/v1`                           | Must start with `/`, must not end with `/`          |
| `SECRET_KEY`                  | placeholder                         | JWT signing key (Phase 2)                           |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60`                                | Must be positive                                    |
| `CORS_ORIGINS`                | `*`                                 | CSV or JSON array                                   |
| `UPLOAD_DIR`                  | `uploads`                           | Relative paths resolve against `backend/`           |
| `MAX_UPLOAD_SIZE_MB`          | `5`                                 | Must be positive                                    |

Validation is enforced at startup, so a bad value fails fast with a clear
message rather than surfacing later as a confusing runtime error.

Two safety behaviours worth knowing:

- **Production secret guard.** Starting with `APP_ENV=production` while
  `SECRET_KEY` still holds the `.env.example` placeholder raises immediately.
- **Docs in production.** `/docs`, `/redoc` and `/openapi.json` return 404 when
  `APP_ENV=production` and `DEBUG=false`. `/health` stays available.

### CORS

`CORS_ORIGINS` accepts either form:

```ini
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
CORS_ORIGINS=["http://localhost:3000","http://localhost:5173"]
```

A wildcard (`*`) automatically disables `allow_credentials`, because browsers
reject that combination per the CORS spec. Use an explicit origin list as soon
as the frontend needs cookies or an `Authorization` header with credentials.

---

## API conventions

### Error format

Every non-2xx response uses one envelope, produced by
`app/core/exceptions.py`:

```json
{
  "error": {
    "code": "not_found",
    "message": "Resource not found.",
    "details": [],
    "request_id": "67453dcf7be7454d942a581e32a8e31c"
  }
}
```

- `code` is stable and machine-readable — branch on it, not on `message`.
- `details` carries per-field problems for validation failures, with `field`
  as a dotted path such as `body.email`.
- `request_id` matches the `X-Request-ID` response header and the server log
  line for that request.

Raise the typed exceptions from services rather than building responses:

| Exception                  | Status | `code`             |
| -------------------------- | ------ | ------------------ |
| `BadRequestError`          | 400    | `bad_request`      |
| `AuthenticationError`      | 401    | `unauthorized`     |
| `PermissionDeniedError`    | 403    | `forbidden`        |
| `NotFoundError`            | 404    | `not_found`        |
| `ConflictError`            | 409    | `conflict`         |
| `UnprocessableEntityError` | 422    | `validation_error` |
| `InternalServerError`      | 500    | `internal_error`   |

Unhandled exceptions are logged with a full traceback server-side and returned
to the client as an opaque 500 — stack traces and exception text never reach
the response body.

### Pagination

List endpoints take `page`, `page_size` (max 100), `sort_by` and `sort_order`
through the `PaginationDep` dependency, and return a `Page[T]` envelope:

```json
{
  "items": [],
  "meta": {
    "page": 1,
    "page_size": 20,
    "total_items": 0,
    "total_pages": 0,
    "has_next": false,
    "has_previous": false
  }
}
```

Endpoints must validate `sort_by` against their own allow-list and append a
primary-key tie-breaker, so repeated requests for the same page return the same
rows.

### Request correlation

`RequestContextMiddleware` assigns every request an ID, reusing a sane inbound
`X-Request-ID` so a trace started by a gateway or the frontend carries through.
It is available as `request.state.request_id`, appears in every log line, and
is returned in both the `X-Request-ID` header and `error.request_id`.

Responses also carry `X-Response-Time-ms`.

### Logging

Logs go to stdout as
`timestamp | level | logger | [request_id] | message`.

A redaction filter masks anything resembling a password, bearer token, API key
or connection-string credential. It is a safety net — never pass secrets to a
logger in the first place.

---

## Routing and prefixes

The `/api/v1` segment is applied exactly once, and the version lives in
configuration:

```
settings.API_V1_PREFIX  +  "/auth"   +  "/login"   =  /api/v1/auth/login
   (app/main.py)        (v1/router.py)  (endpoint module)
```

Rules that keep this working:

1. Endpoint modules expose a bare `router = APIRouter()` with **no** prefix.
2. `app/api/v1/router.py` assigns every prefix and tag when mounting.
3. `app/main.py` mounts the aggregate router once, with
   `prefix=settings.API_V1_PREFIX`.

`app/tests/test_routing.py` enforces all three, so a duplicated prefix fails
the suite rather than reaching production.

Phase 1 registers no domain routes, so `/docs` currently lists only `/health`
and `/`. That is deliberate: the OpenAPI document describes what actually
works, with no placeholder endpoints.

---

## Endpoints

### System

| Method | Path      | Auth | Description                                     |
| ------ | --------- | ---- | ----------------------------------------------- |
| `GET`  | `/health` | none | Liveness probe. Returns status, app name, environment, version and a UTC timestamp. Exposes no configuration or credentials. |
| `GET`  | `/`       | none | Service index: links to the docs and the API root. |

### Authentication — `/api/v1/auth`

| Method  | Path                            | Auth   | Success | Description                          |
| ------- | ------------------------------- | ------ | ------- | ------------------------------------ |
| `POST`  | `/api/v1/auth/register`         | none   | `201`   | Create a citizen account             |
| `POST`  | `/api/v1/auth/login`            | none   | `200`   | Exchange credentials for a token     |
| `GET`   | `/api/v1/auth/me`               | bearer | `200`   | Current user's profile               |
| `PATCH` | `/api/v1/auth/me`               | bearer | `200`   | Update own `full_name` / `phone`     |
| `POST`  | `/api/v1/auth/change-password`  | bearer | `200`   | Change password, current one required |
| `POST`  | `/api/v1/auth/logout`           | bearer | `200`   | Acknowledge logout (client discards token) |

Roles are exactly `citizen`, `admin` and `worker`. **Public registration always
creates a `citizen`** — the role is set server-side and cannot be supplied by
the caller.

### Example flow

**Register**

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "full_name": "Ada Lovelace",
  "email": "ada@example.com",
  "password": "correct-horse-battery",
  "phone": "+1 555 0142"
}
```

```json
{
  "id": 1,
  "full_name": "Ada Lovelace",
  "email": "ada@example.com",
  "role": "citizen",
  "phone": "+1 555 0142",
  "is_active": true,
  "is_verified": false,
  "department_id": null,
  "created_at": "2026-10-10T08:24:07.796449Z",
  "updated_at": "2026-10-10T08:24:07.796449Z"
}
```

**Log in**

```http
POST /api/v1/auth/login
{ "email": "ada@example.com", "password": "correct-horse-battery" }
```

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

**Authenticated request**

```http
GET /api/v1/auth/me
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

In Swagger UI, click **Authorize** and paste the `access_token` value.

### Status codes

| Code  | When                                                              |
| ----- | ----------------------------------------------------------------- |
| `201` | Registration succeeded                                            |
| `400` | Wrong `current_password` on change-password                       |
| `401` | Bad credentials; missing, malformed or expired token; inactive account |
| `409` | Email already registered                                          |
| `422` | Validation failed, or the body contained a field you may not set   |

A wrong current password returns **400, not 401**: the request itself was
properly authenticated, and a 401 would make most clients discard a valid
session.

### Access tokens

`POST /auth/login` returns a JWT signed with `SECRET_KEY` (HS256) carrying:

| Claim  | Value                                            |
| ------ | ------------------------------------------------ |
| `sub`  | User ID, as a string                             |
| `iat`  | Issued-at                                        |
| `exp`  | Expiry, from `ACCESS_TOKEN_EXPIRE_MINUTES`       |
| `type` | `"access"` — checked on every decode             |

A token is rejected when the signature is wrong, it has expired, `type` is not
`access`, or `sub` is not numeric.

**Permissions are never read from the token.** After validating the signature,
the user is re-read from storage, so deactivating an account takes effect on
the very next request even though its token is still cryptographically valid.

### Logout and token revocation

`POST /auth/logout` returns a confirmation message. **The client must delete
its stored token.**

JWTs are stateless and self-contained — the server holds no session to
destroy, so this endpoint *cannot* revoke a token. A token that was issued
before logout stays valid until its `exp` passes. The test
`test_token_still_works_after_logout` documents this deliberately.

Real server-side revocation needs one of:

- a denylist of revoked token IDs, checked on every request, or
- short-lived access tokens paired with revocable refresh tokens.

Neither is in scope for this phase.

### Security behaviour worth knowing

- **No account enumeration.** An unknown email, a wrong password and a
  deactivated account all return the same 401 message.
- **No privilege escalation through the API.** Request schemas set
  `extra="forbid"`, so sending `role`, `is_active`, `is_verified`,
  `department_id` or `email` to `/register` or `PATCH /me` is a 422. The
  rejection happens during validation, before any handler runs, so no partial
  update is applied.
- **Passwords never appear in responses.** `UserRead` has no password field at
  all, so one cannot leak even from a record that carries it.
- **Nothing sensitive reaches the logs.** Failures are logged by user ID, never
  by email, password or token, and a redaction filter is the backstop.
- **Timing-safe comparison.** Password checks use `secrets.compare_digest`.

---

## Temporary Phase 2 limitations

These are known, deliberate shortcuts. Read before deploying anything.

### 1. In-memory storage — data is lost on restart

Users live in a module-level dictionary in
`app/repositories/user_repository.py`.

- **Everything disappears when the process stops.** There is no persistence.
- **Multiple workers do not share state.** Running
  `uvicorn --workers 2` gives each worker its own disconnected store, so a
  user registered through one worker cannot log in through another. Stay on a
  single worker until Phase 3.
- IDs are assigned from a counter that resets with the process.

Writes are guarded by a lock, and `create` performs its uniqueness check and
insert atomically, so concurrent registrations cannot both claim one email.

### 2. Passwords are stored in plain text

`hash_password` in `app/core/security.py` currently returns the password
unchanged, and `verify_password` compares plain text.

**This is not acceptable for any deployment.** It is a development
convenience for this phase only.

Those two functions are the single swap point — `argon2-cffi` is already
installed, so the upgrade is:

```python
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return _hasher.hash(password)

def verify_password(plain_password: str, stored_password: str) -> bool:
    try:
        return _hasher.verify(stored_password, plain_password)
    except VerifyMismatchError:
        return False
```

No other module needs to change. The test
`test_phase2_stores_the_password_as_plain_text` pins the current behaviour and
will fail when hashing lands, which is the intended prompt to update it.

### 3. Not implemented

Refresh tokens, token revocation, email verification, password reset, rate
limiting on login, and the user/department admin endpoints.

---

## Phase restrictions still enforced by tests

`app/tests/test_phase1_no_database.py` fails the build if persistence code
appears before Phase 3. It asserts that:

- no application module imports `sqlalchemy`, `alembic`, `pymysql`, `psycopg`
  or `asyncpg`;
- no `create_engine`, `sessionmaker`, `declarative_base` or
  `metadata.create_all` call exists;
- `app/db/`, `app/models/`, `app/migrations/` and `alembic.ini` do not exist;
- `Settings` defines no `DATABASE_URL`;
- the app boots and serves `/health` with `DATABASE_URL` absent;
- `requirements.txt` installs no database driver.

Delete or invert these when Phase 3 begins.

---

## Roadmap

### Phase 3 — MySQL persistence and administration

- `app/db/base.py` — one shared declarative `Base`
- `app/db/session.py` — one engine, one session factory, `get_db` dependency
- `app/models/` — `User` and `Department`
- Alembic migration `0001_core`
- Argon2 password hashing (replacing the plaintext shortcut)
- Routes on the `users` and `departments` routers

Planned additions to `requirements.txt`: `SQLAlchemy>=2.0`, `alembic`,
`PyMySQL`, `cryptography`.

### Stable interfaces for the report-domain developer

These names are fixed and safe to import now:

| Import                                            | Purpose                        |
| ------------------------------------------------- | ------------------------------ |
| `from app.api.deps import get_current_user`       | Current authenticated user     |
| `from app.api.deps import require_roles`          | Role-based access factory      |
| `from app.api.deps import require_admin`          | Admin-only shorthand           |
| `from app.api.deps import require_staff`          | Admin **or** worker            |
| `from app.core.config import get_settings`        | Configuration                  |
| `from app.schemas.user import UserRole`           | `citizen` / `admin` / `worker` |
| `from app.schemas.common import Page, ErrorResponse` | Response envelopes          |
| `from app.core.exceptions import NotFoundError, ConflictError, ...` | Typed failures |

Usage:

```python
from typing import Annotated
from fastapi import Depends
from app.api.deps import CurrentUser, require_admin
from app.repositories.user_repository import UserRecord

@router.get("/reports")
def list_reports(current_user: CurrentUser): ...

@router.delete("/reports/{report_id}")
def delete_report(admin: Annotated[UserRecord, Depends(require_admin)]): ...
```

Phase 3 adds `get_db` alongside these without changing any of them.

Mount new routers in `app/api/v1/router.py` only, passing the prefix and tags
there. Never add a second `/api/v1`.

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'app'`**
Run from the `backend/` directory, not the repository root. `pytest.ini` sets
`pythonpath = .` for tests; uvicorn resolves `app.main:app` from the working
directory.

**`Activate.ps1 cannot be loaded because running scripts is disabled`**
Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`, or call
`.\.venv\Scripts\python.exe` directly without activating.

**`/docs` returns 404**
Expected when `APP_ENV=production` and `DEBUG=false`. Set `APP_ENV=local` for
development.

**Startup fails with "SECRET_KEY still holds the placeholder value"**
`APP_ENV=production` requires a real secret. Generate one with
`python -c "import secrets; print(secrets.token_urlsafe(64))"`.

**Port already in use**
Pass `--port 8080` to uvicorn.

**My registered user disappeared**
Expected. Storage is in-memory and resets with the process — including on every
`--reload` restart. Register again, or wait for Phase 3.

**Login works, then randomly returns 401**
You are probably running more than one worker. Each has its own isolated user
store. Run a single worker until Phase 3.

**`401` with a token that looks fine**
Check the header format: `Authorization: Bearer <token>`, with a single space
and no quotes. Also confirm the token is under an hour old
(`ACCESS_TOKEN_EXPIRE_MINUTES`), and that `SECRET_KEY` has not changed since it
---

# Frontend Web Application (React + Vite)

A modern, production-minded civic technology web application built with **React**, **Vite**, **TypeScript (Strict Mode)**, and **Tailwind CSS**. 

The platform enables **Citizens** to report and track neighborhood infrastructure hazards, empowers **Municipal Administrators** to triage, dispatch, and analyze issues with SLA tracking, and equips **Field Workers** with mobile-optimized work orders, directions, and on-site resolution workflows.

---

## 🌟 Key Features

### 👤 Citizen Portal
- **Dashboard:** Welcome overview with report statistics derived from live records, quick action buttons, and recent community updates.
- **Multi-Section Report Creation:**
  - Standardized problem categorization (Road Damage, Streetlights, Garbage/Waste, Water Leaks, Drainage, Public Property, etc.).
  - Interactive Leaflet map location picker (click-to-drop pin, draggable marker, browser GPS "Use My Current Location").
  - Photo evidence upload with client-side file validation (JPG/PNG/WebP, max 5MB, up to 5 photos) and image preview gallery.
  - Proactive duplicate detection warnings.
- **Report Tracking & Governance:** Real-time lifecycle timeline, upvoting mechanism, citizen withdrawal controls, and full photo lightbox preview.
- **Community Issue Map:** Interactive full-page map with status/priority filtering and location popups.

### 🏛️ Administrator Operations
- **Operations & Governance Dashboard:** Real-time KPI summary (Total, Open, In Progress, Resolved, Overdue SLA) with **Recharts** visualizations (Donut status breakdown, Category bar chart, Velocity trends).
- **Report Management Console:** Multi-parameter search, status, category, priority, and department filters with pagination and column sorting.
- **Triage & Worker Dispatch:** Assign field workers filtered by active department, adjust priority levels, set SLA deadlines, and transition states through permitted lifecycle rules.
- **Department & SLA Management:** Create, edit, and safely deactivate departments with custom response SLA targets (hours).
- **User Directory & RBAC:** View citizen and staff accounts, provision new field worker accounts, update department assignments, and safely manage administrative accounts.
- **SLA & Analytics Intelligence:** Detailed department compliance percentage tracking, average resolution hours, and workload monitoring.

### 👷 Field Worker Interface
- **Mobile-Optimized Interface:** High-contrast, large touch-target work order management designed for smartphones and tablets in the field.
- **Turn-by-Turn Navigation:** One-tap integration to launch Google Maps driving navigation directly to exact incident GPS coordinates.
- **Workflow State Actions:** "Start Work Order" (`in_progress`) and "Complete Work Order" (`resolved`) with required resolution notes and optional evidence photo URLs.
- **Field Navigation Map:** Spatial display of active dispatches on OpenStreetMap tiles.

---

## 🛠️ Mandatory Technology Stack

- **Core Framework:** React 18 & TypeScript (with `strict: true`)
- **Build Tool:** Vite 6
- **Styling:** Tailwind CSS (Custom civic palette: Slate-50 background, Teal/Navy accents, accessible focus indicators)
- **Routing:** React Router 6 (with role-based route guards and smart dashboard redirection)
- **Data Fetching & Cache:** TanStack Query v5 (React Query)
- **Forms & Validation:** React Hook Form & Zod schemas
- **Interactive Maps:** Leaflet & React Leaflet
- **Data Visualizations:** Recharts
- **Icons:** Lucide React
- **Notifications:** Accessible custom floating toast system & unread badge dropdown
- **Testing:** Vitest & React Testing Library (`@testing-library/react`, `jsdom`, `@testing-library/jest-dom`)

---

## 🚀 Quick Start Guide

### Prerequisites
- **Node.js:** v18.0.0 or newer (Tested on Node.js v25)
- **Package Manager:** `npm` (v9 or newer)

### 1. Installation
Clone the repository and install all dependencies:
```bash
npm install
```

### 2. Environment Configuration
Copy the example environment configuration:
```bash
cp .env.example .env
```

Default configuration variables in `.env`:
```env
# FastAPI Backend API endpoint
VITE_API_BASE_URL=http://localhost:8000/api/v1

# Application Branding
VITE_APP_NAME=Neighborhood Issue Reporter

# Default Map Center (Leaflet / OpenStreetMap)
VITE_MAP_DEFAULT_LAT=40.7128
VITE_MAP_DEFAULT_LNG=-74.0060
VITE_MAP_DEFAULT_ZOOM=13

# Fallback adapter when backend is unreachable or in preview/mock mode
VITE_ENABLE_MOCK_FALLBACK=true
```

### 3. Start Development Server
```bash
npm run dev
```
Open your browser at `http://localhost:5173`.

---

## 🔑 Demo Personas & Quick Login

When evaluating the application without entering credentials, use the 1-Click **"Demo Quick-Fill Personas"** buttons on the `/login` screen:

| Persona | Role | Email | Password | Landing Page |
| :--- | :--- | :--- | :--- | :--- |
| **Sarah Jenkins** | Citizen | `citizen@example.com` | `password123` | `/citizen/dashboard` |
| **Marcus Vance** | Administrator | `admin@example.com` | `password123` | `/admin/dashboard` |
| **Dave Miller** | Field Worker | `worker@example.com` | `password123` | `/worker/dashboard` |

---

## 🧪 Testing and Quality Assurance

Run the test suite via Vitest:
```bash
npm test
```

Run test suite in interactive watch mode:
```bash
npm run test:watch
```

Run strict TypeScript type checks:
```bash
npm run typecheck
```

Build production bundle:
```bash
npm run build
```

Preview production build locally:
```bash
npm run preview
```

---

## 🗺️ Project Structure

```text
├── src/
│   ├── app/
│   │   ├── App.tsx             # Root application component
│   │   ├── router.tsx          # Route definitions & RBAC guards
│   │   └── providers.tsx       # QueryClient, Auth, & Toast providers
│   ├── components/
│   │   ├── data-display/       # Status badges, priority badges, timelines, pagination
│   │   ├── layout/             # Header, sidebar, mobile navigation, app & public layouts
│   │   ├── maps/               # Interactive Leaflet location picker & issue map
│   │   ├── reports/            # ReportCard, ReportFilters, view toggles
│   │   └── ui/                 # Accessible button, input, select, textarea, modal, toast
│   ├── features/
│   │   ├── admin/              # Dashboard, reports triage, departments, users, analytics
│   │   ├── auth/               # Login, register, forgot-password, unauthorized
│   │   ├── citizen/            # Citizen dashboard, report creation, my reports, issue map
│   │   ├── notifications/      # Notifications inbox with unread filters
│   │   └── worker/             # Field dashboard, assignments, navigation, resolution notes
│   ├── hooks/
│   │   ├── use-auth.tsx        # Authentication context & session hook
│   │   ├── use-debounce.ts     # Search debouncing hook
│   │   └── use-toast.tsx       # Toast notifications hook & context
│   ├── lib/
│   │   ├── api-client.ts       # Axios client with auth interceptors & storage
│   │   ├── api-errors.ts       # FastAPI 422/400/401/403/500 error parser
│   │   ├── constants.ts        # Problem categories, status styling, map defaults
│   │   ├── formatters.ts       # Date, coordinate, category, and status formatters
│   │   ├── mock-adapter.ts     # Resilient typed mock adapter with localStorage persistence
│   │   ├── mock-data.ts        # Realistic initial civic dataset
│   │   └── permissions.ts      # Role-based action permissions matrix
│   ├── schemas/                # Zod validation schemas for auth, reports, departments, users
│   ├── services/               # Typed services (auth, reports, departments, users, notifications)
│   ├── test/                   # Vitest tests (auth, reports, utils, components)
│   └── types/                  # TypeScript interface declarations
├── docs/                       # Project documentation
│   ├── API_INTEGRATION_NOTES.md    # Detailed API contract documentation
│   ├── DEVELOPER_2_INTEGRATION.md  # Report-domain integration notes
│   └── DEVELOPER_2_DEPENDENCIES.md # Dependency map for Developer 2
├── tools/
│   └── share/                  # Cloudflare tunnel launcher for sharing dev builds
│       ├── start-share.bat
│       └── cloudflared.exe     # (gitignored binary, downloaded locally)
├── package.json
├── tailwind.config.js
├── tsconfig.json
└── vite.config.ts
```

---

## 🔧 Backend Integration & Troubleshooting

### CORS Configuration
Ensure your FastAPI backend has `CORSMiddleware` configured to permit requests from the Vite frontend origin (`http://localhost:5173` or `http://127.0.0.1:5173`):
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### Offline / Fallback Mode
If the FastAPI backend is not currently running, the frontend automatically falls back to `MockBackendAdapter` when `VITE_ENABLE_MOCK_FALLBACK=true`. All state updates (e.g. creating reports, assigning workers, marking resolutions) persist to browser `localStorage` and survive page refreshes.

---

## 📄 License
MIT License &copy; 2026 Neighborhood Issue Reporter Civic Technology Initiative.
