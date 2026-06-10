"""Rate limit tests."""

import pytest
from fastapi.testclient import TestClient

from app.core.exceptions import BadRequestError
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
    with pytest.raises(BadRequestError):
        check_rate_limit("rl:test:key", limit=3, window_sec=60)


def test_send_code_email_cooldown():
    rate_limit_send_code("a@example.com")
    with pytest.raises(BadRequestError):
        rate_limit_send_code("a@example.com")


def test_send_code_ip_limit():
    for i in range(10):
        rate_limit_send_code(f"user{i}@example.com", ip="1.2.3.4")
    with pytest.raises(BadRequestError):
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
    with pytest.raises(BadRequestError):
        rate_limit_agent(req, user_id=42)
