"""Settings parsing, validation and derived values."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import (
    BACKEND_DIR,
    PLACEHOLDER_SECRET_KEY,
    Settings,
    get_settings,
)


def _settings(**overrides: object) -> Settings:
    """Build settings from explicit values, ignoring the ambient environment."""
    base: dict[str, object] = {
        "APP_NAME": "Test API",
        "APP_ENV": "test",
        "DEBUG": False,
        "API_V1_PREFIX": "/api/v1",
        "SECRET_KEY": "unit-test-secret",
        "ACCESS_TOKEN_EXPIRE_MINUTES": 60,
        "CORS_ORIGINS": "*",
        "UPLOAD_DIR": "uploads",
        "MAX_UPLOAD_SIZE_MB": 5,
    }
    base.update(overrides)
    return Settings(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Required settings are present
# ---------------------------------------------------------------------------
def test_all_phase1_settings_are_supported() -> None:
    config = _settings()

    for name in (
        "APP_NAME",
        "APP_ENV",
        "DEBUG",
        "API_V1_PREFIX",
        "SECRET_KEY",
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        "CORS_ORIGINS",
        "UPLOAD_DIR",
        "MAX_UPLOAD_SIZE_MB",
    ):
        assert hasattr(config, name), f"missing setting: {name}"


def test_api_prefix_defaults_to_api_v1() -> None:
    assert Settings.model_fields["API_V1_PREFIX"].default == "/api/v1"


def test_settings_are_immutable() -> None:
    config = _settings()

    with pytest.raises(ValidationError):
        config.APP_NAME = "mutated"  # type: ignore[misc]


def test_get_settings_is_cached() -> None:
    assert get_settings() is get_settings()


# ---------------------------------------------------------------------------
# CORS parsing
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("*", ["*"]),
        ("http://localhost:3000", ["http://localhost:3000"]),
        (
            "http://localhost:3000,http://localhost:5173",
            ["http://localhost:3000", "http://localhost:5173"],
        ),
        (
            " http://a.test , http://b.test ",
            ["http://a.test", "http://b.test"],
        ),
        (
            '["http://a.test","http://b.test"]',
            ["http://a.test", "http://b.test"],
        ),
        ("", []),
    ],
)
def test_cors_origins_accepts_csv_and_json(raw: str, expected: list[str]) -> None:
    assert _settings(CORS_ORIGINS=raw).cors_origins == expected


def test_wildcard_origin_is_detected() -> None:
    assert _settings(CORS_ORIGINS="*").allow_all_origins is True
    assert _settings(CORS_ORIGINS="http://a.test").allow_all_origins is False


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("bad_prefix", ["api/v1", "v1", "api"])
def test_api_prefix_must_start_with_a_slash(bad_prefix: str) -> None:
    with pytest.raises(ValidationError):
        _settings(API_V1_PREFIX=bad_prefix)


def test_api_prefix_must_not_end_with_a_slash() -> None:
    with pytest.raises(ValidationError):
        _settings(API_V1_PREFIX="/api/v1/")


@pytest.mark.parametrize("bad_value", [0, -1, -60])
def test_token_expiry_must_be_positive(bad_value: int) -> None:
    with pytest.raises(ValidationError):
        _settings(ACCESS_TOKEN_EXPIRE_MINUTES=bad_value)


@pytest.mark.parametrize("bad_value", [0, -5])
def test_max_upload_size_must_be_positive(bad_value: int) -> None:
    with pytest.raises(ValidationError):
        _settings(MAX_UPLOAD_SIZE_MB=bad_value)


def test_unknown_app_env_is_rejected() -> None:
    with pytest.raises(ValidationError):
        _settings(APP_ENV="banana")


def test_production_refuses_the_placeholder_secret() -> None:
    """A deployment must not run on the secret published in .env.example."""
    with pytest.raises(ValidationError, match="placeholder"):
        _settings(APP_ENV="production", SECRET_KEY=PLACEHOLDER_SECRET_KEY)


def test_production_accepts_a_real_secret() -> None:
    config = _settings(APP_ENV="production", SECRET_KEY="a-genuinely-random-secret")

    assert config.is_production is True


# ---------------------------------------------------------------------------
# Derived values
# ---------------------------------------------------------------------------
def test_relative_upload_dir_resolves_against_the_backend_directory() -> None:
    config = _settings(UPLOAD_DIR="uploads")

    assert config.upload_path == BACKEND_DIR / "uploads"
    assert config.upload_path.is_absolute()


def test_absolute_upload_dir_is_preserved() -> None:
    absolute = Path(BACKEND_DIR / "custom-uploads").resolve()
    config = _settings(UPLOAD_DIR=str(absolute))

    assert config.upload_path == absolute


def test_max_upload_size_bytes_conversion() -> None:
    assert _settings(MAX_UPLOAD_SIZE_MB=5).max_upload_size_bytes == 5 * 1024 * 1024


def test_docs_disabled_only_in_production_without_debug() -> None:
    assert _settings(APP_ENV="local", DEBUG=True).docs_enabled is True
    assert _settings(APP_ENV="test", DEBUG=False).docs_enabled is True
    assert (
        _settings(APP_ENV="production", DEBUG=False, SECRET_KEY="real").docs_enabled
        is False
    )
