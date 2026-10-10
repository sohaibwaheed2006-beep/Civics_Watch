"""Supabase client integration.

Provides preconfigured Supabase client instances for database operations,
storage (e.g. photo attachments), and authentication services.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING, Optional

from app.core.config import get_settings
from app.core.logging import get_logger

if TYPE_CHECKING:
    from supabase import Client

logger = get_logger(__name__)

__all__ = [
    "get_supabase_client",
    "get_supabase_admin_client",
    "get_supabase",
    "get_supabase_admin",
]


class SupabaseConfigError(RuntimeError):
    """Raised when Supabase is invoked without necessary URL or credentials."""


@lru_cache(maxsize=1)
def get_supabase_client() -> "Client":
    """Return a cached Supabase client initialized with the publishable key.

    Falls back to the secret key if no publishable key is configured.
    Use for client-scoped operations respecting Row Level Security (RLS).
    """
    settings = get_settings()
    if not settings.SUPABASE_URL:
        raise SupabaseConfigError(
            "SUPABASE_URL is not configured in settings / .env. "
            "Please set SUPABASE_URL=https://<project-id>.supabase.co"
        )

    key = settings.SUPABASE_PUBLISHABLE_KEY or settings.SUPABASE_SECRET_KEY
    if not key:
        raise SupabaseConfigError(
            "Neither SUPABASE_PUBLISHABLE_KEY nor SUPABASE_SECRET_KEY is configured."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "The 'supabase' package is not installed. Run 'pip install supabase'."
        ) from exc

    logger.info("Initializing Supabase client for %s", settings.SUPABASE_URL)
    return create_client(settings.SUPABASE_URL, key)


@lru_cache(maxsize=1)
def get_supabase_admin_client() -> "Client":
    """Return a cached admin Supabase client initialized with the secret key.

    Use strictly server-side for administrative actions, bypassing RLS.
    Never expose this client or secret key to the frontend.
    """
    settings = get_settings()
    if not settings.SUPABASE_URL:
        raise SupabaseConfigError(
            "SUPABASE_URL is not configured in settings / .env. "
            "Please set SUPABASE_URL=https://<project-id>.supabase.co"
        )

    if not settings.SUPABASE_SECRET_KEY:
        raise SupabaseConfigError(
            "SUPABASE_SECRET_KEY is not configured in settings / .env."
        )

    try:
        from supabase import create_client
    except ImportError as exc:
        raise RuntimeError(
            "The 'supabase' package is not installed. Run 'pip install supabase'."
        ) from exc

    logger.info("Initializing Supabase Admin client for %s", settings.SUPABASE_URL)
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SECRET_KEY)


def get_supabase() -> "Client":
    """FastAPI dependency for accessing the standard Supabase client."""
    return get_supabase_client()


def get_supabase_admin() -> "Client":
    """FastAPI dependency for accessing the admin Supabase client."""
    return get_supabase_admin_client()
