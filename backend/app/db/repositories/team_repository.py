from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.db.models import Team


class TeamRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_all(self) -> list[Team]:
        return list(self.db.scalars(select(Team).order_by(Team.id)).all())

    def get_by_name(self, name: str) -> Team | None:
        stmt = (
            select(Team)
            .options(selectinload(Team.players_detailed))
            .where(Team.name == name)
        )
        return self.db.scalar(stmt)

    def get_by_id(self, team_id: int) -> Team | None:
        return self.db.get(Team, team_id)
