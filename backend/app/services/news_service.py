"""News listing with optional user-team prioritization and short TTL cache."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.core.cache import cache_get, cache_set
from app.db.models import Team
from app.db.models.commerce import User
from app.db.repositories.match_repository import NewsRepository
from app.utils.news_text import clean_news_summary, extract_news_thumbnail

NEWS_LIST_CACHE_TTL = 60
NEWS_FETCH_CAP = 100


class NewsService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = NewsRepository(db)

    def list_articles(
        self,
        *,
        lang: str | None,
        limit: int,
        team: str | None,
        user: User | None,
        personalize: bool,
    ) -> list[dict]:
        prioritize = self._prioritize_teams(user) if personalize and not team else ()
        cache_key = self._cache_key(lang, limit, team, prioritize, personalize and bool(user))

        cached = cache_get(cache_key)
        if cached is not None:
            return cached

        rows = self.repo.list_recent(
            limit=limit,
            team=team,
            lang=lang,
            prioritize=prioritize or None,
            fetch_cap=NEWS_FETCH_CAP,
        )
        main, sub = (prioritize[0], prioritize[1]) if len(prioritize) >= 2 else (
            (prioritize[0], None) if prioritize else (None, None)
        )
        out = [
            {
                "id": a.id,
                "title": a.title,
                "url": a.url,
                "source": a.source,
                "published_at": a.published_at,
                "summary": clean_news_summary(a.summary) or None,
                "thumbnail_url": extract_news_thumbnail(a.summary),
                "lang": a.lang,
                "team_tags": a.team_tags,
                "for_my_team": bool(main and a.team_tags and main in a.team_tags),
                "for_sub_team": bool(sub and a.team_tags and sub in a.team_tags),
            }
            for a in rows
        ]
        cache_set(cache_key, out, NEWS_LIST_CACHE_TTL)
        return out

    def _prioritize_teams(self, user: User | None) -> tuple[str, ...]:
        if not user:
            return ()
        names: list[str] = []
        if user.favorite_team_id:
            t = self.db.get(Team, user.favorite_team_id)
            if t and t.name:
                names.append(t.name)
        if user.secondary_team_id and user.secondary_team_id != user.favorite_team_id:
            t = self.db.get(Team, user.secondary_team_id)
            if t and t.name and t.name not in names:
                names.append(t.name)
        return tuple(names)

    @staticmethod
    def _cache_key(
        lang: str | None,
        limit: int,
        team: str | None,
        prioritize: tuple[str, ...],
        personalized: bool,
    ) -> str:
        lang_key = lang or "all"
        team_key = team or "-"
        pri_key = "|".join(prioritize) if prioritize else "-"
        return f"news:list:{lang_key}:{limit}:{team_key}:{pri_key}:p{int(personalized)}"
