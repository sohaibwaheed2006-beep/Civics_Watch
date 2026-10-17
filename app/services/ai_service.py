"""AI-assisted classification: category + priority.

Primary path: Google Gemini (REST ``generateContent`` with a strict JSON
response schema). Fallback path: deterministic keyword rules. Report
submission MUST NEVER fail because the AI provider is slow, down or
misconfigured, so every network/parsing error here is swallowed and the
deterministic rules take over.

Behaviour
---------
* ``classify_report`` is the single entry point; it is cached per
  ``(title, description)`` pair so the two legacy helpers below share one
  provider call per report.
* ``suggest_category`` and ``suggest_priority`` keep their original
  signatures so callers (and the test suite) are unaffected.
* The AI's priority is preferred over the user-chosen category's default
  baseline, because the model reads the full text. Vote-count escalation is
  layered on top of whatever source produced the base priority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from app.core.config import Settings, get_settings
from app.core.enums import ReportCategory, ReportPriority
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "AiClassification",
    "CategorySuggestion",
    "classify_report",
    "clear_classification_cache",
    "suggest_category",
    "suggest_priority",
]


@dataclass(frozen=True, slots=True)
class CategorySuggestion:
    """Back-compat shape consumed by ``report_service.create_report``."""

    category: ReportCategory
    confidence: float
    source: str  # "ai" or "deterministic"


@dataclass(frozen=True, slots=True)
class AiClassification:
    """Full classification output from the primary or fallback path."""

    category: ReportCategory
    priority: ReportPriority
    confidence: float
    source: str  # "gemini" or "deterministic"


# ---------------------------------------------------------------------------
# Deterministic rules (fallback)
# ---------------------------------------------------------------------------
#: Keyword hints used by the deterministic classifier. Scored by match count.
_CATEGORY_KEYWORDS: dict[ReportCategory, tuple[str, ...]] = {
    ReportCategory.ROAD_DAMAGE: (
        "pothole", "road", "pavement", "crack", "asphalt", "sinkhole",
    ),
    ReportCategory.STREETLIGHT: (
        "light", "lamp", "street light", "streetlight", "bulb", "dark",
    ),
    ReportCategory.GARBAGE: (
        "garbage", "trash", "waste", "bin", "dump", "litter", "rubbish",
    ),
    ReportCategory.WATER_LEAK: (
        "water", "leak", "pipe", "burst", "hydrant", "mains",
    ),
    ReportCategory.DRAINAGE: (
        "drain", "sewer", "flood", "manhole", "gutter", "overflow",
    ),
    ReportCategory.PUBLIC_PROPERTY: (
        "bench", "vandal", "graffiti", "sign", "fence", "park",
    ),
}

#: Urgency boosters applied by the deterministic priority rule.
_URGENT_KEYWORDS = (
    "urgent", "danger", "dangerous", "injury", "injured", "emergency",
    "immediately", "severe", "broken main", "flooding", "fire", "gas",
)
_HIGH_KEYWORDS = (
    "unsafe", "hazard", "blocking", "blocked", "major", "large",
)

#: Categories whose default priority is elevated.
_CATEGORY_PRIORITY: dict[ReportCategory, ReportPriority] = {
    ReportCategory.WATER_LEAK: ReportPriority.HIGH,
    ReportCategory.DRAINAGE: ReportPriority.HIGH,
    ReportCategory.ROAD_DAMAGE: ReportPriority.MEDIUM,
    ReportCategory.STREETLIGHT: ReportPriority.MEDIUM,
    ReportCategory.GARBAGE: ReportPriority.LOW,
    ReportCategory.PUBLIC_PROPERTY: ReportPriority.LOW,
    ReportCategory.OTHER: ReportPriority.LOW,
}

_PRIORITY_ORDER = {
    ReportPriority.LOW: 0,
    ReportPriority.MEDIUM: 1,
    ReportPriority.HIGH: 2,
    ReportPriority.URGENT: 3,
}

_ALLOWED_CATEGORIES = {c.value for c in ReportCategory}
_ALLOWED_PRIORITIES = {p.value for p in ReportPriority}


def _max_priority(a: ReportPriority, b: ReportPriority) -> ReportPriority:
    return a if _PRIORITY_ORDER[a] >= _PRIORITY_ORDER[b] else b


def _deterministic_category(text: str) -> CategorySuggestion:
    """Score every category by keyword hits and return the top match."""
    lower = text.lower()
    scores: dict[ReportCategory, int] = {}
    for category, words in _CATEGORY_KEYWORDS.items():
        hits = sum(1 for w in words if w in lower)
        if hits:
            scores[category] = hits
    if not scores:
        return CategorySuggestion(
            category=ReportCategory.OTHER,
            confidence=0.3,
            source="deterministic",
        )
    best, hits = max(scores.items(), key=lambda item: item[1])
    confidence = min(0.3 + 0.2 * hits, 0.9)
    return CategorySuggestion(category=best, confidence=confidence, source="deterministic")


def _deterministic_priority(
    *, category: ReportCategory, text: str
) -> ReportPriority:
    """Baseline priority from category, escalated by urgent/high keywords."""
    lower = text.lower()
    base = _CATEGORY_PRIORITY.get(category, ReportPriority.LOW)
    if any(w in lower for w in _URGENT_KEYWORDS):
        return ReportPriority.URGENT
    if any(w in lower for w in _HIGH_KEYWORDS):
        return _max_priority(base, ReportPriority.HIGH)
    return base


# ---------------------------------------------------------------------------
# Gemini provider (primary)
# ---------------------------------------------------------------------------
_GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "{model}:generateContent"
)

_GEMINI_SYSTEM_PROMPT = (
    "You are an urban-services triage assistant for a city's public issue "
    "reporting system. Classify the citizen report into a category and a "
    "priority. Priority definitions:\n"
    "- urgent: immediate danger to people or property (gas leak, active "
    "flooding, exposed live wires, structural collapse, fire, injury).\n"
    "- high: significant hazard, blocked critical infrastructure, or any "
    "water/sewer failure (burst pipes, sewer overflow, large blocked road).\n"
    "- medium: noticeable degradation that needs timely repair (potholes, "
    "broken streetlights, sizeable garbage pile-ups).\n"
    "- low: cosmetic or minor inconvenience (graffiti, small litter, faded "
    "signs).\n"
    "Return STRICT JSON only. Do not include any prose."
)


def _gemini_request_body(title: str, description: str) -> dict[str, Any]:
    prompt = (
        f"{_GEMINI_SYSTEM_PROMPT}\n\n"
        f"Title: {title}\n"
        f"Description: {description}\n"
    )
    return {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.1,
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": sorted(_ALLOWED_CATEGORIES),
                    },
                    "priority": {
                        "type": "string",
                        "enum": sorted(_ALLOWED_PRIORITIES),
                    },
                    "confidence": {"type": "number"},
                },
                "required": ["category", "priority", "confidence"],
            },
        },
    }


def _parse_gemini_response(payload: dict[str, Any]) -> AiClassification | None:
    """Pull the structured JSON out of a Gemini generateContent response."""
    try:
        text = payload["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError):
        logger.warning("Gemini response missing expected shape")
        return None
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        logger.warning("Gemini returned non-JSON payload")
        return None

    category = parsed.get("category")
    priority = parsed.get("priority")
    if category not in _ALLOWED_CATEGORIES or priority not in _ALLOWED_PRIORITIES:
        logger.warning(
            "Gemini returned out-of-range values: category=%r priority=%r",
            category,
            priority,
        )
        return None
    try:
        confidence = float(parsed.get("confidence", 0.7))
    except (TypeError, ValueError):
        confidence = 0.7
    confidence = max(0.0, min(1.0, confidence))
    return AiClassification(
        category=ReportCategory(category),
        priority=ReportPriority(priority),
        confidence=confidence,
        source="gemini",
    )


def _call_gemini(
    settings: Settings, *, title: str, description: str
) -> AiClassification | None:
    """One Gemini REST call. Returns ``None`` on any failure.

    Imported locally so ``httpx`` is only touched when a key is actually set.
    """
    import httpx  # local import keeps module import cheap

    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    try:
        with httpx.Client(timeout=settings.AI_TIMEOUT_SECONDS) as client:
            # Key goes in the header, not ?key=, so httpx's DEBUG URL logs
            # don't leak it.
            response = client.post(
                url,
                headers={"x-goog-api-key": settings.GEMINI_API_KEY},
                json=_gemini_request_body(title, description),
            )
    except httpx.HTTPError as exc:
        logger.warning("Gemini request failed: %s", type(exc).__name__)
        return None

    if response.status_code != 200:
        # Body may contain the API error reason; log only the status to avoid
        # leaking the request parameters.
        logger.warning("Gemini HTTP %s", response.status_code)
        return None

    try:
        data = response.json()
    except ValueError:
        logger.warning("Gemini response was not valid JSON")
        return None
    return _parse_gemini_response(data)


# ---------------------------------------------------------------------------
# Cached classification
# ---------------------------------------------------------------------------
@lru_cache(maxsize=256)
def _classify_cached(title: str, description: str) -> AiClassification:
    """Classify once per unique input. Tries Gemini first; falls back."""
    text = f"{title}\n{description}".strip()
    settings = get_settings()

    if settings.gemini_configured:
        try:
            result = _call_gemini(settings, title=title, description=description)
            if result is not None:
                logger.info(
                    "Gemini classified: category=%s priority=%s confidence=%.2f",
                    result.category.value,
                    result.priority.value,
                    result.confidence,
                )
                return result
        except Exception as exc:  # noqa: BLE001 - sanitised log, no re-raise
            logger.warning("Gemini call raised: %s", type(exc).__name__)

    # Deterministic fallback.
    cat_sug = _deterministic_category(text) if text else None
    category = cat_sug.category if cat_sug else ReportCategory.OTHER
    priority = _deterministic_priority(category=category, text=text)
    confidence = cat_sug.confidence if cat_sug else 0.3
    return AiClassification(
        category=category,
        priority=priority,
        confidence=confidence,
        source="deterministic",
    )


def classify_report(title: str, description: str) -> AiClassification:
    """Public entry point. Always returns a classification."""
    return _classify_cached(title or "", description or "")


def clear_classification_cache() -> None:
    """Drop the in-process classification cache. Useful for tests and
    long-lived workers that want to pick up a new API key without restart."""
    _classify_cached.cache_clear()


# ---------------------------------------------------------------------------
# Back-compat public helpers used by report_service and existing tests
# ---------------------------------------------------------------------------
def suggest_category(
    title: str, description: str
) -> CategorySuggestion | None:
    """Return a category suggestion, or ``None`` when the input is empty."""
    text = f"{title}\n{description}".strip()
    if not text:
        return None
    classification = _classify_cached(title, description)
    return CategorySuggestion(
        category=classification.category,
        confidence=classification.confidence,
        source="ai" if classification.source == "gemini" else "deterministic",
    )


def suggest_priority(
    *,
    category: ReportCategory,
    title: str,
    description: str,
    vote_count: int = 0,
) -> ReportPriority:
    """AI-first priority. Vote-count escalation is layered on the base.

    When Gemini is unavailable or returns something invalid, the deterministic
    rule (per-category baseline + urgent/high keywords) decides. In both
    cases, enough votes can push the final value up but never pull it down.
    """
    text = f"{title}\n{description}".strip()
    if text:
        classification = _classify_cached(title, description)
    else:
        classification = None

    if classification is not None and classification.source == "gemini":
        base = classification.priority
    else:
        base = _deterministic_priority(category=category, text=text)

    if vote_count >= 10:
        return _max_priority(base, ReportPriority.HIGH)
    if vote_count >= 3:
        return _max_priority(base, ReportPriority.MEDIUM)
    return base
