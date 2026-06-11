"""Rate limit tests."""

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import RateLimitError
from app.core.rate_limit import check_rate_limit, rate_limit_send_code, reset_rate_limit_memory
from app.main import app


@pytest.fixture(autouse=True)
def clear_limits():
    reset_rate_limit_memory()
    yield
    reset_rate_limit_memory()


def test_check_rate_limit_blocks_over_limit():
    for _ in range(3):
        check_rate_limit("rl:test:key", limit=3, window_sec=60)
    with pytest.raises(RateLimitError) as exc_info:
        check_rate_limit("rl:test:key", limit=3, window_sec=60)
    assert exc_info.value.status_code == 429
    assert exc_info.value.retry_after_sec == 60


def test_send_code_email_cooldown():
    rate_limit_send_code("a@example.com")
    with pytest.raises(RateLimitError):
        rate_limit_send_code("a@example.com")


def test_send_code_ip_limit():
    for i in range(10):
        rate_limit_send_code(f"user{i}@example.com", ip="1.2.3.4")
    with pytest.raises(RateLimitError):
        rate_limit_send_code("extra@example.com", ip="1.2.3.4")


def test_send_code_requires_age_confirmed(client):
    resp = client.post("/api/auth/send-code", json={"email": "test@example.com", "age_confirmed": False})
    assert resp.status_code == 400


def test_rate_limit_agent_user():
    from unittest.mock import MagicMock

    from app.core.rate_limit import rate_limit_agent

    req = MagicMock()
    req.headers = {}
    req.client = MagicMock(host="127.0.0.1")
    for _ in range(10):
        rate_limit_agent(req, user_id=42)
    with pytest.raises(RateLimitError):
        rate_limit_agent(req, user_id=42)


def test_rate_limit_error_json_shape():
    exc = RateLimitError("访问有点快了，请稍等片刻再试", retry_after_sec=45)
    from app.core.exceptions import rate_limit_error_body

    body = rate_limit_error_body(exc)
    assert body["code"] == "RATE_LIMIT"
    assert body["message"] == "访问有点快了，请稍等片刻再试"
    assert body["retry_after_sec"] == 45


def test_client_ip_websocket_uses_forwarded_for(monkeypatch):
    from unittest.mock import MagicMock

    from app.core.config import get_settings
    from app.core.rate_limit import client_ip_websocket

    settings = get_settings()
    monkeypatch.setattr(settings, "trusted_proxy_count", 1)

    ws = MagicMock()
    ws.headers = {"x-forwarded-for": "203.0.113.10, 127.0.0.1", "x-real-ip": "203.0.113.10"}
    ws.client = MagicMock(host="127.0.0.1")
    assert client_ip_websocket(ws) == "203.0.113.10"
