"""Tests for public share HTML pages."""

import uuid

import pytest
from sqlalchemy.orm import Session

from app.db.models.commerce import User
from app.db.session import SessionLocal


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def test_invite_share_page_default(client):
    r = client.get("/share/invite")
    assert r.status_code == 200
    assert "text/html" in r.headers.get("content-type", "")
    assert "最后一舞" in r.text
    assert 'og:title' in r.text


def test_invite_share_page_with_valid_ref(client, db: Session):
    suffix = uuid.uuid4().hex[:8]
    code = f"S{suffix[:7].upper()}"
    user = User(email=f"share_{suffix}@test.com", nickname="分享测试", fan_coins=0, invite_code=code)
    db.add(user)
    db.commit()

    r = client.get(f"/share/invite?ref={code}")
    assert r.status_code == 200
    assert "分享测试" in r.text
    assert f"ref={code}" in r.text
