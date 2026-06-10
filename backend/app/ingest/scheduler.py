"""Background data ingestion scheduler with adaptive poll intervals."""

from __future__ import annotations

import logging
import sys
import time
from datetime import timedelta
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select

from app.core.config import get_settings
from app.db.models import Match
from app.db.session import SessionLocal
from app.ingest.enrich_service import TeamEnrichService
from app.ingest.live_sync_service import LiveMatchSyncService
from app.ingest.news_rss_service import NewsRssService
from app.ingest.standings_sync_service import StandingsSyncService

logger = logging.getLogger(__name__)


def _has_live_matches(db) -> bool:
    return bool(
        db.scalar(select(Match.id).where(Match.status == "live").limit(1))
    )


def run_once():
    db = SessionLocal()
    try:
        live = LiveMatchSyncService(db).sync()
        news = NewsRssService(db).sync()
        enrich = TeamEnrichService(db).sync()
        standings = StandingsSyncService().sync()
        settled = 0
        voided = 0
        try:
            from app.services.game_service import GameService

            gs = GameService(db)
            settled = gs.settle_finished_matches()
            voided = gs.void_postponed_predictions()
        except Exception:
            logger.exception("Game settlement failed")
        try:
            from app.services.arena_service import ArenaService

            ArenaService(db).freeze_finished_arenas()
            ArenaService(db).process_matchday_goal_rewards()
            ArenaService(db).recalc_arena_tiers()
        except Exception:
            logger.exception("Arena maintenance failed")
        try:
            from app.services.season_pass_service import SeasonPassService

            batch = SeasonPassService(db).grant_daily_batch()
            if batch.get("granted_users"):
                logger.info("Season pass daily batch: %s", batch)
        except Exception:
            logger.exception("Season pass daily batch failed")
        try:
            from app.services.auth_service import AuthService

            purged = AuthService.purge_expired_sessions(db)
            if purged:
                logger.info("Purged %s expired user sessions", purged)
        except Exception:
            logger.exception("Session purge failed")
        try:
            from app.services.referral_service import ReferralService

            referral_result = ReferralService(db).settle_previous_week()
            if referral_result.get("awarded"):
                logger.info("Referral weekly settlement: %s", referral_result)
        except Exception:
            logger.exception("Referral weekly settlement failed")
        logger.info(
            "Ingest complete: live=%s news=%s enrich=%s standings=%s settled=%s voided=%s",
            live,
            news,
            enrich,
            standings,
            settled,
            voided,
        )
        return _has_live_matches(db)
    finally:
        db.close()


def main():
    from app.core.distributed_lock import distributed_lock

    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    settings = get_settings()
    logger.info(
        "Ingest scheduler started (live=%ss idle=%ss)",
        settings.live_poll_interval_live,
        settings.live_poll_interval_idle,
    )
    while True:
        sleep_sec = settings.live_poll_interval_idle
        with distributed_lock("ingest:leader", ttl_sec=max(120, settings.live_poll_interval_idle + 60)) as leader:
            if not leader:
                time.sleep(min(30, settings.live_poll_interval_idle))
                continue
            try:
                has_live = run_once()
            except Exception:
                logger.exception("Ingest cycle failed")
                has_live = False
            sleep_sec = settings.live_poll_interval_live if has_live else settings.live_poll_interval_idle
        time.sleep(sleep_sec)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    if args.once:
        logging.basicConfig(level=logging.INFO)
        run_once()
    else:
        main()
