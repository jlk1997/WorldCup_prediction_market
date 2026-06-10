"""Tests for AI inflight lock acquisition."""

from unittest.mock import patch

import pytest

from app.core.exceptions import ServiceUnavailableError
from app.services.ai_inflight import acquire_inflight_or_wait, mark_inflight_failed, release_inflight


def test_acquire_returns_token_for_leader():
    with patch("app.services.ai_inflight.try_acquire_lock", return_value="tok-1"):
        result = acquire_inflight_or_wait("k", lambda: None, timeout_sec=5)
    assert result.token == "tok-1"
    assert result.cached is None


def test_acquire_returns_cache_for_follower():
    cache = {"status": "success", "cached": True}
    calls = {"n": 0}

    def wait():
        calls["n"] += 1
        return cache if calls["n"] >= 1 else None

    with patch("app.services.ai_inflight.try_acquire_lock", return_value=None), patch(
        "app.services.ai_inflight.time.sleep"
    ):
        result = acquire_inflight_or_wait("k", wait, timeout_sec=5)
    assert result.cached == cache
    assert result.token is None


def test_follower_becomes_leader_gets_token():
    calls = {"n": 0}

    def lock_side_effect(key, ttl_sec=300):
        calls["n"] += 1
        return "tok-leader" if calls["n"] >= 2 else None

    with patch("app.services.ai_inflight.try_acquire_lock", side_effect=lock_side_effect), patch(
        "app.services.ai_inflight.time.sleep"
    ):
        result = acquire_inflight_or_wait("k", lambda: None, timeout_sec=10)
    assert result.token == "tok-leader"


def test_failed_marker_stops_wait():
    mark_inflight_failed("k-test-fail")
    with patch("app.services.ai_inflight.try_acquire_lock", return_value=None):
        with pytest.raises(ServiceUnavailableError, match="失败"):
            acquire_inflight_or_wait("k-test-fail", lambda: None, timeout_sec=5)



def test_release_inflight_delegates():
    with patch("app.services.ai_inflight.release_lock") as release:
        release_inflight("k", "tok")
    release.assert_called_once_with("k", "tok")
