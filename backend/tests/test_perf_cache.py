"""Performance cache helpers for today-home and market surfaces."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.core.cache import cache_delete, cache_get, cache_set
from app.core.user_surface_cache import (
    LIVE_MINTS_TTL,
    TODAY_HOME_TTL,
    daily_status_key,
    today_home_key,
)
from app.db.models.commerce import User
from app.db.session import SessionLocal
from app.services.today_home_service import LIVE_MINTS_CACHE_KEY, TodayHomeService


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_today_home_service_uses_cache(db: Session, monkeypatch):
    suffix = uuid.uuid4().hex[:8]
    user = User(email=f"th_{suffix}@test.com", nickname=f"th_{suffix}")
    db.add(user)
    db.commit()

    from app.services.game_service import GameService

    calls = {"n": 0}
    original_daily = GameService.get_daily_status

    def counting_daily(self, user):
        calls["n"] += 1
        return original_daily(self, user)

    monkeypatch.setattr(GameService, "get_daily_status", counting_daily)
    cache_delete(today_home_key(user.id))

    svc = TodayHomeService(db)
    first = svc.build(user)
    second = svc.build(user)
    assert calls["n"] == 1
    assert second == first


def test_daily_status_cache_roundtrip():
    uid = 999_001
    cache_delete(daily_status_key(uid))
    payload = {"match_day": True, "signed_today": False}
    cache_set(daily_status_key(uid), payload, ttl=15)
    assert cache_get(daily_status_key(uid)) == payload
    cache_delete(daily_status_key(uid))


def test_live_mints_cache_key_constant():
    assert LIVE_MINTS_CACHE_KEY
    assert TODAY_HOME_TTL > 0
    assert LIVE_MINTS_TTL > 0
