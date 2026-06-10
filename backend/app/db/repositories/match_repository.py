from datetime import datetime

from sqlalchemy import desc, or_, select
from sqlalchemy.orm import Session

from app.db.models import DataSyncLog, Match, NewsArticle
from app.utils.team_names import canonical_team_name


class MatchRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_schedule(self, limit: int | None = None) -> list[Match]:
        # 正式赛程由 expand_schedule 写入，日期格式为「2026年06月12日」
        stmt = (
            select(Match)
            .where(Match.match_date.like("%年%月%日%"))
            .order_by(Match.match_date, Match.match_time, Match.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, match_id: int) -> Match | None:
        return self.db.get(Match, match_id)

    def list_live(self) -> list[Match]:
        stmt = select(Match).where(Match.status.in_(["live"])).order_by(Match.id)
        return list(self.db.scalars(stmt).all())

    def list_for_team(self, team_name: str, limit: int = 10) -> list[Match]:
        canonical = canonical_team_name(team_name)
        stmt = (
            select(Match)
            .where(
                or_(
                    Match.team1_name == canonical,
                    Match.team2_name == canonical,
                    Match.team1_name == team_name,
                    Match.team2_name == team_name,
                )
            )
            .order_by(desc(Match.id))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def list_knockout_bracket(self) -> dict[str, list[Match]]:
        stmt = (
            select(Match)
            .where(Match.round_type == "knockout")
            .order_by(Match.bracket_round, Match.bracket_order, Match.id)
        )
        matches = list(self.db.scalars(stmt).all())
        rounds: dict[str, list[Match]] = {}
        for m in matches:
            key = m.bracket_round or "unknown"
            rounds.setdefault(key, []).append(m)
        return rounds

    def list_by_status(self, limit: int = 512) -> dict[str, list[Match]]:
        matches = self.list_schedule(limit=limit)
        grouped: dict[str, list[Match]] = {"live": [], "scheduled": [], "finished": [], "postponed": []}
        for m in matches:
            key = m.status or "scheduled"
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(m)
        return grouped


class NewsRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_recent(
        self,
        limit: int = 50,
        team: str | None = None,
        lang: str | None = None,
        prioritize: tuple[str, ...] | None = None,
        fetch_cap: int = 100,
    ) -> list[NewsArticle]:
        stmt = select(NewsArticle).order_by(
            desc(NewsArticle.published_at), desc(NewsArticle.id)
        )
        if lang and lang != "all":
            stmt = stmt.where(NewsArticle.lang == lang)

        if team:
            stmt = stmt.where(NewsArticle.team_tags.contains([team]))
            stmt = stmt.limit(limit)
            return list(self.db.scalars(stmt).all())

        if prioritize:
            cap = min(fetch_cap, max(limit * 3, 60))
            stmt = stmt.limit(cap)
            items = list(self.db.scalars(stmt).all())
            return self._sort_by_teams(items, prioritize)[:limit]

        stmt = stmt.limit(limit)
        return list(self.db.scalars(stmt).all())

    @staticmethod
    def _sort_by_teams(items: list[NewsArticle], prioritize: tuple[str, ...]) -> list[NewsArticle]:
        def score(article: NewsArticle) -> int:
            tags = article.team_tags or []
            best = 0
            for i, name in enumerate(prioritize):
                if name in tags:
                    best = max(best, len(prioritize) - i)
            return best

        def sort_key(article: NewsArticle) -> tuple:
            pub = article.published_at.timestamp() if article.published_at else 0
            return (-score(article), -pub, -article.id)

        return sorted(items, key=sort_key)


class SyncLogRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_recent(self, limit: int = 20) -> list[DataSyncLog]:
        stmt = select(DataSyncLog).order_by(desc(DataSyncLog.ran_at)).limit(limit)
        return list(self.db.scalars(stmt).all())
