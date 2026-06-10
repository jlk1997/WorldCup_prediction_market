"""Agent tools backed by DB and ingest services."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Match, NewsArticle, PlayerDetailed, Team
from app.db.repositories.match_repository import NewsRepository
from app.ingest.bsd_client import BsdClient, load_team_bsd_mapping
from app.utils.team_names import canonical_team_name


class AgentTools:
    def __init__(self, db: Session):
        self.db = db

    def get_team_profile(self, name: str) -> dict:
        canonical = canonical_team_name(name)
        team = self.db.scalar(
            select(Team).options(selectinload(Team.players_detailed)).where(Team.name == canonical)
        ) or self.db.scalar(
            select(Team).options(selectinload(Team.players_detailed)).where(Team.name == name)
        )
        if not team:
            return {"error": f"球队 {name} 未找到"}
        players = sorted(
            [p for p in (team.players_detailed or []) if p.position != "教练"],
            key=lambda p: p.overall_rating or 0,
            reverse=True,
        )[:8]
        return {
            "name": team.name,
            "fifa_ranking": team.fifa_ranking,
            "coach": team.coach,
            "formation": team.formation,
            "total_value": team.total_value,
            "avg_age": float(team.avg_age) if team.avg_age else None,
            "key_players": [
                {
                    "name": p.name,
                    "position": p.position,
                    "rating": p.overall_rating,
                    "stats": p.stats,
                    "is_starter": p.is_starter,
                }
                for p in players
            ],
        }

    def get_injury_report(self, team_name: str) -> dict:
        team = self.db.scalar(select(Team).where(Team.name == team_name))
        if not team:
            return {"team": team_name, "injuries": []}
        players = self.db.scalars(
            select(PlayerDetailed).where(PlayerDetailed.team_id == team.id)
        ).all()
        injuries = []
        for p in players:
            if p.injury_status or p.injuries:
                injuries.append({
                    "name": p.name,
                    "status": p.injury_status,
                    "detail": p.injury_detail or p.injuries,
                })
        return {"team": team_name, "injuries": injuries}

    def get_live_match(self, team1: str, team2: str) -> dict:
        stmt = select(Match).where(
            ((Match.team1_name == team1) & (Match.team2_name == team2))
            | ((Match.team1_name == team2) & (Match.team2_name == team1))
        )
        match = self.db.scalar(stmt)
        if not match:
            return {"found": False}
        return {
            "found": True,
            "status": match.status,
            "score": f"{match.home_score or 0}:{match.away_score or 0}",
            "minute": match.minute,
            "period": match.period,
            "events": match.events_json,
        }

    def search_news(self, teams: list[str], days: int = 7) -> list[dict]:
        items = NewsRepository(self.db).list_recent(limit=20)
        result = []
        for n in items:
            if n.team_tags and any(t in (n.team_tags or []) for t in teams):
                result.append({
                    "title": n.title,
                    "url": n.url,
                    "summary": n.summary,
                    "source": n.source,
                })
        return result[:10]

    def get_tactical_matchup(
        self,
        team1: str,
        team2: str,
        profile1: dict | None = None,
        profile2: dict | None = None,
    ) -> dict:
        t1 = profile1 if profile1 else self.get_team_profile(team1)
        t2 = profile2 if profile2 else self.get_team_profile(team2)
        return {
            "team1_formation": t1.get("formation"),
            "team2_formation": t2.get("formation"),
            "team1_strength": t1.get("fifa_ranking"),
            "team2_strength": t2.get("fifa_ranking"),
            "note": "基于阵型与FIFA排名的战术对比摘要",
        }

    def gather_match_facts(self, team1: str, team2: str) -> dict:
        """Single-pass fact bundle — avoids duplicate profile queries."""
        t1 = self.get_team_profile(team1)
        t2 = self.get_team_profile(team2)
        return {
            "team1": t1,
            "team2": t2,
            "injuries": {
                team1: self.get_injury_report(team1),
                team2: self.get_injury_report(team2),
            },
            "news": self.search_news([team1, team2]),
            "tactical": self.get_tactical_matchup(team1, team2, t1, t2),
            "h2h": self.get_head_to_head(team1, team2),
            "live": self.get_live_match(team1, team2),
        }

    def get_head_to_head(self, team1: str, team2: str) -> dict:
        finished = self.db.scalars(
            select(Match).where(
                Match.status == "finished",
                (
                    ((Match.team1_name == team1) & (Match.team2_name == team2))
                    | ((Match.team1_name == team2) & (Match.team2_name == team1))
                ),
            )
        ).all()
        meetings = [
            {"score": f"{m.home_score}:{m.away_score}", "date": m.match_date}
            for m in finished
        ]

        bsd_meetings: list[dict] = []
        client = BsdClient()
        if client.configured:
            name_map = load_team_bsd_mapping()
            c1, c2 = canonical_team_name(team1), canonical_team_name(team2)
            id1 = name_map.get(c1) or name_map.get(team1)
            id2 = name_map.get(c2) or name_map.get(team2)
            if id1 and id2:
                seen: set[int] = set()
                for fx in client.list_league_events(team_id=id1, status="finished"):
                    teams = {fx.get("home_team_id"), fx.get("away_team_id")}
                    if id2 not in teams:
                        continue
                    eid = fx.get("id")
                    if eid in seen:
                        continue
                    seen.add(eid)
                    bsd_meetings.append({
                        "score": f"{fx.get('home_score')}:{fx.get('away_score')}",
                        "date": (fx.get("event_date") or "")[:10],
                        "source": "bsd",
                    })
                    if len(bsd_meetings) >= 5:
                        break

        return {
            "team1": team1,
            "team2": team2,
            "meetings_in_db": len(meetings),
            "recent_db": meetings[:5],
            "recent_api": bsd_meetings,
            "note": "合并本地与 BSD 交锋记录",
        }
