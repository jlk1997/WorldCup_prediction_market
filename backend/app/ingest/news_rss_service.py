"""RSS news ingestion (English + Chinese feeds)."""

from __future__ import annotations

import html
import logging
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from urllib.parse import urlparse

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import cache_delete_prefix
from app.core.config import get_settings
from app.db.models import DataSyncLog, NewsArticle, Team
from app.ingest.news_tagging import extract_team_tags
from app.utils.news_text import clean_news_summary

logger = logging.getLogger(__name__)


def _strip_html(text: str) -> str:
    return clean_news_summary(text, max_len=500)


def _normalize_url(url: str) -> str:
    return html.unescape((url or "").strip())


def _source_from_url(feed_url: str) -> str:
    try:
        host = urlparse(feed_url).netloc or feed_url
        return host.replace("www.", "")
    except Exception:
        return feed_url


def _parse_rss_items(xml_text: str) -> list[dict]:
    items: list[dict] = []
    blocks = re.findall(r"<item>(.*?)</item>", xml_text, re.DOTALL | re.IGNORECASE)
    if not blocks:
        blocks = re.findall(r"<entry>(.*?)</entry>", xml_text, re.DOTALL | re.IGNORECASE)

    for block in blocks:
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.DOTALL)
        link = re.search(r"<link>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</link>", block, re.DOTALL)
        if not link:
            link = re.search(r'<link[^>]+href=["\']([^"\']+)["\']', block, re.DOTALL)
        desc = re.search(
            r"<description>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</description>", block, re.DOTALL
        )
        if not desc:
            desc = re.search(r"<summary>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</summary>", block, re.DOTALL)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", block, re.DOTALL)
        if not pub:
            pub = re.search(r"<updated>(.*?)</updated>", block, re.DOTALL)
        published_at = None
        if pub:
            raw = pub.group(1).strip()
            try:
                published_at = parsedate_to_datetime(raw)
            except Exception:
                try:
                    published_at = datetime.fromisoformat(raw.replace("Z", "+00:00"))
                except Exception:
                    published_at = None
        if published_at and published_at.tzinfo:
            published_at = published_at.astimezone(timezone.utc).replace(tzinfo=None)

        url = _normalize_url(link.group(1)) if link else ""
        if not url:
            guid = re.search(r"<guid[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</guid>", block, re.DOTALL)
            if guid:
                url = _normalize_url(guid.group(1))

        items.append(
            {
                "title": _strip_html(title.group(1)) if title else "",
                "url": url,
                "summary": _strip_html(desc.group(1))[:500] if desc else "",
                "published_at": published_at,
            }
        )
    return items


class NewsRssService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def sync(self) -> dict[str, int]:
        """Sync all configured feeds. Returns inserted count per lang."""
        cn_teams = list(self.db.scalars(select(Team.name)).all())
        inserted_en = self._sync_feeds(self.settings.news_rss_feed_list_en, "en", cn_teams)
        inserted_zh = self._sync_feeds(self.settings.news_rss_feed_list_zh, "zh", cn_teams)
        if inserted_en or inserted_zh:
            cache_delete_prefix("news:list:")
        if not inserted_en and not inserted_zh and not self.settings.news_rss_feed_list_zh:
            if not self.settings.news_rss_feed_list_en:
                self._log("rss", "skipped", 0, "NEWS_RSS_FEEDS_EN not configured")
        return {"en": inserted_en, "zh": inserted_zh, "total": inserted_en + inserted_zh}

    def _sync_feeds(self, feeds: list[str], lang: str, cn_team_names: list[str]) -> int:
        if not feeds:
            return 0

        inserted = 0
        seen_urls: set[str] = set()

        for feed_url in feeds:
            try:
                with httpx.Client(timeout=20.0, follow_redirects=True) as client:
                    resp = client.get(
                        feed_url,
                        headers={"User-Agent": "WC2026-NewsBot/1.0 (+https://github.com/wc2026)"},
                    )
                    resp.raise_for_status()
                    items = _parse_rss_items(resp.text)
            except Exception as exc:
                logger.warning("RSS fetch failed [%s] %s: %s", lang, feed_url, exc)
                continue

            source = _source_from_url(feed_url)
            for item in items:
                url = _normalize_url(item.get("url", ""))
                title = (item.get("title") or "").strip()
                if not url or not title or url in seen_urls:
                    continue

                exists = self.db.scalar(select(NewsArticle.id).where(NewsArticle.url == url))
                if exists:
                    seen_urls.add(url)
                    continue

                summary = item.get("summary") or ""
                tags = extract_team_tags(title, summary, lang, cn_team_names)
                try:
                    with self.db.begin_nested():
                        self.db.add(
                            NewsArticle(
                                title=title,
                                url=url,
                                source=source,
                                lang=lang,
                                published_at=item.get("published_at"),
                                summary=summary or None,
                                team_tags=tags or None,
                            )
                        )
                        self.db.flush()
                    inserted += 1
                    seen_urls.add(url)
                except IntegrityError:
                    logger.debug("Skip duplicate news url: %s", url)

        self.db.commit()
        self._log(f"rss_{lang}", "ok", inserted)
        return inserted

    def _log(self, source: str, status: str, records: int, error: str | None = None):
        self.db.add(DataSyncLog(source=source, status=status, records=records, error=error))
        self.db.commit()
