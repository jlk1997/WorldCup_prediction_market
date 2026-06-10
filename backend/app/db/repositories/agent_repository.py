from datetime import datetime, timedelta



from sqlalchemy import desc, or_, select

from sqlalchemy.orm import Session



from app.core.match_pair import normalize_match_pair

from app.db.models import AgentRun





class AgentRepository:

    def __init__(self, db: Session):

        self.db = db



    def find_recent(

        self,

        team1: str,

        team2: str,

        mode: str = "pre_match",

        max_age_hours: int = 24,

        max_age_minutes: int | None = None,

        live_fingerprint: str | None = None,

    ) -> AgentRun | None:

        if max_age_minutes is not None:

            cutoff = datetime.utcnow() - timedelta(minutes=max_age_minutes)

        else:

            cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)

        a, b = normalize_match_pair(team1, team2)

        stmt = (

            select(AgentRun)

            .where(AgentRun.mode == mode, AgentRun.created_at >= cutoff)

            .where(

                or_(

                    (AgentRun.team1 == a) & (AgentRun.team2 == b),

                    (AgentRun.team1 == b) & (AgentRun.team2 == a),

                )

            )

            .order_by(desc(AgentRun.created_at))

            .limit(5)

        )

        candidates = list(self.db.scalars(stmt).all())

        if not candidates:

            return None



        if mode == "live" and live_fingerprint:

            for run in candidates:

                stored = (run.final_output or {}).get("_live_fingerprint")

                if stored == live_fingerprint:

                    return run

            return None



        return candidates[0]



    def list_runs(
        self,
        limit: int = 20,
        offset: int = 0,
        team: str | None = None,
        mode: str | None = None,
        q: str | None = None,
        user_id: int | None = None,
    ) -> list[AgentRun]:
        stmt = select(AgentRun).order_by(desc(AgentRun.created_at))
        if user_id is not None:
            stmt = stmt.where(AgentRun.user_id == user_id)

        if mode:

            stmt = stmt.where(AgentRun.mode == mode)

        if team:

            stmt = stmt.where(or_(AgentRun.team1 == team, AgentRun.team2 == team))

        if q:

            like = f"%{q.strip()}%"

            stmt = stmt.where(or_(AgentRun.team1.ilike(like), AgentRun.team2.ilike(like)))

        stmt = stmt.offset(offset).limit(limit)

        return list(self.db.scalars(stmt).all())



    def get_by_id(self, run_id: int) -> AgentRun | None:

        return self.db.get(AgentRun, run_id)


