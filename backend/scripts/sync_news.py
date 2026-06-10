"""One-shot news RSS sync with a readable summary (for ops)."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import func, select

from app.core.config import get_settings
from app.db.models import NewsArticle
from app.db.session import SessionLocal
from app.ingest.news_rss_service import NewsRssService
from app.services.news_service import NewsService


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync football news from RSS feeds")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable debug logging")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    settings = get_settings()
    db = SessionLocal()
    try:
        print("=== News sync ===")
        print(f"EN feeds ({len(settings.news_rss_feed_list_en)}):")
        for url in settings.news_rss_feed_list_en:
            print(f"  - {url}")
        print(f"ZH feeds ({len(settings.news_rss_feed_list_zh)}):")
        for url in settings.news_rss_feed_list_zh:
            print(f"  - {url}")
        print(
            f"Limits: list={settings.news_max_age_days}d "
            f"ingest={settings.news_ingest_max_age_days}d "
            f"retention={settings.news_retention_days}d"
        )

        before = db.scalar(select(func.count(NewsArticle.id))) or 0
        result = NewsRssService(db).sync()
        after = db.scalar(select(func.count(NewsArticle.id))) or 0
        visible = NewsService(db).lang_stats()

        print("\n=== Result ===")
        print(f"Inserted EN : {result.get('en', 0)}")
        print(f"Inserted ZH : {result.get('zh', 0)}")
        print(f"Pruned      : {result.get('pruned', 0)}")
        print(f"Scrubbed    : {result.get('scrubbed', 0)}")
        print(f"DB total    : {before} -> {after}")
        print(f"Visible 30d : zh={visible['zh']} en={visible['en']} total={visible['total']}")

        recent = NewsService(db).list_articles(
            lang="zh", limit=3, team=None, user=None, personalize=False
        )
        if recent:
            print("\nLatest visible (zh):")
            for row in recent:
                print(f"  · [{row.get('published_at')}] {row.get('title')}")
        else:
            print("\nNo visible Chinese articles in the last 30 days.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
