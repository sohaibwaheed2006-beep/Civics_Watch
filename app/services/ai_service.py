"""AI-assisted suggestion service with safe deterministic fallback.

AI integration is optional. When ``AI_ENABLED`` is false, or any provider call
fails, the deterministic rules below take over. The service NEVER raises:
every exception is caught and a fallback is returned so a provider outage does
not break report submission.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings
from app.core.enums import ReportCategory, ReportPriority
from app.core.logging import get_logger

logger = get_logger(__name__)

__all__ = [
    "CategorySuggestion",
    "suggest_category",
    "suggest_priority",
]


@dataclass(frozen=True, slots=True)
class CategorySuggestion:
    category: ReportCategory
    confidence: float
    source: str  # "ai" or "deterministic"


#: Keyword hints used by the deterministic classifier. Scored by match count.
_CATEGORY_KEYWORDS: dict[ReportCategory, tuple[str, ...]] = {
    ReportCategory.ROAD_DAMAGE: (
        "pothole",
        "road",
        "pavement",
        "crack",
        "asphalt",
        "sinkhole",
    ),
    ReportCategory.STREETLIGHT: (
        "light",
        "lamp",
        "street light",
        "streetlight",
        "bulb",
        "dark",
    ),
    ReportCategory.GARBAGE: (
        "garbage",
        "trash",
        "waste",
        "bin",
        "dump",
        "litter",
        "rubbish",
    ),
    ReportCategory.WATER_LEAK: (
        "water",
        "leak",
        "pipe",
        "burst",
        "hydrant",
        "mains",
    ),
    ReportCategory.DRAINAGE: (
        "drain",
        "sewer",
        "flood",
        "manhole",
        "gutter",
        "overflow",
    ),
    ReportCategory.PUBLIC_PROPERTY: (
        "bench",
        "vandal",
        "graffiti",
        "sign",
        "fence",
        "park",
    ),
}


#: Urgency boosters applied by the deterministic priority rule.
_URGENT_KEYWORDS = (
    "urgent",
    "danger",
    "dangerous",
    "injury",
    "injured",
    "emergency",
    "immediately",
    "severe",
    "broken main",
    "flooding",
    "fire",
    "gas",
)
_HIGH_KEYWORDS = (
    "unsafe",
    "hazard",
    "blocking",
    "blocked",
    "major",
    "large",
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
    # Confidence saturates at ~0.9 - a keyword match is not proof.
    confidence = min(0.3 + 0.2 * hits, 0.9)
    return CategorySuggestion(
        category=best, confidence=confidence, source="deterministic"
    )


def suggest_category(
    title: str, description: str
) -> CategorySuggestion | None:
    """Return a category suggestion, or ``None`` when neither path can.

    When AI is enabled, calls the provider inside ``try``; on any failure logs
    a sanitised warning and falls through to the deterministic classifier.
    """
    text = f"{title}\n{description}".strip()
    if not text:
        return None

    settings = get_settings()
    if settings.AI_ENABLED and settings.AI_API_KEY:
        try:
            # Placeholder: the real integration lives behind a provider adapter
            # that must be built and configured in deployment. We never raise;
            # instead we fall through to deterministic when the provider is
            # unreachable or returns something unsafe.
            return _deterministic_category(text)
        except Exception as exc:  # noqa: BLE001 - sanitised log, no re-raise
            logger.warning(
                "AI category suggestion failed: %s", type(exc).__name__
            )
    return _deterministic_category(text)


def suggest_priority(
    *,
    category: ReportCategory,
    title: str,
    description: str,
    vote_count: int = 0,
) -> ReportPriority:
    """Deterministic, explainable priority rule.

    Baseline is per-category; urgent/high keywords and vote counts can escalate.
    """
    text = f"{title}\n{description}".lower()
    base = _CATEGORY_PRIORITY.get(category, ReportPriority.LOW)

    if any(w in text for w in _URGENT_KEYWORDS):
        return ReportPriority.URGENT
    if any(w in text for w in _HIGH_KEYWORDS):
        return _max_priority(base, ReportPriority.HIGH)

    if vote_count >= 10:
        return _max_priority(base, ReportPriority.HIGH)
    if vote_count >= 3:
        return _max_priority(base, ReportPriority.MEDIUM)
    return base


_PRIORITY_ORDER = {
    ReportPriority.LOW: 0,
    ReportPriority.MEDIUM: 1,
    ReportPriority.HIGH: 2,
    ReportPriority.URGENT: 3,
}


def _max_priority(a: ReportPriority, b: ReportPriority) -> ReportPriority:
    return a if _PRIORITY_ORDER[a] >= _PRIORITY_ORDER[b] else b
