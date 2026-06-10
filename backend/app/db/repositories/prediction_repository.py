from datetime import datetime, timezone

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.match_pair import normalize_match_pair
from app.db.models import MatchPrediction


class PredictionRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, team1: str, team2: str) -> MatchPrediction | None:
        a, b = normalize_match_pair(team1, team2)
        stmt = select(MatchPrediction).where(
            MatchPrediction.team1 == a,
            MatchPrediction.team2 == b,
        )
        return self.db.scalar(stmt)

    def is_complete(self, prediction: MatchPrediction | None) -> bool:
        if not prediction:
            return False
        return all(
            [
                prediction.score,
                prediction.total_goals,
                prediction.red_cards,
                prediction.penalties,
                prediction.advice,
            ]
        )

    def upsert(
        self,
        team1: str,
        team2: str,
        *,
        score: str,
        total_goals: str,
        red_cards: str,
        penalties: str,
        advice: str,
    ) -> MatchPrediction:
        a, b = normalize_match_pair(team1, team2)
        row = self.get(a, b)
        if row:
            row.score = score
            row.total_goals = total_goals
            row.red_cards = red_cards
            row.penalties = penalties
            row.advice = advice
            row.updated_at = datetime.now(timezone.utc)
        else:
            row = MatchPrediction(
                team1=a,
                team2=b,
                score=score,
                total_goals=total_goals,
                red_cards=red_cards,
                penalties=penalties,
                advice=advice,
            )
            self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return row
