"""Tests for football relevance filtering."""

from datetime import datetime, timedelta

from app.ingest.news_relevance import is_football_relevant


def test_rejects_basketball_zh():
    assert not is_football_relevant("湖人击败凯尔特人", "NBA总决赛精彩回顾", "zh")


def test_accepts_football_zh():
    assert is_football_relevant("国足世预赛主场取胜", "武磊破门", "zh")


def test_accepts_team_tag_without_keyword():
    assert is_football_relevant("国家队最新动态", "训练备战", "zh", team_tags=["阿根廷"])


def test_rejects_tennis_en():
    assert not is_football_relevant("Wimbledon final set", "tennis championship", "en")


def test_accepts_football_en():
    assert is_football_relevant("Argentina win World Cup qualifier", "Messi scores", "en")
