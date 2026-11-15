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

:func:`verify_resolution_photo` is **non-fatal**: it returns ``None`` when
Gemini is unreachable, mis-configured or returning garbage, and the caller
falls back to deterministic defaults.

:func:`analyze_report_photo` is stricter, because the citizen wizard needs to
tell two very different situations apart instead of silently moving on:

* :class:`PhotoNotRecognizedError` - Gemini answered but could not read the
  photo (undecodable image, safety block, unusable answer). The citizen should
  retake the photo.
* :class:`VisionUnavailableError` - Gemini itself is down / unconfigured /
  over quota. Retaking will not help; the citizen should retry shortly.

A successful result additionally carries ``issue_detected``: ``False`` means
the photo was readable but shows no clear public issue (also a retake).
"""

from __future__ import annotations

import base64
import json
import time
from dataclasses import dataclass
from typing import Any

from app.core.config import Settings, get_settings
from app.core.enums import ReportCategory, ReportPriority
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "VisionAutoFill",
    "ResolutionVerdict",
    "PhotoNotRecognizedError",
    "VisionUnavailableError",
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
    # False when the photo is readable but does not clearly show a reportable
    # public issue (blurry, too dark, too far away, or simply not an issue).
    # ``retake_reason`` then tells the citizen what to do differently.
    issue_detected: bool = True
    retake_reason: str | None = None


class VisionUnavailableError(Exception):
    """Photo analysis could not run at all (provider down / not configured)."""


class PhotoNotRecognizedError(Exception):
    """The provider could not read or interpret this particular photo."""


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


class _GeminiUnavailable(Exception):
    """The provider could not be reached or refused the call (network error,
    timeout, bad/expired key, quota, 5xx). Nothing is wrong with the photo."""


class _GeminiRejectedInput(Exception):
    """The provider answered, but could not make sense of this input: an
    undecodable image, a safety block, or an empty / malformed answer."""


#: Transient upstream statuses worth one more attempt before giving up.
_RETRYABLE_STATUSES = frozenset({429, 500, 502, 503, 504})
_MAX_ATTEMPTS = 2
_RETRY_BACKOFF_SECONDS = 0.8


def _upstream_error_summary(response: Any) -> str:
    """``STATUS: message`` from a Gemini error body, for the server log only.

    The body never echoes the API key (it travels in a header), and this is
    what tells an operator *why* a call failed: API_KEY_INVALID,
    RESOURCE_EXHAUSTED (quota), "Unable to process input image", etc.
    """
    try:
        err = response.json().get("error", {})
        return f"{err.get('status', '?')}: {str(err.get('message', ''))[:200]}"
    except Exception:  # noqa: BLE001 - diagnostics must never raise
        return "unparseable error body"


def _request_gemini(
    settings: Settings,
    *,
    parts: list[dict[str, Any]],
    schema: dict[str, Any],
    temperature: float = 0.1,
) -> dict[str, Any]:
    """One schema-enforced Gemini call, retried once on transient failures.

    Returns the parsed top-level JSON dict. Raises :class:`_GeminiUnavailable`
    when the service itself is the problem and :class:`_GeminiRejectedInput`
    when the service worked but this particular input produced no usable
    answer. Callers decide how to surface each.
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

    response = None
    for attempt in range(1, _MAX_ATTEMPTS + 1):
        last_attempt = attempt == _MAX_ATTEMPTS
        try:
            with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
                # Send the API key in a header rather than ?key= so that it
                # does not land in httpx's DEBUG request-URL logs.
                response = client.post(
                    url,
                    headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                    json=body,
                )
        except httpx.HTTPError as exc:
            logger.warning(
                "Gemini vision request failed (attempt %d/%d): %s",
                attempt,
                _MAX_ATTEMPTS,
                type(exc).__name__,
            )
            if last_attempt:
                raise _GeminiUnavailable(type(exc).__name__) from exc
            time.sleep(_RETRY_BACKOFF_SECONDS)
            continue

        if response.status_code in _RETRYABLE_STATUSES and not last_attempt:
            logger.warning(
                "Gemini vision HTTP %s (attempt %d/%d), retrying: %s",
                response.status_code,
                attempt,
                _MAX_ATTEMPTS,
                _upstream_error_summary(response),
            )
            time.sleep(_RETRY_BACKOFF_SECONDS)
            continue
        break

    assert response is not None  # the loop either set it or raised
    if response.status_code != 200:
        summary = _upstream_error_summary(response)
        logger.warning("Gemini vision HTTP %s: %s", response.status_code, summary)
        # A 400 whose status is INVALID_ARGUMENT means Gemini could not decode
        # or process the image itself. A bad key is also a 400, but carries
        # API_KEY_INVALID in the message and is an outage, not a photo problem.
        if (
            response.status_code == 400
            and summary.startswith("INVALID_ARGUMENT")
            and "api key" not in summary.lower()
        ):
            raise _GeminiRejectedInput(summary)
        raise _GeminiUnavailable(f"HTTP {response.status_code}")

    try:
        payload = response.json()
    except ValueError as exc:
        logger.warning("Gemini vision response was not valid JSON")
        raise _GeminiUnavailable("non-JSON response") from exc

    try:
        answer_parts = payload["candidates"][0]["content"]["parts"]
        # Skip "thought" parts emitted by thinking models; keep the answer.
        text = "".join(
            p.get("text", "") for p in answer_parts if not p.get("thought")
        )
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        # No candidate content: typically a safety block on the image.
        block = (payload.get("promptFeedback") or {}).get("blockReason")
        logger.warning(
            "Gemini vision returned no content (blockReason=%s)", block
        )
        raise _GeminiRejectedInput("no candidate content") from exc

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        logger.warning("Gemini vision returned non-JSON payload")
        raise _GeminiRejectedInput("non-JSON answer") from exc
    if not isinstance(data, dict):
        raise _GeminiRejectedInput("answer was not a JSON object")
    return data


def _call_gemini(
    settings: Settings,
    *,
    parts: list[dict[str, Any]],
    schema: dict[str, Any],
    temperature: float = 0.1,
) -> dict[str, Any] | None:
    """Non-raising wrapper around :func:`_request_gemini`.

    Returns ``None`` on any failure, for callers that treat the AI as a
    best-effort extra and fall through to a deterministic path.
    """
    try:
        return _request_gemini(
            settings, parts=parts, schema=schema, temperature=temperature
        )
    except (_GeminiUnavailable, _GeminiRejectedInput):
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
        "issue_detected": {"type": "boolean"},
        "retake_reason": {"type": "string"},
    },
    "required": [
        "category",
        "priority",
        "title",
        "description",
        "confidence",
        "spam_score",
        "is_spam",
        "issue_detected",
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
    "- issue_detected: true only when a specific, reportable public issue "
    "is clearly visible and identifiable in the photo. false when the photo "
    "is too dark, too blurry, too far away, obstructed, blank, or simply "
    "does not show any public infrastructure problem.\n"
    "- retake_reason: required when issue_detected is false; omit otherwise. "
    "One short, friendly sentence (<=140 chars) addressed to the citizen "
    "saying what is wrong with the photo and how to retake it (e.g. 'The "
    "photo is too dark to see the problem - retake it with more light.').\n"
    "Return JSON only; no prose."
)

_DEFAULT_RETAKE_REASON = (
    "We couldn't spot a clear public issue in this photo. Retake it closer "
    "to the problem, in good light, with the issue filling the frame."
)


def analyze_report_photo(image_bytes: bytes) -> VisionAutoFill:
    """Analyze a citizen photo.

    Raises :class:`VisionUnavailableError` when Gemini cannot be used at all
    and :class:`PhotoNotRecognizedError` when it could not read this photo.
    Check ``issue_detected`` on the result: ``False`` means the photo was
    understood but shows nothing reportable.
    """
    if not image_bytes:
        raise PhotoNotRecognizedError("empty image")
    settings = get_settings()
    if not settings.gemini_configured:
        raise VisionUnavailableError("GEMINI_API_KEY is not set")

    parts: list[dict[str, Any]] = [
        {"text": _AUTOFILL_PROMPT},
        _inline_image_part(image_bytes),
    ]
    try:
        data = _request_gemini(settings, parts=parts, schema=_AUTOFILL_SCHEMA)
    except _GeminiUnavailable as exc:
        raise VisionUnavailableError(str(exc)) from exc
    except _GeminiRejectedInput as exc:
        raise PhotoNotRecognizedError(str(exc)) from exc

    category = data.get("category")
    priority = data.get("priority")
    if category not in {c.value for c in ReportCategory}:
        raise PhotoNotRecognizedError("answer had no valid category")
    if priority not in {p.value for p in ReportPriority}:
        raise PhotoNotRecognizedError("answer had no valid priority")

    title = str(data.get("title", "")).strip()[:200]
    description = str(data.get("description", "")).strip()[:5000]
    if not title or not description:
        raise PhotoNotRecognizedError("answer had no title/description")

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

    # A photo only counts as "issue detected" when the model says so AND it
    # is not junk. Anything at or above the auto-reject score would be thrown
    # out at submission anyway, so stop the citizen here instead.
    issue_detected = (
        bool(data.get("issue_detected", True))
        and not is_spam
        and spam_score < settings.SPAM_AUTO_REJECT_SCORE
    )
    retake_reason: str | None = None
    if not issue_detected:
        raw_reason = data.get("retake_reason")
        if isinstance(raw_reason, str) and raw_reason.strip():
            retake_reason = raw_reason.strip()[:280]
        else:
            retake_reason = spam_reason or _DEFAULT_RETAKE_REASON

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
        issue_detected=issue_detected,
        retake_reason=retake_reason,
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
