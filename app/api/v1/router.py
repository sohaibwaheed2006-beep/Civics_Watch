"""Aggregate router for API version 1.

This module is the single place where domain routers are mounted, and it owns
every prefix and tag. Endpoint modules declare their paths *relative* to the
prefix assigned here (``@router.post("/login")``, not ``"/auth/login"``), which
is what keeps prefixes from being applied twice.

The ``/api/v1`` portion of the path is **not** set here. ``app.main`` includes
this router with ``prefix=settings.API_V1_PREFIX``, so the version lives in
configuration and appears exactly once in the final URL::

    settings.API_V1_PREFIX   +   "/auth"   +   "/login"
         /api/v1                 (here)       (endpoint module)
    = /api/v1/auth/login

Integration note for Developer 2
--------------------------------
Mount the report-domain routers in the block marked below, following the same
pattern: pass the prefix and tags at this level and leave the endpoint modules
prefix-free. Do not call ``app.include_router`` from ``main.py`` directly and
do not add a second ``/api/v1`` prefix anywhere.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1.endpoints import (
    ai,
    analytics,
    assignments,
    auth,
    bonus,
    departments,
    notifications,
    report_photos,
    reports,
    reviews,
    users,
    votes,
)

#: Version-1 aggregate router. Mounted under ``settings.API_V1_PREFIX``.
api_router = APIRouter()

# ---------------------------------------------------------------------------
# Core domain (Developer 1)
# ---------------------------------------------------------------------------
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(
    departments.router, prefix="/departments", tags=["Departments"]
)

# ---------------------------------------------------------------------------
# Report domain (Developer 2)
# ---------------------------------------------------------------------------
# Reports mount first so that /reports/{id}/* paths exist before the photo and
# vote sub-routers attach their nested paths.
api_router.include_router(reports.router, prefix="/reports", tags=["Reports"])
api_router.include_router(
    report_photos.router, prefix="/reports", tags=["Report Photos"]
)
api_router.include_router(votes.router, prefix="/reports", tags=["Votes"])
# Assignments: a mix of /reports/{id}/assign, /assignments/my,
# /departments/{id}/queue - all under the same router so the paths line up.
api_router.include_router(assignments.router)
api_router.include_router(
    notifications.router, prefix="/notifications", tags=["Notifications"]
)
api_router.include_router(
    analytics.router, prefix="/analytics", tags=["Analytics"]
)

# ---------------------------------------------------------------------------
# AI automation (vision auto-fill, resolution check, auto-routing, bonuses)
# ---------------------------------------------------------------------------
# ai.router owns /ai/vision/* and /ai/reports/{id}/{cluster,auto-route}.
api_router.include_router(ai.router, prefix="/ai", tags=["AI Automation"])
# reviews.router hangs off /reports/{id}/review so citizens rate the worker
# that closed their report.
api_router.include_router(reviews.router, prefix="/reports", tags=["Reviews"])
# bonus.router exposes the worker-of-the-month leaderboard and the admin
# award action.
api_router.include_router(bonus.router, prefix="/bonus", tags=["Worker Bonus"])

__all__ = ["api_router"]
