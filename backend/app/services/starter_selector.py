"""Assign 4-3-3 starters per team based on overall_rating."""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.db.models import PlayerDetailed, Team


def update_all_starters(db: Session) -> int:
    db.execute(text("UPDATE players_detailed SET is_starter = FALSE"))
    teams = list(db.scalars(select(Team.id)).all())
    updated = 0

    for team_id in teams:
        starters: list[int] = []

        def top_ids(position: str, limit: int) -> list[int]:
            stmt = (
                select(PlayerDetailed.id)
                .where(
                    PlayerDetailed.team_id == team_id,
                    PlayerDetailed.position == position,
                )
                .order_by(PlayerDetailed.overall_rating.desc().nulls_last())
                .limit(limit)
            )
            return list(db.scalars(stmt).all())

        starters.extend(top_ids("门将", 1))
        starters.extend(top_ids("后卫", 4))
        starters.extend(top_ids("中场", 3))
        starters.extend(top_ids("前锋", 3))

        if len(starters) < 11:
            shortage = 11 - len(starters)
            stmt = (
                select(PlayerDetailed.id)
                .where(
                    PlayerDetailed.team_id == team_id,
                    PlayerDetailed.position != "教练",
                )
                .order_by(PlayerDetailed.overall_rating.desc().nulls_last())
                .limit(shortage)
            )
            if starters:
                stmt = stmt.where(~PlayerDetailed.id.in_(starters))
            starters.extend(list(db.scalars(stmt).all()))

        if starters:
            db.execute(
                text("UPDATE players_detailed SET is_starter = TRUE WHERE id = ANY(:ids)"),
                {"ids": starters},
            )
            updated += 1

    db.commit()
    return updated
