from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import PlayerDetailed, Team


class PlayerRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_by_team(self, team_id: int) -> list[PlayerDetailed]:
        stmt = (
            select(PlayerDetailed)
            .where(PlayerDetailed.team_id == team_id)
            .order_by(PlayerDetailed.id)
        )
        return list(self.db.scalars(stmt).all())

    def list_all(
        self,
        limit: int = 100,
        q: str | None = None,
        team_name: str | None = None,
    ) -> list[tuple[PlayerDetailed, str]]:
        stmt = (
            select(PlayerDetailed, Team.name)
            .join(Team, PlayerDetailed.team_id == Team.id)
            .order_by(Team.name, PlayerDetailed.name)
            .limit(limit)
        )
        if q:
            like = f"%{q.strip()}%"
            stmt = stmt.where(
                PlayerDetailed.name.ilike(like) | Team.name.ilike(like) | PlayerDetailed.club.ilike(like)
            )
        if team_name:
            stmt = stmt.where(Team.name == team_name)
        return list(self.db.execute(stmt).all())

    def get_by_id(self, player_id: int) -> tuple[PlayerDetailed, str] | None:
        stmt = (
            select(PlayerDetailed, Team.name)
            .join(Team, PlayerDetailed.team_id == Team.id)
            .where(PlayerDetailed.id == player_id)
        )
        row = self.db.execute(stmt).first()
        return row if row else None
