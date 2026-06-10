"""Remove test junk rows and reset live-sync corruption on official schedule."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text

from app.db.session import SessionLocal
from app.ingest.quota import invalidate_live_cache


def repair(*, dry_run: bool = False) -> dict:
    db = SessionLocal()
    try:
        total_before = db.scalar(text("SELECT COUNT(*) FROM matches")) or 0
        junk_ids = db.execute(
            text(
                """
                SELECT id FROM matches
                WHERE match_date ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
                   OR (team1_name = 'A' AND team2_name = 'B')
                   OR team1_name LIKE '结算队A_%'
                   OR team1_name LIKE '延期A_%'
                """
            )
        ).scalars().all()

        reset_official = db.execute(
            text(
                """
                UPDATE matches
                SET status = 'scheduled',
                    home_score = NULL,
                    away_score = NULL,
                    minute = NULL,
                    period = NULL,
                    events_json = NULL,
                    live_updated_at = NULL
                WHERE match_date LIKE '%年%月%日%'
                  AND (status <> 'scheduled'
                       OR home_score IS NOT NULL
                       OR away_score IS NOT NULL)
                """
            )
        ).rowcount

        deleted_preds = 0
        deleted_matches = 0
        if junk_ids:
            deleted_preds = db.execute(
                text("DELETE FROM game_predictions WHERE match_id = ANY(:ids)"),
                {"ids": junk_ids},
            ).rowcount
            deleted_matches = db.execute(
                text("DELETE FROM matches WHERE id = ANY(:ids)"),
                {"ids": junk_ids},
            ).rowcount

        if dry_run:
            db.rollback()
        else:
            db.commit()
            invalidate_live_cache()

        total_after = total_before if dry_run else (db.scalar(text("SELECT COUNT(*) FROM matches")) or 0)
        return {
            "total_before": total_before,
            "total_after": total_after,
            "junk_match_ids": len(junk_ids),
            "deleted_predictions": deleted_preds,
            "deleted_matches": deleted_matches,
            "reset_official_rows": reset_official,
            "dry_run": dry_run,
        }
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Remove pytest junk matches from PostgreSQL")
    parser.add_argument("--dry-run", action="store_true", help="Report only, do not commit")
    args = parser.parse_args()
    result = repair(dry_run=args.dry_run)
    print(result)


if __name__ == "__main__":
    main()
