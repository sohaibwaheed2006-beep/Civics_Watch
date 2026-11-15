"""Error tracking / observability wiring (Sentry).

Kept deliberately optional: with no ``SENTRY_DSN`` configured the SDK is never
initialised, so there is zero runtime cost and nothing leaves the process. This
mirrors how the rest of the app treats optional integrations (Gemini, SMTP,
Google Maps) — a ``*_configured`` flag gates the feature and it degrades to a
no-op when the credential is absent.
"""

from __future__ import annotations

from app.core.config import Settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def init_sentry(settings: Settings) -> bool:
    """Initialise Sentry if a DSN is configured.

    Returns ``True`` when Sentry was initialised, ``False`` otherwise (DSN not
    set, or the SDK is not installed). Never raises: a monitoring failure must
    not stop the application from booting.
    """
    if not settings.sentry_configured:
        logger.info("Sentry disabled (SENTRY_DSN not set)")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:  # pragma: no cover - defensive; dep is in requirements
        logger.warning(
            "SENTRY_DSN is set but sentry-sdk is not installed; "
            "run 'pip install -r requirements.txt'. Error tracking is OFF."
        )
        return False

    sentry_sdk.init(
        dsn=settings.SENTRY_DSN.strip(),
        environment=settings.APP_ENV,
        release=None,  # Render/CI can set this via SENTRY_RELEASE if desired.
        # Errors are always captured at 100%; only tracing is sampled.
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        # Don't attach request bodies / headers that may carry the bearer token
        # or personal data. Stack traces and request metadata are enough.
        send_default_pii=False,
        integrations=[StarletteIntegration(), FastApiIntegration()],
    )
    logger.info("Sentry initialised | env=%s", settings.APP_ENV)
    return True
