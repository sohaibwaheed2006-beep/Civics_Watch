"""Business logic layer.

Services own the rules; routers own HTTP. A service receives already-validated
input, enforces domain invariants, and raises the
:class:`~app.core.exceptions.AppError` subclasses on failure - it never builds
an HTTP response and never imports FastAPI.

- ``auth_service``       - registration, login, tokens, profile, password
- ``user_service``       - user listing, lookup, role changes, admin guards
- ``department_service`` - department listing, creation, updates

Each takes the request's SQLAlchemy ``Session`` as its first argument and
commits its own unit of work, so transaction boundaries are visible at the
call site.
"""
