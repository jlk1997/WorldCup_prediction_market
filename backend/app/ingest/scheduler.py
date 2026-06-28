"""Background data ingestion scheduler with adaptive poll intervals."""

from __future__ import annotations

import logging
import sys
import time
from datetime import datetime, timedelta
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
        try:
            from app.services.collectible_service import CollectibleService

            highlights = CollectibleService(db).apply_match_highlights_batch()
            if highlights:
                logger.info("Collectible match highlights updated: %s cards", highlights)
        except Exception:
            logger.exception("Collectible highlight sync failed")
        try:
            from app.services.collectible_chain_service import CollectibleChainService

            chain_result = CollectibleChainService(db).process_pending()
            if chain_result.get("minted") or chain_result.get("failed"):
                logger.info("Collectible AVATA mint batch: %s", chain_result)
        except Exception:
            logger.exception("Collectible AVATA mint batch failed")
        try:
            from app.services.marketplace_service import MarketplaceService

            auction_result = MarketplaceService(db).settle_expired_auctions()
            if auction_result.get("settled") or auction_result.get("expired"):
                logger.info("Marketplace auctions settled: %s", auction_result)
            fixed_result = MarketplaceService(db).expire_stale_listings()
            if fixed_result.get("expired"):
                logger.info("Marketplace fixed listings expired: %s", fixed_result)
        except Exception:
            logger.exception("Marketplace auction settlement failed")
        try:
            from app.services.primary_mint_service import PrimaryMintService

            lottery_result = PrimaryMintService(db).draw_pending_lotteries()
            if lottery_result.get("drawn"):
                logger.info("Mint lottery auto-draw: %s", lottery_result)
            status_result = PrimaryMintService(db).sync_event_statuses()
            if status_result.get("updated"):
                logger.info("Mint event status sync: %s", status_result)
            expire_mint = PrimaryMintService(db).expire_pending_mint_orders()
            if expire_mint.get("expired"):
                logger.info("Expired pending mint orders: %s", expire_mint)
        except Exception:
            logger.exception("Mint lottery auto-draw failed")
        try:
            from app.services.matchday_orchestration_service import MatchdayOrchestrationService

            md = MatchdayOrchestrationService(db).run_matchday_cycle()
            if md.get("ai_pushes") or md.get("matchday_activated"):
                logger.info("Matchday orchestration: %s", md)
        except Exception:
            logger.exception("Matchday orchestration failed")
        try:
            from app.services.payment_service import PaymentService

            order_expire = PaymentService(db).expire_abandoned_pending_orders()
            if order_expire.get("generic_expired") or order_expire.get("mint_expired"):
                logger.info("Expired abandoned orders: %s", order_expire)
        except Exception:
            logger.exception("Order expiry failed")
        try:
            from app.db.models import Match
            from app.services.fantasy_service import FantasyService

            fantasy = FantasyService(db)
            recent_cutoff = datetime.utcnow() - timedelta(days=3)
            finished = (
                db.query(Match)
                .filter(Match.status == "finished", Match.live_updated_at >= recent_cutoff)
                .order_by(Match.id.desc())
                .limit(50)
                .all()
            )
            total_fantasy = sum(fantasy.score_match(m) for m in finished)
            if total_fantasy:
                logger.info("Fantasy lineups scored: %s", total_fantasy)
            if datetime.utcnow().weekday() == 0:
                settle = fantasy.settle_previous_week()
                if settle.get("awarded"):
                    logger.info("Fantasy weekly settlement: %s", settle)
        except Exception:
            logger.exception("Fantasy scoring failed")
        try:
            from app.services.card_duel_service import CardDuelService

            duel_exp = CardDuelService(db).expire_pending_pvp_duels()
            if duel_exp.get("expired"):
                logger.info("Card duel pending expired: %s", duel_exp)
            from app.services.card_duel_match_service import CardDuelMatchService

            match_res = CardDuelMatchService(db).process_matchmaking()
            if match_res.get("matched") or match_res.get("expired"):
                logger.info("Card duel matchmaking: %s", match_res)
            from app.services.duel_season_service import DuelSeasonService

            season_res = DuelSeasonService(db).settle_ended_seasons()
            if season_res.get("settled"):
                logger.info("Duel season settled: %s", season_res)
        except Exception:
            logger.exception("Card duel expiry failed")
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
