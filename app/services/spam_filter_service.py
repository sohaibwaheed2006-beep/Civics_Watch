"""Spam / junk / abuse filter for incoming reports.

Two layers:

* **Deterministic heuristics** catch the obvious junk for free and offline:
  test strings, keyboard mashing, single repeated characters, no real words,
  profanity-only content. These produce a high score with no network call.

* **Gemini text check** is consulted only for the borderline middle band, so
  a clearly-fine or clearly-junk report never pays for an API round-trip.

The caller decides what to do with the score. The convention used across the
app:

* ``score >= SPAM_AUTO_REJECT_SCORE`` -> auto-reject (report is recorded as
  rejected with the reason; it never enters the work queue).
* ``score >= SPAM_FLAG_SCORE`` -> keep the report but flag it for a human.
* otherwise -> normal.

Like every AI hook here, the Gemini layer is non-fatal: any failure falls back
to the deterministic score, which is always available.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = ["SpamVerdict", "assess_text"]


@dataclass(frozen=True, slots=True)
class SpamVerdict:
    score: float  # 0..1, higher = more likely junk
    is_spam: bool  # score >= auto-reject threshold
    is_flagged: bool  # score >= flag threshold (but below auto-reject)
    reason: str | None
    source: str  # "deterministic" or "gemini"


# A small, conservative junk-word set. Kept deliberately short: the goal is to
# catch obvious test/abuse content, not to moralise. Borderline content is
# handed to the model, not keyword-matched.
_TEST_TOKENS = frozenset(
    {
        "test",
        "testing",
        "asdf",
        "asdasd",
        "qwerty",
        "qwe",
        "hello",
        "hi",
        "ignore",
        "sample",
        "dummy",
        "lorem",
        "ipsum",
        "blah",
        "xyz",
        "abc",
    }
)

_WORD_RE = re.compile(r"[A-Za-z]{2,}")


def _deterministic_score(title: str, description: str) -> SpamVerdict | None:
    """Cheap offline heuristics. Returns ``None`` when nothing fires.

    ``None`` means "no strong signal either way" and lets the caller decide
    whether to consult the model.
    """
    combined = f"{title} {description}".strip().lower()
    if not combined:
        return SpamVerdict(
            score=0.95,
            is_spam=True,
            is_flagged=False,
            reason="Empty report content.",
            source="deterministic",
        )

    words = _WORD_RE.findall(combined)
    # Keyboard mashing / no real words.
    if not words:
        return SpamVerdict(
            score=0.9,
            is_spam=True,
            is_flagged=False,
            reason="No readable words in the report.",
            source="deterministic",
        )

    # A single character repeated (e.g. "aaaaaa", "....", "!!!!").
    stripped = re.sub(r"\s", "", combined)
    if len(stripped) >= 5 and len(set(stripped)) <= 2:
        return SpamVerdict(
            score=0.9,
            is_spam=True,
            is_flagged=False,
            reason="Report is a single repeated character.",
            source="deterministic",
        )

    # Content is made up entirely of test/junk tokens.
    unique_words = set(words)
    if unique_words and unique_words <= _TEST_TOKENS:
        return SpamVerdict(
            score=0.88,
            is_spam=True,
            is_flagged=False,
            reason="Report looks like a test/placeholder submission.",
            source="deterministic",
        )

    # Very short and dominated by a test token -> borderline, flag only.
    if len(words) <= 3 and unique_words & _TEST_TOKENS:
        return SpamVerdict(
            score=0.6,
            is_spam=False,
            is_flagged=True,
            reason="Very short report containing test-like words.",
            source="deterministic",
        )

    return None


# ---------------------------------------------------------------------------
# Gemini text check (borderline band only)
# ---------------------------------------------------------------------------
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

_SPAM_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "spam_score": {"type": "number"},
        "reason": {"type": "string"},
    },
    "required": ["spam_score"],
}

_SPAM_PROMPT = (
    "You are a moderation filter for a city's public issue-reporting system. "
    "Decide whether the following report is a genuine civic issue or junk "
    "(test content, gibberish, spam, advertising, or abuse). Return STRICT "
    "JSON:\n"
    "- spam_score: 0..1. 0 = clearly a real neighborhood issue; 1 = clearly "
    "junk/abuse/test. Use the middle of the range when genuinely unsure.\n"
    "- reason: short sentence (<=140 chars) explaining the score.\n"
    "Report title: {title}\n"
    "Report description: {description}\n"
    "Return JSON only; no prose."
)


def _call_gemini_text(
    settings: Settings, *, title: str, description: str
) -> tuple[float, str | None] | None:
    import httpx

    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    prompt = _SPAM_PROMPT.format(title=title[:200], description=description[:2000])
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.0,
            "responseMimeType": "application/json",
            "responseSchema": _SPAM_SCHEMA,
        },
    }
    try:
        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            response = client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Spam text check failed: %s", type(exc).__name__)
        return None
    if response.status_code != 200:
        logger.warning("Spam text check HTTP %s", response.status_code)
        return None
    try:
        payload = response.json()
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
        parsed = json.loads(text)
    except (ValueError, KeyError, IndexError, TypeError):
        logger.warning("Spam text check returned an unexpected shape")
        return None
    try:
        score = float(parsed.get("spam_score", 0.0))
    except (TypeError, ValueError):
        return None
    score = max(0.0, min(1.0, score))
    reason = parsed.get("reason")
    if isinstance(reason, str):
        reason = reason.strip()[:280] or None
    else:
        reason = None
    return score, reason


def assess_text(title: str, description: str) -> SpamVerdict:
    """Assess a report's text. Always returns a verdict (never raises)."""
    settings = get_settings()
    reject_at = settings.SPAM_AUTO_REJECT_SCORE
    flag_at = settings.SPAM_FLAG_SCORE

    deterministic = _deterministic_score(title, description)
    if deterministic is not None:
        # Re-derive the bands from the configured thresholds so a tuned config
        # is respected rather than the hard-coded flags above.
        return SpamVerdict(
            score=deterministic.score,
            is_spam=deterministic.score >= reject_at,
            is_flagged=flag_at <= deterministic.score < reject_at,
            reason=deterministic.reason,
            source="deterministic",
        )

    # Nothing obvious fired. Consult the model only if it's configured.
    if settings.gemini_configured:
        try:
            result = _call_gemini_text(
                settings, title=title, description=description
            )
            if result is not None:
                score, reason = result
                return SpamVerdict(
                    score=score,
                    is_spam=score >= reject_at,
                    is_flagged=flag_at <= score < reject_at,
                    reason=reason,
                    source="gemini",
                )
        except Exception as exc:  # noqa: BLE001 - never block submission
            logger.warning("Spam text check raised: %s", type(exc).__name__)

    # Default: treat as clean.
    return SpamVerdict(
        score=0.0,
        is_spam=False,
        is_flagged=False,
        reason=None,
        source="deterministic",
    )
