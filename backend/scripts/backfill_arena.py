"""Optional backfill: migrate historical cheers/quiz/predictions into fan_activity_logs."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy.orm import Session

from app.db.models import Match, Team
from app.db.models.commerce import FanQuizLog, GamePrediction, User, UserCheer
from app.db.session import SessionLocal
from app.services.arena_service import ArenaService, _date_ref

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)


def _team_id(db: Session, name: str | None) -> int | None:
    if not name:
        return None
    t = db.query(Team).filter(Team.name == name).first()
    return t.id if t else None


def backfill(db: Session, dry_run: bool = True) -> dict:
    svc = ArenaService(db)
    stats = {"cheer": 0, "quiz": 0, "predict_submit": 0, "predict_win": 0, "skipped": 0}

    for uc in db.query(UserCheer).all():
        user = db.get(User, uc.user_id)
        if not user:
            continue
        ok = svc.record_activity(
            user,
            "cheer",
            team_id=uc.team_id,
            battalion_delta=10,
            ref_type="match",
            ref_id=uc.match_id,
        )
        stats["cheer" if ok else "skipped"] += 1

    for q in db.query(FanQuizLog).filter(FanQuizLog.correct.is_(True)).all():
        user = db.get(User, q.user_id)
        if not user:
            continue
        ok = svc.record_activity(
            user,
            "quiz",
            team_id=user.favorite_team_id,
            battalion_delta=8,
            ref_type="date",
            ref_id=_date_ref(q.quiz_date),
        )
        stats["quiz" if ok else "skipped"] += 1

    for pred in db.query(GamePrediction).all():
        user = db.get(User, pred.user_id)
        if not user:
            continue
        ok = svc.record_activity(
            user,
            "predict_submit",
            team_id=user.favorite_team_id,
            battalion_delta=5,
            ref_type="match",
            ref_id=pred.match_id,
        )
        stats["predict_submit" if ok else "skipped"] += 1
        if pred.status == "won" and pred.points_awarded:
            match = db.get(Match, pred.match_id)
            if match:
                ok2 = svc.on_predict_settle(user, pred, match)
                if ok2.get("battalion_added"):
                    stats["predict_win"] += 1

    if dry_run:
        db.rollback()
        logger.info("DRY RUN — rolled back")
    else:
        db.commit()
        logger.info("Committed backfill")
    return stats


def main():
    parser = argparse.ArgumentParser(description="Backfill arena activity logs from legacy data")
    parser.add_argument("--commit", action="store_true", help="Persist changes (default dry-run)")
    args = parser.parse_args()
    db = SessionLocal()
    try:
        result = backfill(db, dry_run=not args.commit)
        logger.info("Backfill stats: %s", result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
