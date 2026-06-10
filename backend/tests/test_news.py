"""Tests for news personalization and tagging."""

from datetime import datetime, timedelta

from app.ingest.news_tagging import extract_team_tags
from app.services.news_service import NewsService


def test_extract_tags_english():
    tags = extract_team_tags(
        "Argentina beat Brazil in friendly",
        "Messi scored",
        "en",
        ["阿根廷", "巴西", "法国"],
    )
    assert "阿根廷" in tags
    assert "巴西" in tags


def test_extract_tags_chinese():
    tags = extract_team_tags(
        "国足备战世界杯，潘帕斯雄鹰状态火热",
        "",
        "zh",
        ["中国", "阿根廷", "法国"],
    )
    assert "中国" in tags
    assert "阿根廷" in tags


def test_news_list_lang_filter(client):
    en = client.get("/api/news?lang=en&limit=5&personalize=false")
    assert en.status_code in (200, 503)
    if en.status_code == 200:
        for row in en.json():
            assert row.get("lang", "en") == "en"


def test_news_stats(client):
    resp = client.get("/api/news/stats")
    assert resp.status_code in (200, 503)
    if resp.status_code == 200:
        body = resp.json()
        assert "en" in body
        assert "zh" in body


def test_sort_by_teams():
    from types import SimpleNamespace

    from app.db.repositories.match_repository import NewsRepository

    now = datetime.utcnow()
    items = [
        SimpleNamespace(
            id=1,
            team_tags=["法国"],
            published_at=now - timedelta(days=10),
            created_at=None,
        ),
        SimpleNamespace(
            id=2,
            team_tags=["阿根廷"],
            published_at=now - timedelta(days=1),
            created_at=None,
        ),
        SimpleNamespace(id=3, team_tags=None, published_at=now, created_at=None),
    ]
    sorted_items = NewsRepository._sort_by_teams(items, ("阿根廷", "法国"))
    assert sorted_items[0].id == 3
    assert sorted_items[1].id == 2
    assert sorted_items[2].id == 1


def test_sort_by_teams_recency_over_old_favorite():
    from types import SimpleNamespace

    from app.db.repositories.match_repository import NewsRepository

    now = datetime.utcnow()
    items = [
        SimpleNamespace(
            id=1,
            team_tags=["阿根廷"],
            published_at=now - timedelta(days=20),
            created_at=None,
        ),
        SimpleNamespace(
            id=2,
            team_tags=None,
            published_at=now - timedelta(hours=2),
            created_at=None,
        ),
    ]
    sorted_items = NewsRepository._sort_by_teams(items, ("阿根廷",))
    assert sorted_items[0].id == 2
