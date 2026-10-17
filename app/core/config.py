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
    #: SQLAlchemy URL for the Supabase Postgres instance, e.g.
    #: ``postgresql+psycopg2://postgres.<ref>:<password>@aws-0-<region>.pooler.supabase.com:6543/postgres``
    #: SQLite is accepted for local-only development. Connections are opened
    #: lazily, so a wrong URL only fails when a request needs data.
    DATABASE_URL: str = (
        "postgresql+psycopg2://CHANGE_ME:CHANGE_ME@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
    )

    #: Connection pool sizing. ``pool_recycle`` keeps idle connections well
    #: below any upstream idle timeout, so the pool never hands out a
    #: connection the server has already dropped.
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

    # --- Photo storage ----------------------------------------------------
    #: Where report photos are stored. "local" writes to UPLOAD_DIR, which is
    #: fine for a single long-running server with a persistent disk. "supabase"
    #: uploads to a Supabase Storage bucket and is REQUIRED on hosts with an
    #: ephemeral filesystem (Render's free tier, Vercel serverless), where the
    #: local disk is wiped on every restart and uploads would silently vanish.
    PHOTO_STORAGE_BACKEND: Literal["local", "supabase"] = "local"

    #: Supabase Storage bucket for report photos. Create it as a *public* bucket
    #: in the Supabase dashboard (Storage -> New bucket, "Public bucket" on).
    SUPABASE_STORAGE_BUCKET: str = "report-photos"

    # --- Report domain ----------------------------------------------------
    #: Maximum photos per report. Keeps a single actor from flooding storage.
    MAX_PHOTOS_PER_REPORT: int = 8

    #: Duplicate-detection radius in metres. Reports closer than this and in a
    #: compatible category are candidates for duplicate flagging.
    DUPLICATE_RADIUS_METERS: int = 150

    #: Time window (hours) within which two reports can be duplicates.
    DUPLICATE_TIME_WINDOW_HOURS: int = 168  # one week

    #: Minimum duplicate score (0..1) for a candidate to be surfaced.
    DUPLICATE_MIN_SCORE: float = 0.55

    # --- AI (optional) ----------------------------------------------------
    AI_ENABLED: bool = False
    AI_PROVIDER: str = "deterministic"
    AI_API_KEY: str = ""
    AI_MODEL: str = ""
    AI_TIMEOUT_SECONDS: int = 10

    # --- Google AI (Gemini) ----------------------------------------------
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-flash-lite-latest"

    #: Resolution-note quality check: match scores below this flag the closure
    #: for admin review. The worker's photo must look like the described fix.
    RESOLUTION_MATCH_MIN_SCORE: float = 0.55

    #: Incident clustering: if a new report scores at or above this against an
    #: existing cluster member, it inherits the same cluster id.
    CLUSTER_LINK_MIN_SCORE: float = 0.60

    #: Spam filter thresholds (0..1). At or above the reject score a report is
    #: auto-rejected and never enters the work queue. Between the flag score
    #: and the reject score it is kept but flagged for human review.
    SPAM_AUTO_REJECT_SCORE: float = 0.85
    SPAM_FLAG_SCORE: float = 0.50

    #: Worker bonus weighting. The three must sum to 1.0; validated below.
    BONUS_WEIGHT_RATING: float = 0.5
    BONUS_WEIGHT_SPEED: float = 0.3
    BONUS_WEIGHT_VOLUME: float = 0.2

    # --- Google Maps -----------------------------------------------------
    GOOGLE_MAPS_API_KEY: str = ""

    # --- Email / SMTP -----------------------------------------------------
    #: Master switch. Even with SMTP configured, set this False to silence all
    #: outbound mail (useful in tests and local demos).
    EMAIL_ENABLED: bool = True

    #: SMTP relay. Leave SMTP_HOST empty to disable email entirely; the auth
    #: flows then degrade gracefully (the reset endpoint still returns its
    #: generic 200, it just never dispatches a message).
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""

    #: STARTTLS on a plaintext connection (port 587, the common default) vs an
    #: implicit TLS connection (SMTP_USE_SSL, port 465). They are mutually
    #: exclusive; enabling both is rejected below.
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_TIMEOUT_SECONDS: int = 15

    #: Envelope sender. Falls back to SMTP_USERNAME when left blank.
    SMTP_FROM_EMAIL: str = ""
    #: Human-readable From name; falls back to APP_NAME when blank.
    SMTP_FROM_NAME: str = ""

    #: Base URL of the frontend, used to build links inside emails
    #: (``{FRONTEND_BASE_URL}/reset-password?token=...``). No trailing slash.
    FRONTEND_BASE_URL: str = "http://localhost:5173"

    #: Lifetime of a password-reset link. Short on purpose: a reset link is a
    #: bearer credential for the account.
    PASSWORD_RESET_TOKEN_EXPIRE_MINUTES: int = 30
    #: Lifetime of an email-verification link. Longer, since it is low-risk.
    EMAIL_VERIFICATION_TOKEN_EXPIRE_HOURS: int = 48

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
        # Guard the common mistake of a bare hostname with no scheme. SQLite
        # is allowed for local-only development; the shipping target is
        # Supabase (postgresql).
        if "://" not in value:
            raise ValueError(
                "DATABASE_URL must be a SQLAlchemy URL, e.g. "
                "postgresql+psycopg2://user:password@host:6543/postgres"
            )
        scheme = value.split("://", 1)[0].lower()
        if not scheme.startswith(("postgres", "sqlite")):
            raise ValueError(
                f"unsupported database dialect {scheme!r}; this project targets "
                "Supabase Postgres (postgresql+psycopg2://...)"
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

    @field_validator("SMTP_PORT", "SMTP_TIMEOUT_SECONDS")
    @classmethod
    def _validate_smtp_positive(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("value must be positive")
        return value

    @field_validator("FRONTEND_BASE_URL")
    @classmethod
    def _validate_frontend_base_url(cls, value: str) -> str:
        value = value.strip().rstrip("/")
        if value and "://" not in value:
            raise ValueError("FRONTEND_BASE_URL must include a scheme, e.g. http://")
        return value

    @model_validator(mode="after")
    def _validate_smtp_tls(self) -> "Settings":
        if self.SMTP_USE_TLS and self.SMTP_USE_SSL:
            raise ValueError(
                "SMTP_USE_TLS (STARTTLS) and SMTP_USE_SSL (implicit TLS) are "
                "mutually exclusive; enable only one"
            )
        return self

    @model_validator(mode="after")
    def _validate_bonus_weights(self) -> "Settings":
        total = (
            self.BONUS_WEIGHT_RATING
            + self.BONUS_WEIGHT_SPEED
            + self.BONUS_WEIGHT_VOLUME
        )
        if abs(total - 1.0) > 1e-6:
            raise ValueError(
                "BONUS_WEIGHT_RATING + BONUS_WEIGHT_SPEED + BONUS_WEIGHT_VOLUME "
                f"must sum to 1.0 (got {total:.6f})"
            )
        return self

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
    def is_postgres(self) -> bool:
        """True when pointed at Postgres / Supabase."""
        return self.DATABASE_URL.lower().startswith("postgres")

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
    def photo_storage_is_supabase(self) -> bool:
        """True when report photos should be stored in Supabase Storage."""
        return self.PHOTO_STORAGE_BACKEND == "supabase"

    @property
    def gemini_configured(self) -> bool:
        """True when a Gemini API key is set."""
        return bool(self.GEMINI_API_KEY.strip())

    @property
    def google_maps_configured(self) -> bool:
        """True when a Google Maps API key is set."""
        return bool(self.GOOGLE_MAPS_API_KEY.strip())

    @property
    def smtp_configured(self) -> bool:
        """True when enough SMTP settings are present to attempt delivery."""
        return bool(self.SMTP_HOST.strip() and self.smtp_from_email)

    @property
    def emails_enabled(self) -> bool:
        """True when outbound email is both switched on and configured."""
        return self.EMAIL_ENABLED and self.smtp_configured

    @property
    def smtp_from_email(self) -> str:
        """Envelope sender, defaulting to the SMTP username when unset."""
        return (self.SMTP_FROM_EMAIL or self.SMTP_USERNAME).strip()

    @property
    def smtp_from_name(self) -> str:
        """Display name for the From header, defaulting to the app name."""
        return self.SMTP_FROM_NAME.strip() or self.APP_NAME

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
