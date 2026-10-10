"""Application configuration.

Settings are loaded from environment variables, falling back to the
``backend/.env`` file and finally to the defaults declared below. The whole
application reads configuration through :func:`get_settings`, which caches a
single immutable ``Settings`` instance for the process lifetime.

Phase 1 note
------------
There is deliberately **no** ``DATABASE_URL`` setting. The application must be
able to boot with no database configured at all. The persistence settings are
introduced in Phase 2 alongside SQLAlchemy.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import computed_field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ``backend/`` - config.py lives at backend/app/core/config.py, so two parents
# up from the file's directory. Used to resolve relative paths (.env, uploads)
# independently of the directory the process was started from.
BACKEND_DIR: Path = Path(__file__).resolve().parents[2]

#: Sentinel value shipped in ``.env.example``. Refused in production.
PLACEHOLDER_SECRET_KEY = "replace-with-a-long-random-secret-value"

AppEnv = Literal["local", "development", "test", "staging", "production"]


class Settings(BaseSettings):
    """Typed, validated application settings."""

    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
        frozen=True,
    )

    # --- Application ------------------------------------------------------
    APP_NAME: str = "Neighborhood Issue Reporter API"
    APP_ENV: AppEnv = "local"
    DEBUG: bool = True

    #: Mount point shared by every versioned router.
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---------------------------------------------------------
    #: SQLAlchemy URL for MySQL 8, e.g.
    #: ``mysql+pymysql://user:password@127.0.0.1:3306/neighborhood_issues``
    #: The default is a non-functional placeholder so the application still
    #: imports and serves ``/health`` before MySQL is configured. Connections
    #: are opened lazily, so a wrong URL only fails when a request needs data.
    DATABASE_URL: str = (
        "mysql+pymysql://CHANGE_ME:CHANGE_ME@127.0.0.1:3306/neighborhood_issues"
    )

    #: Connection pool sizing. ``pool_recycle`` sits below MySQL's default
    #: ``wait_timeout`` (28800s) so the pool never hands out a connection the
    #: server has already dropped.
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    DB_POOL_RECYCLE_SECONDS: int = 1800

    #: Log every emitted SQL statement. Noisy; local debugging only.
    DB_ECHO: bool = False

    # --- Security ---------------------------------------------------------
    SECRET_KEY: str = PLACEHOLDER_SECRET_KEY
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # --- CORS -------------------------------------------------------------
    # Kept as a raw string so that both a comma-separated list and a JSON
    # array are accepted from the environment. Use the ``cors_origins``
    # property to get the parsed value; pydantic-settings would otherwise
    # insist on strict JSON for a ``list[str]`` field.
    CORS_ORIGINS: str = "*"

    # --- Uploads (used by the report-photo module in a later phase) -------
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_SIZE_MB: int = 5

    # --- Supabase ---------------------------------------------------------
    SUPABASE_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_SECRET_KEY: str = ""

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("API_V1_PREFIX")
    @classmethod
    def _validate_prefix(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("/"):
            raise ValueError("API_V1_PREFIX must start with '/'")
        if len(value) > 1 and value.endswith("/"):
            raise ValueError("API_V1_PREFIX must not end with '/'")
        return value

    @field_validator("ACCESS_TOKEN_EXPIRE_MINUTES")
    @classmethod
    def _validate_token_expiry(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("ACCESS_TOKEN_EXPIRE_MINUTES must be positive")
        return value

    @field_validator("MAX_UPLOAD_SIZE_MB")
    @classmethod
    def _validate_upload_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be positive")
        return value

    @field_validator("APP_NAME", "UPLOAD_DIR")
    @classmethod
    def _validate_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value must not be empty")
        return value

    @field_validator("DATABASE_URL")
    @classmethod
    def _validate_database_url(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("DATABASE_URL must not be empty")
        # Guard the common mistakes: a bare hostname, or a Postgres URL copied
        # from another project. SQLite is allowed only for isolated tests.
        if "://" not in value:
            raise ValueError(
                "DATABASE_URL must be a SQLAlchemy URL, e.g. "
                "mysql+pymysql://user:password@host:3306/dbname"
            )
        scheme = value.split("://", 1)[0].lower()
        if not scheme.startswith(("mysql", "sqlite")):
            raise ValueError(
                f"unsupported database dialect {scheme!r}; this project targets "
                "MySQL 8 (mysql+pymysql://...)"
            )
        return value

    @field_validator("DB_POOL_SIZE", "DB_POOL_RECYCLE_SECONDS")
    @classmethod
    def _validate_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    @field_validator("DB_MAX_OVERFLOW")
    @classmethod
    def _validate_non_negative(cls, value: int) -> int:
        if value < 0:
            raise ValueError("value must not be negative")
        return value

    @model_validator(mode="after")
    def _guard_production_secret(self) -> "Settings":
        """Refuse to run production with the shipped placeholder secret."""
        if self.APP_ENV == "production" and self.SECRET_KEY == PLACEHOLDER_SECRET_KEY:
            raise ValueError(
                "SECRET_KEY still holds the placeholder value from .env.example; "
                "set a unique random SECRET_KEY before running in production"
            )
        return self

    # ------------------------------------------------------------------
    # Derived values
    # ------------------------------------------------------------------
    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins(self) -> list[str]:
        """``CORS_ORIGINS`` parsed into a list.

        Accepts a JSON array (``["http://a","http://b"]``) or a
        comma-separated string (``http://a,http://b``). Returns ``["*"]`` when
        every origin is allowed.
        """
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError as exc:  # pragma: no cover - defensive
                raise ValueError(f"CORS_ORIGINS is not valid JSON: {exc}") from exc
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def allow_all_origins(self) -> bool:
        """True when CORS is wide open, which forbids credentialed requests."""
        return "*" in self.cors_origins

    @property
    def upload_path(self) -> Path:
        """``UPLOAD_DIR`` resolved to an absolute path."""
        candidate = Path(self.UPLOAD_DIR)
        if not candidate.is_absolute():
            candidate = BACKEND_DIR / candidate
        return candidate

    @property
    def max_upload_size_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_sqlite(self) -> bool:
        """True when pointed at SQLite, which needs different pool options."""
        return self.DATABASE_URL.lower().startswith("sqlite")

    @property
    def database_url_safe(self) -> str:
        """``DATABASE_URL`` with the password masked, for logs and diagnostics.

        Never log ``DATABASE_URL`` directly.
        """
        url = self.DATABASE_URL
        if "://" not in url:
            return url
        scheme, _, remainder = url.partition("://")
        if "@" not in remainder:
            return url
        credentials, _, host = remainder.partition("@")
        user, sep, _password = credentials.partition(":")
        if not sep:
            return url
        return f"{scheme}://{user}:***@{host}"

    @property
    def database_configured(self) -> bool:
        """False while ``DATABASE_URL`` still holds the shipped placeholder."""
        return "CHANGE_ME" not in self.DATABASE_URL

    @property
    def supabase_configured(self) -> bool:
        """True when SUPABASE_URL and at least one Supabase key are configured."""
        return bool(
            self.SUPABASE_URL.strip()
            and (self.SUPABASE_PUBLISHABLE_KEY.strip() or self.SUPABASE_SECRET_KEY.strip())
        )

    @property
    def docs_enabled(self) -> bool:
        """Interactive docs are always on outside production."""
        return not self.is_production or self.DEBUG


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the cached settings instance.

    Cached so that env parsing and validation happen once. Call
    ``get_settings.cache_clear()`` in tests that need to re-read the
    environment.
    """
    return Settings()


#: Convenience module-level handle for straightforward imports.
settings: Settings = get_settings()
