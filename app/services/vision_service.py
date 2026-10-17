"""Gemini Vision analysis for citizen photos and worker evidence shots.

Two public entry points:

* :func:`analyze_report_photo` runs on an initial citizen upload. It returns a
  category, priority, generated title/description and (when the model finds
  one) a short free-text location hint. This drives the "AI Vision Auto-Fill
  from Photo" workflow on the frontend.

* :func:`verify_resolution_photo` runs on a worker's evidence photo at resolve
  time. It compares the fix photo against the original complaint context and
  returns a match score 0..1 plus a short reason. Low-confidence results feed
  the admin-review flag.

Both calls are **non-fatal**: the application must keep working when Gemini is
unreachable, mis-configured or returning garbage. In all failure modes the
functions return ``None`` and the caller falls back to deterministic defaults.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.core.enums import ReportCategory, ReportPriority
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "VisionAutoFill",
    "ResolutionVerdict",
    "analyze_report_photo",
    "verify_resolution_photo",
]

_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

_ALLOWED_CATEGORIES = sorted(c.value for c in ReportCategory)
_ALLOWED_PRIORITIES = sorted(p.value for p in ReportPriority)


@dataclass(frozen=True, slots=True)
class VisionAutoFill:
    """Everything the citizen form can prefill from a single photo."""

    category: ReportCategory
    priority: ReportPriority
    title: str
    description: str
    location_hint: str | None
    confidence: float
    source: str  # "gemini"
    # Spam/junk assessment folded into the same call: 0 = legit public issue,
    # 1 = clearly test/junk/abuse. ``is_spam`` is the model's binary verdict.
    spam_score: float = 0.0
    is_spam: bool = False
    spam_reason: str | None = None


@dataclass(frozen=True, slots=True)
class ResolutionVerdict:
    """Match assessment between an original complaint and a fix photo."""

    match_score: float  # 0..1
    looks_fixed: bool
    reason: str
    source: str  # "gemini"


# ---------------------------------------------------------------------------
# Low-level transport
# ---------------------------------------------------------------------------
def _sniff_mime(data: bytes) -> str:
    """Best-effort MIME detection for the Gemini inline_data block."""
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    # Fall back to JPEG; Gemini will still try to read it.
    return "image/jpeg"


def _inline_image_part(data: bytes) -> dict[str, Any]:
    return {
        "inline_data": {
            "mime_type": _sniff_mime(data),
            "data": base64.b64encode(data).decode("ascii"),
        }
    }


def _call_gemini(
    settings: Settings,
    *,
    parts: list[dict[str, Any]],
    schema: dict[str, Any],
    temperature: float = 0.1,
) -> dict[str, Any] | None:
    """One Gemini call that enforces a JSON response schema.

    Returns the parsed top-level JSON dict, or ``None`` on any failure. All
    network and parsing errors are swallowed; the caller must treat ``None``
    as "AI unavailable, fall through to deterministic path".
    """
    import httpx  # local import keeps the module cheap on import

    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    body: dict[str, Any] = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {
            "temperature": temperature,
            "responseMimeType": "application/json",
            "responseSchema": schema,
        },
    }

    try:
        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            # Send the API key in a header rather than ?key= so that it does
            # not land in httpx's DEBUG request-URL logs.
            response = client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=body,
            )
    except httpx.HTTPError as exc:
        logger.warning("Gemini vision request failed: %s", type(exc).__name__)
        return None

    if response.status_code != 200:
        logger.warning("Gemini vision HTTP %s", response.status_code)
        return None

    try:
        payload = response.json()
    except ValueError:
        logger.warning("Gemini vision response was not valid JSON")
        return None

    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        logger.warning("Gemini vision response missing expected shape")
        return None

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Gemini vision returned non-JSON payload")
        return None


# ---------------------------------------------------------------------------
# Public: initial citizen upload
# ---------------------------------------------------------------------------
_AUTOFILL_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": _ALLOWED_CATEGORIES},
        "priority": {"type": "string", "enum": _ALLOWED_PRIORITIES},
        "title": {"type": "string"},
        "description": {"type": "string"},
        "location_hint": {"type": "string"},
        "confidence": {"type": "number"},
        "spam_score": {"type": "number"},
        "is_spam": {"type": "boolean"},
        "spam_reason": {"type": "string"},
    },
    "required": [
        "category",
        "priority",
        "title",
        "description",
        "confidence",
        "spam_score",
        "is_spam",
    ],
}

_AUTOFILL_PROMPT = (
    "You are an urban-services triage assistant. The attached photo was just "
    "submitted by a citizen reporting a neighborhood issue. Produce STRICT "
    "JSON with these fields:\n"
    "- category: one of road_damage, streetlight, garbage, water_leak, "
    "drainage, public_property, other.\n"
    "- priority: urgent (immediate danger: exposed live wires, active "
    "flooding, gas, fire, structural collapse), high (significant hazard or "
    "any water/sewer failure), medium (potholes, broken lights, piled "
    "garbage), low (cosmetic / minor).\n"
    "- title: 4-10 words, professional and specific.\n"
    "- description: 1-3 sentences, concrete and measurable where possible "
    "(e.g. 'Approx. 8-inch deep asphalt depression on travel lane with "
    "exposed base aggregate').\n"
    "- location_hint: short free-text description of landmarks or signage "
    "visible in the photo (optional; omit if nothing identifiable).\n"
    "- confidence: 0..1, how sure you are of the category.\n"
    "- spam_score: 0..1. 1.0 means the photo is clearly NOT a public "
    "infrastructure issue: a selfie, meme, screenshot, blank/black image, "
    "indoor private space, pornography, hateful content, random object, "
    "test upload or anything a reasonable moderator would reject. 0.0 "
    "means a plausible civic report. Scores 0.4-0.7 mean 'borderline, "
    "needs a human'.\n"
    "- is_spam: true only when spam_score >= 0.8 and you are confident the "
    "report should be auto-rejected.\n"
    "- spam_reason: short sentence (<=140 chars) explaining why if "
    "spam_score > 0; omit otherwise.\n"
    "Return JSON only; no prose."
)


def analyze_report_photo(image_bytes: bytes) -> VisionAutoFill | None:
    """Analyze a citizen photo. Returns ``None`` when Gemini is unavailable."""
    if not image_bytes:
        return None
    settings = get_settings()
    if not settings.gemini_configured:
        return None

    parts: list[dict[str, Any]] = [
        {"text": _AUTOFILL_PROMPT},
        _inline_image_part(image_bytes),
    ]
    data = _call_gemini(settings, parts=parts, schema=_AUTOFILL_SCHEMA)
    if data is None:
        return None

    category = data.get("category")
    priority = data.get("priority")
    if category not in {c.value for c in ReportCategory}:
        return None
    if priority not in {p.value for p in ReportPriority}:
        return None

    title = str(data.get("title", "")).strip()[:200]
    description = str(data.get("description", "")).strip()[:5000]
    if not title or not description:
        return None

    location_hint = data.get("location_hint")
    if isinstance(location_hint, str):
        location_hint = location_hint.strip()[:500] or None
    else:
        location_hint = None

    try:
        confidence = float(data.get("confidence", 0.6))
    except (TypeError, ValueError):
        confidence = 0.6
    confidence = max(0.0, min(1.0, confidence))

    try:
        spam_score = float(data.get("spam_score", 0.0))
    except (TypeError, ValueError):
        spam_score = 0.0
    spam_score = max(0.0, min(1.0, spam_score))
    is_spam = bool(data.get("is_spam", False))
    spam_reason = data.get("spam_reason")
    if isinstance(spam_reason, str):
        spam_reason = spam_reason.strip()[:280] or None
    else:
        spam_reason = None

    return VisionAutoFill(
        category=ReportCategory(category),
        priority=ReportPriority(priority),
        title=title,
        description=description,
        location_hint=location_hint,
        confidence=confidence,
        source="gemini",
        spam_score=spam_score,
        is_spam=is_spam,
        spam_reason=spam_reason,
    )


# ---------------------------------------------------------------------------
# Public: worker evidence photo
# ---------------------------------------------------------------------------
_VERIFY_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "match_score": {"type": "number"},
        "looks_fixed": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["match_score", "looks_fixed", "reason"],
}

_VERIFY_PROMPT_TMPL = (
    "You are reviewing closure evidence for a city issue report. The citizen "
    "originally reported:\n"
    "- Category: {category}\n"
    "- Title: {title}\n"
    "- Description: {description}\n\n"
    "A worker is now closing the ticket and uploaded the attached photo as "
    "proof of repair. Judge whether this photo plausibly shows the described "
    "issue in a fixed/clean state. Produce STRICT JSON:\n"
    "- match_score: 0..1, higher means the fix photo is on-topic and shows "
    "the issue resolved. Below 0.5 means the photo is unrelated, blurry, "
    "or does not show the described repair.\n"
    "- looks_fixed: boolean, true only if the photo clearly shows the "
    "problem resolved (not just a different angle of the same damage).\n"
    "- reason: one short sentence (<=140 chars) explaining the score.\n"
    "Return JSON only; no prose."
)


def verify_resolution_photo(
    *,
    image_bytes: bytes,
    category: ReportCategory,
    title: str,
    description: str,
) -> ResolutionVerdict | None:
    """Score a worker's fix photo against the original complaint."""
    if not image_bytes:
        return None
    settings = get_settings()
    if not settings.gemini_configured:
        return None

    prompt = _VERIFY_PROMPT_TMPL.format(
        category=category.value,
        title=title[:200],
        description=description[:1000],
    )
    parts: list[dict[str, Any]] = [
        {"text": prompt},
        _inline_image_part(image_bytes),
    ]
    data = _call_gemini(settings, parts=parts, schema=_VERIFY_SCHEMA)
    if data is None:
        return None

    try:
        match_score = float(data.get("match_score", 0.0))
    except (TypeError, ValueError):
        return None
    match_score = max(0.0, min(1.0, match_score))

    looks_fixed = bool(data.get("looks_fixed", False))
    reason = str(data.get("reason", "")).strip()[:280]
    if not reason:
        reason = "No reason provided."

    return ResolutionVerdict(
        match_score=match_score,
        looks_fixed=looks_fixed,
        reason=reason,
        source="gemini",
    )
