"""Tests for Supabase client initialization."""

from __future__ import annotations

import pytest

from app.core.config import get_settings
from app.core.supabase import (
    SupabaseConfigError,
    get_supabase_admin_client,
    get_supabase_client,
)


def test_supabase_client_raises_when_no_url(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", "")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    get_settings.cache_clear()
    get_supabase_client.cache_clear()

    with pytest.raises(SupabaseConfigError, match="SUPABASE_URL is not configured"):
        get_supabase_client()


def test_supabase_admin_client_raises_when_no_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUPABASE_URL", "https://xyz.supabase.co")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "")
    get_settings.cache_clear()
    get_supabase_admin_client.cache_clear()

    with pytest.raises(SupabaseConfigError, match="SUPABASE_SECRET_KEY is not configured"):
        get_supabase_admin_client()
