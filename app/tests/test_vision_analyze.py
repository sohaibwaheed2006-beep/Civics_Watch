"""Photo-analysis endpoint: the wizard must be able to tell apart
"issue detected", "retake the photo" and "AI service is down".

Gemini is never called here; the transport (``_request_gemini``) is patched.
"""

from __future__ import annotations

import base64

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.services import vision_service

# A valid 1x1 PNG, enough to pass upload validation.
_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGA"
    "WjR9awAAAABJRU5ErkJggg=="
)

_GOOD_ANSWER = {
    "category": "road_damage",
    "priority": "medium",
    "title": "Deep pothole on travel lane",
    "description": "Approx. 12-inch pothole with cracked asphalt around it.",
    "confidence": 0.93,
    "spam_score": 0.05,
    "is_spam": False,
    "issue_detected": True,
}


@pytest.fixture
def gemini_key(monkeypatch: pytest.MonkeyPatch):
    """Pretend a Gemini key is configured for the duration of one test."""
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    get_settings.cache_clear()
    yield
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()


def _analyze(client: TestClient, api_prefix: str, headers: dict[str, str]):
    return client.post(
        f"{api_prefix}/ai/vision/analyze",
        headers=headers,
        files={"file": ("photo.png", _PNG, "image/png")},
    )


def _patch_answer(monkeypatch: pytest.MonkeyPatch, answer=None, raises=None):
    def _fake(settings, *, parts, schema, temperature=0.1):
        if raises is not None:
            raise raises
        return dict(answer)

    monkeypatch.setattr(vision_service, "_request_gemini", _fake)


class TestVisionAnalyze:
    def test_detected_issue_prefills_the_form(
        self, client, api_prefix, auth_headers, gemini_key, monkeypatch
    ) -> None:
        _patch_answer(monkeypatch, _GOOD_ANSWER)
        response = _analyze(client, api_prefix, auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["issue_detected"] is True
        assert body["retake_reason"] is None
        assert body["category"] == "road_damage"

    def test_readable_photo_without_issue_asks_for_retake(
        self, client, api_prefix, auth_headers, gemini_key, monkeypatch
    ) -> None:
        _patch_answer(
            monkeypatch,
            {
                **_GOOD_ANSWER,
                "category": "other",
                "issue_detected": False,
                "retake_reason": "Too dark to see the problem - add light.",
            },
        )
        response = _analyze(client, api_prefix, auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["issue_detected"] is False
        assert body["retake_reason"] == "Too dark to see the problem - add light."

    def test_spam_verdict_counts_as_not_detected(
        self, client, api_prefix, auth_headers, gemini_key, monkeypatch
    ) -> None:
        # Model forgot to clear issue_detected, but flagged the photo as junk.
        _patch_answer(
            monkeypatch,
            {
                **_GOOD_ANSWER,
                "spam_score": 0.95,
                "is_spam": True,
                "spam_reason": "This is a selfie, not a public issue.",
            },
        )
        body = _analyze(client, api_prefix, auth_headers).json()
        assert body["issue_detected"] is False
        assert body["retake_reason"] == "This is a selfie, not a public issue."

    def test_unreadable_photo_is_422_retake(
        self, client, api_prefix, auth_headers, gemini_key, monkeypatch
    ) -> None:
        _patch_answer(
            monkeypatch, raises=vision_service._GeminiRejectedInput("bad image")
        )
        response = _analyze(client, api_prefix, auth_headers)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "photo_not_recognized"

    def test_malformed_answer_is_422_retake(
        self, client, api_prefix, auth_headers, gemini_key, monkeypatch
    ) -> None:
        _patch_answer(monkeypatch, {**_GOOD_ANSWER, "category": "not-a-category"})
        response = _analyze(client, api_prefix, auth_headers)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "photo_not_recognized"

    def test_provider_outage_is_503_not_a_photo_problem(
        self, client, api_prefix, auth_headers, gemini_key, monkeypatch
    ) -> None:
        _patch_answer(
            monkeypatch, raises=vision_service._GeminiUnavailable("HTTP 503")
        )
        response = _analyze(client, api_prefix, auth_headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "vision_unavailable"

    def test_missing_api_key_is_503(
        self, client, api_prefix, auth_headers
    ) -> None:
        # conftest pins GEMINI_API_KEY="" - no key, no analysis.
        response = _analyze(client, api_prefix, auth_headers)
        assert response.status_code == 503
        assert response.json()["error"]["code"] == "vision_unavailable"

    def test_requires_authentication(self, client, api_prefix) -> None:
        response = client.post(
            f"{api_prefix}/ai/vision/analyze",
            files={"file": ("photo.png", _PNG, "image/png")},
        )
        assert response.status_code == 401
