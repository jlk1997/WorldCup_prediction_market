"""Tests for platform AI token budget reserve/release."""

from unittest.mock import patch

import pytest

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError
from app.services.ai_token_budget import (
    ESTIMATED_TOKENS_PER_ANALYZE,
    AiTokenBudgetService,
    _fallback_reserved,
)


@pytest.fixture(autouse=True)
def _clear_fallback():
    _fallback_reserved.clear()
    yield
    _fallback_reserved.clear()


def test_fallback_reserve_serializes_without_redis():
    settings = get_settings()
    budget = settings.ai_daily_token_budget
    svc = AiTokenBudgetService(None)

    with patch("app.services.ai_token_budget._redis_incr", return_value=None), patch(
        "app.services.ai_token_budget._redis_get", return_value=None
    ), patch.object(settings, "ai_daily_token_budget", budget):
        svc.reserve(ESTIMATED_TOKENS_PER_ANALYZE)
        svc.reserve(ESTIMATED_TOKENS_PER_ANALYZE)
        with pytest.raises(ServiceUnavailableError, match="算力"):
            svc.reserve(budget)


def test_fallback_release_frees_capacity():
    svc = AiTokenBudgetService(None)
    with patch("app.services.ai_token_budget._redis_incr", return_value=None), patch(
        "app.services.ai_token_budget._redis_get", return_value=None
    ):
        svc.reserve(ESTIMATED_TOKENS_PER_ANALYZE)
        svc.release_reserved(ESTIMATED_TOKENS_PER_ANALYZE)
        svc.reserve(ESTIMATED_TOKENS_PER_ANALYZE)


def test_redis_over_budget_rolls_back():
    settings = get_settings()
    svc = AiTokenBudgetService(None)
    calls: list[int] = []

    def fake_incr(key, delta, ttl=86400 * 2):
        calls.append(delta)
        return settings.ai_daily_token_budget + 1

    with patch("app.services.ai_token_budget._redis_incr", side_effect=fake_incr), patch(
        "app.services.ai_token_budget._redis_get", return_value=0
    ):
        with pytest.raises(ServiceUnavailableError, match="算力"):
            svc.reserve(ESTIMATED_TOKENS_PER_ANALYZE)
    assert calls == [ESTIMATED_TOKENS_PER_ANALYZE, -ESTIMATED_TOKENS_PER_ANALYZE]
