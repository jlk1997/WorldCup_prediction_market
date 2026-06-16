import logging
import math
import random
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import desc, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.cache import cache_delete, cache_delete_prefix, cache_get, cache_set
from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.core.match_scores import result_pick_from_team_scores
from app.db.models import Match, Team
from app.db.models.commerce import FanQuizLog, GamePrediction, TeamCheer, User, UserBadge, UserCheer
from app.db.repositories.user_repository import UserRepository, WalletRepository
from app.services.profile_service import ProfileService
from app.services.recommendation_service import RecommendationService
from app.services.arena_service import ArenaService
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)

_TEAM_NAME_ID_CACHE: dict[str, int | None] = {}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


from app.core.match_kickoff import parse_kickoff
from app.core.predict_eligibility import is_match_predictable, match_has_live_signals


def _match_has_live_signals(match: Match) -> bool:
    return match_has_live_signals(match)


class GameService:
    PICKS = {"home", "draw", "away"}
    CHEER_COST = 5
    CHEER_POINTS = 10
    QUIZ_REWARD = 15
    MATCH_DAY_SIGNIN_BONUS = 10
    QQ_GROUP_REASON = "qq_group_join"
    QQ_GROUP_REWARD_COINS = 50

    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.wallet = WalletRepository(db)

    def _match_predictable(self, match: Match, now: datetime | None = None) -> bool:
        return is_match_predictable(
            match,
            close_minutes_before=self.settings.predict_close_minutes_before,
            now=now or _utcnow(),
        )

    def _assert_match_predictable(self, match: Match) -> None:
        if match.status not in (None, "scheduled"):
            raise BadRequestError("该比赛已无法竞猜")
        kick = parse_kickoff(match)
        if not kick:
            raise BadRequestError("该比赛缺少开球时间，暂不可竞猜")
        now = _utcnow()
        if kick <= now:
            raise BadRequestError("比赛已开赛，无法竞猜")
        if kick - timedelta(minutes=self.settings.predict_close_minutes_before) <= now:
            raise BadRequestError("已超过竞猜截止时间")
        if _match_has_live_signals(match):
            raise BadRequestError("比赛已开始，无法竞猜")

    def list_predictable_matches(self) -> list[Match]:
        rows = (
            self.db.query(Match)
            .filter((Match.status == "scheduled") | (Match.status.is_(None)))
            .order_by(Match.match_date, Match.match_time)
            .all()
        )
        now = _utcnow()
        return [m for m in rows if self._match_predictable(m, now)]

    def list_predictable_match_cards(self, user: User | None = None) -> list[dict]:
        from app.services.recommendation_service import match_to_brief

        rows = self.list_predictable_matches()
        main_id = user.favorite_team_id if user else None
        sub_id = user.secondary_team_id if user else None
        star_ids: set[int] = set()
        if user:
            for s in RecommendationService(self.db)._star_player_matches(user.id):
                star_ids.add(s["match_id"])
        cards: list[dict] = []
        user_preds: dict[int, GamePrediction] = {}
        if user:
            for p in (
                self.db.query(GamePrediction)
                .filter(GamePrediction.user_id == user.id, GamePrediction.match_id.isnot(None))
                .all()
            ):
                user_preds[p.match_id] = p
        for m in rows:
            brief = match_to_brief(m, self.settings)
            t1 = self._team_id_by_name(m.team1_name)
            t2 = self._team_id_by_name(m.team2_name)
            team_ids = {x for x in (t1, t2) if x}
            pred = user_preds.get(m.id)
            cards.append(
                {
                    **brief,
                    "stadium": m.stadium,
                    "is_main_team": bool(main_id and main_id in team_ids),
                    "is_sub_team": bool(sub_id and sub_id in team_ids),
                    "has_star_player": m.id in star_ids,
                    "user_predicted": pred is not None,
                    "user_pick": pred.pick if pred else None,
                    "user_prediction_status": pred.status if pred else None,
                    "user_stake_coins": pred.stake_coins if pred else None,
                    "user_is_free": bool(pred.is_free) if pred else False,
                }
            )
        unpredicted_ids = [c["id"] for c in cards if not c.get("user_predicted")]
        if unpredicted_ids:
            stats_map = self._get_pick_stats_map(unpredicted_ids)
            for card in cards:
                if not card.get("user_predicted"):
                    card["pick_stats"] = stats_map.get(card["id"])
        return cards

    def submit_prediction(
        self,
        user: User,
        match_id: int,
        pick: str,
        stake_coins: int,
        use_free: bool = False,
    ) -> GamePrediction:
        pick = pick.strip().lower()
        if pick not in self.PICKS:
            raise BadRequestError("请选择 team1 胜 / 平局 / team2 胜（home / draw / away）")

        locked_user = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked_user:
            raise NotFoundError("用户不存在")
        user = locked_user

        existing = (
            self.db.query(GamePrediction)
            .filter(GamePrediction.user_id == user.id, GamePrediction.match_id == match_id)
            .first()
        )
        if existing:
            raise BadRequestError("您已竞猜过该场比赛")

        match = (
            self.db.query(Match).filter(Match.id == match_id).with_for_update().first()
        )
        if not match:
            raise NotFoundError("比赛不存在")
        self._assert_match_predictable(match)

        is_free = False
        stake = 0
        if use_free:
            if stake_coins > 0:
                raise BadRequestError("免费竞猜不可同时设置质押")
            today = _utcnow().date()
            used = self.wallet.count_free_predictions_today(user.id, today)
            bonus = 0
            try:
                from app.services.referral_service import ReferralService

                bonus = ReferralService(self.db, self.settings).bonus_free_predictions(user.id)
            except Exception:
                logger.exception("Referral bonus free predict lookup failed")
            if used >= self.settings.daily_free_predict + bonus + (user.extra_free_predict_daily or 0):
                raise BadRequestError("今日免费竞猜次数已用完")
            is_free = True
        else:
            stake = stake_coins
            if stake > 0:
                ProfileService(self.db).require_profile(user)
            if stake < self.settings.predict_stake_min or stake > self.settings.predict_stake_max:
                raise BadRequestError(
                    f"质押范围 {self.settings.predict_stake_min}-{self.settings.predict_stake_max} 球迷币"
                )
            self.wallet.deduct_coins(user, stake, "predict_stake", "match", match_id)

        pred = GamePrediction(
            user_id=user.id,
            match_id=match_id,
            pick=pick,
            stake_coins=stake,
            is_free=is_free,
            status="pending",
        )
        self.db.add(pred)
        try:
            self.db.flush()
        except IntegrityError:
            self.db.rollback()
            raise BadRequestError("您已竞猜过该场比赛") from None
        ArenaService(self.db).on_predict_submit(user, match_id)
        self.db.commit()
        self.db.refresh(pred)
        cache_delete_prefix("game:pick_stats:")
        self._referral_first_action(user)
        return pred

    def raise_prediction_stake(
        self,
        user: User,
        match_id: int,
        additional_stake_coins: int,
    ) -> GamePrediction:
        if additional_stake_coins <= 0:
            raise BadRequestError("追加质押金额须大于 0")

        locked_user = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked_user:
            raise NotFoundError("用户不存在")
        user = locked_user

        existing = (
            self.db.query(GamePrediction)
            .filter(GamePrediction.user_id == user.id, GamePrediction.match_id == match_id)
            .with_for_update()
            .first()
        )
        if not existing:
            raise BadRequestError("请先提交竞猜后再追加质押")
        if existing.status != "pending":
            raise BadRequestError("该竞猜已结算，无法追加质押")
        if existing.is_free:
            raise BadRequestError("免费竞猜不支持追加质押")

        match = (
            self.db.query(Match).filter(Match.id == match_id).with_for_update().first()
        )
        if not match:
            raise NotFoundError("比赛不存在")
        self._assert_match_predictable(match)

        new_total = existing.stake_coins + additional_stake_coins
        if additional_stake_coins < self.settings.predict_stake_min:
            raise BadRequestError(
                f"单次追加至少 {self.settings.predict_stake_min} 球迷币"
            )
        if new_total > self.settings.predict_stake_max:
            raise BadRequestError(
                f"质押总额不能超过 {self.settings.predict_stake_max} 球迷币（当前已质押 {existing.stake_coins}）"
            )

        ProfileService(self.db).require_profile(user)
        self.wallet.deduct_coins(user, additional_stake_coins, "predict_stake", "match", match_id)
        existing.stake_coins = new_total
        self.db.commit()
        self.db.refresh(existing)
        return existing

    def _referral_first_action(self, user: User) -> None:
        try:
            from app.services.referral_service import ReferralService

            ReferralService(self.db, self.settings).on_first_action(user)
        except Exception:
            logger.exception("Referral first_action hook failed")

    def signin(self, user: User) -> dict:
        today = _utcnow().date()
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        if user.last_signin_date == today:
            raise BadRequestError("今日已签到")
        yesterday = today - timedelta(days=1)
        if user.last_signin_date == yesterday:
            user.signin_streak = (user.signin_streak or 0) + 1
        else:
            user.signin_streak = 1
        user.last_signin_date = today
        added = self.settings.daily_signin_coins
        streak_bonus = 0
        streak = user.signin_streak or 1
        bonus_map = self.settings.signin_streak_bonus_map
        if streak in bonus_map:
            if streak == 7:
                streak_bonus = random.randint(
                    self.settings.signin_streak_day7_chest_min,
                    self.settings.signin_streak_day7_chest_max,
                )
            else:
                streak_bonus = bonus_map[streak]
            if streak_bonus > 0:
                self.wallet.add_coins(user, streak_bonus, "signin_streak_bonus")
        match_day = RecommendationService(self.db).is_match_day_for_user(user, today)
        signin_coins = self.settings.daily_signin_coins
        if match_day:
            signin_coins += self.MATCH_DAY_SIGNIN_BONUS
        self.wallet.add_coins(user, signin_coins, "daily_signin")
        added = signin_coins + streak_bonus
        arena_extra = ArenaService(self.db).on_signin(user, today, match_day)
        self._recalc_fan_level(user)
        self.db.commit()
        cache_delete("stats:signin_today")
        self.db.refresh(user)
        try:
            from app.services.referral_service import ReferralService

            ReferralService(self.db, self.settings).on_signin(user)
        except Exception:
            logger.exception("Referral signin hook failed")
        next_bonus_day = self._next_signin_streak_bonus_day(streak)
        return {
            "fan_coins": user.fan_coins,
            "added": added,
            "match_day_bonus": match_day,
            "battalion_added": arena_extra.get("battalion_added", 0),
            "signin_streak": streak,
            "streak_bonus": streak_bonus,
            "signin_streak_bonus_next": next_bonus_day,
        }

    def qq_group_claimed(self, user_id: int) -> bool:
        return self.wallet._coin_ledger_exists(
            user_id, self.QQ_GROUP_REASON, "user", user_id
        )

    def _today_signin_count(self) -> int:
        cached = cache_get("stats:signin_today")
        if cached is not None:
            return int(cached)
        today = _utcnow().date()
        cnt = (
            self.db.query(func.count(User.id))
            .filter(User.last_signin_date == today, User.status == "active")
            .scalar()
            or 0
        )
        cache_set("stats:signin_today", int(cnt), ttl=120)
        return int(cnt)

    def claim_qq_group_reward(self, user: User) -> dict:
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        if self.qq_group_claimed(user.id):
            return {
                "already_claimed": True,
                "coins_added": 0,
                "fan_coins": user.fan_coins,
            }
        self.wallet.add_coins(
            user,
            self.QQ_GROUP_REWARD_COINS,
            self.QQ_GROUP_REASON,
            "user",
            user.id,
        )
        return {
            "already_claimed": False,
            "coins_added": self.QQ_GROUP_REWARD_COINS,
            "fan_coins": user.fan_coins,
        }

    def my_predictions(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = (
            self.db.query(GamePrediction, Match)
            .join(Match, GamePrediction.match_id == Match.id)
            .filter(GamePrediction.user_id == user_id)
            .order_by(desc(GamePrediction.created_at))
            .limit(limit)
            .all()
        )
        return [self._prediction_card(pred, match) for pred, match in rows]

    def _prediction_card(self, pred: GamePrediction, match: Match | None) -> dict:
        pick_label = {"home": "主胜", "draw": "平局", "away": "客胜"}.get(pred.pick, pred.pick)
        if match and pred.pick == "home":
            pick_label = f"{match.team1_name} 胜"
        elif match and pred.pick == "away":
            pick_label = f"{match.team2_name} 胜"
        status_label = {
            "pending": "待开奖",
            "won": "猜中",
            "lost": "未中",
            "void": "流局退款",
        }.get(pred.status, pred.status)
        return {
            "id": pred.id,
            "match_id": pred.match_id,
            "pick": pred.pick,
            "pick_label": pick_label,
            "stake_coins": pred.stake_coins,
            "is_free": pred.is_free,
            "status": pred.status,
            "status_label": status_label,
            "points_awarded": pred.points_awarded,
            "redeem_points_awarded": pred.redeem_points_awarded or 0,
            "coins_returned": pred.coins_returned,
            "team1": match.team1_name if match else None,
            "team2": match.team2_name if match else None,
            "match_date": match.match_date if match else None,
            "match_time": match.match_time if match else None,
            "final_score": (
                f"{match.home_score}:{match.away_score}"
                if match and match.home_score is not None and match.away_score is not None
                else None
            ),
            "settled_at": pred.settled_at,
            "created_at": pred.created_at,
        }

    def void_postponed_predictions(self) -> int:
        """Refund stakes when match is postponed/cancelled."""
        pending_ids = [
            row if isinstance(row, int) else row[0]
            for row in (
                self.db.query(GamePrediction.id)
                .join(Match, GamePrediction.match_id == Match.id)
                .filter(GamePrediction.status == "pending", Match.status == "postponed")
                .all()
            )
        ]
        count = 0
        for pred_id in pending_ids:
            try:
                if self._void_one_transaction(pred_id):
                    count += 1
            except Exception:
                logger.exception("Failed to void prediction id=%s", pred_id)
                self.db.rollback()
        return count

    def _void_one_transaction(self, pred_id: int) -> bool:
        locked = (
            self.db.query(GamePrediction)
            .filter(GamePrediction.id == pred_id, GamePrediction.status == "pending")
            .with_for_update()
            .first()
        )
        if not locked:
            self.db.rollback()
            return False
        match = self.db.get(Match, locked.match_id)
        user = self.db.query(User).filter(User.id == locked.user_id).with_for_update().first()
        if not match or not user or match.status != "postponed":
            self.db.rollback()
            return False
        self._void_one(user, locked, match)
        self.db.commit()
        return True

    def _void_one(self, user: User, pred: GamePrediction, match: Match | None = None) -> None:
        if pred.status != "pending":
            return
        pred.status = "void"
        pred.settled_at = _utcnow()
        pred.points_awarded = 0
        if not pred.is_free and pred.stake_coins > 0:
            pred.coins_returned = pred.stake_coins
            self.wallet.add_coins(
                user,
                pred.stake_coins,
                "predict_void_refund",
                "game_prediction",
                pred.id,
            )
        else:
            pred.coins_returned = 0
        if match:
            try:
                NotificationService(self.db).notify_predict_settled(
                    user.id,
                    pred.id,
                    team1=match.team1_name,
                    team2=match.team2_name,
                    final_score=None,
                    status="void",
                    points_awarded=0,
                    redeem_points_awarded=0,
                    coins_returned=pred.coins_returned,
                )
            except Exception:
                logger.exception("Void notification failed pred=%s", pred.id)

    def settle_finished_matches(self) -> int:
        pending_ids = [
            row if isinstance(row, int) else row[0]
            for row in (
                self.db.query(GamePrediction.id)
                .join(Match, GamePrediction.match_id == Match.id)
                .filter(GamePrediction.status == "pending", Match.status == "finished")
                .all()
            )
        ]
        count = 0
        for pred_id in pending_ids:
            try:
                if self._settle_one_transaction(pred_id):
                    count += 1
            except Exception:
                logger.exception("Failed to settle prediction id=%s", pred_id)
                self.db.rollback()
        return count

    def _settle_one_transaction(self, pred_id: int) -> bool:
        locked = (
            self.db.query(GamePrediction)
            .filter(GamePrediction.id == pred_id, GamePrediction.status == "pending")
            .with_for_update()
            .first()
        )
        if not locked:
            self.db.rollback()
            return False
        match = self.db.get(Match, locked.match_id)
        user = self.db.query(User).filter(User.id == locked.user_id).with_for_update().first()
        if not match or not user or match.status != "finished":
            self.db.rollback()
            return False
        result_pick = result_pick_from_team_scores(match.home_score, match.away_score)
        if result_pick is None:
            if self._should_void_no_score(match):
                self._void_stale_no_score(user, locked, match)
                self.db.commit()
                self._post_settle_notify(
                    {
                        "user_id": user.id,
                        "prediction_id": locked.id,
                        "match_id": match.id,
                        "team1": match.team1_name,
                        "team2": match.team2_name,
                        "final_score": None,
                        "status": "void",
                        "void_reason": "no_score",
                        "points_awarded": 0,
                        "redeem_points_awarded": 0,
                        "coins_returned": locked.coins_returned,
                        "stake_coins": locked.stake_coins,
                        "is_free": locked.is_free,
                        "user_pick": locked.pick,
                    }
                )
                return True
            self.db.rollback()
            return False
        notify_payload = self._settle_one(user, locked, match)
        if not notify_payload:
            self.db.rollback()
            return False
        self.db.commit()
        self._post_settle_notify(notify_payload)
        return True

    def _post_settle_notify(self, payload: dict) -> None:
        try:
            if payload.get("status") == "won" and payload.get("season_rank") is None:
                from app.services.leaderboard_service import LeaderboardService

                user = self.db.get(User, payload["user_id"])
                if user:
                    payload["season_rank"] = LeaderboardService(self.db)._season_points_rank(user)
            notify_payload = {
                k: v
                for k, v in payload.items()
                if k not in ("user_id", "prediction_id", "result_pick")
            }
            NotificationService(self.db).notify_predict_settled(
                payload["user_id"],
                payload["prediction_id"],
                **notify_payload,
            )
            try:
                from app.core.user_ws_hub import push_predict_settled

                ws_payload = {**notify_payload, "prediction_id": payload["prediction_id"]}
                push_predict_settled(payload["user_id"], ws_payload)
            except Exception:
                logger.debug("User WS push skipped for pred=%s", payload.get("prediction_id"))
            cache_delete_prefix("game:win_feed:")
            cache_delete_prefix("game:pick_stats:")
            from app.core.match_cache import invalidate_match_caches

            invalidate_match_caches()
            self.db.commit()
        except Exception:
            logger.exception("Post-settle notification failed pred=%s", payload.get("prediction_id"))
            self.db.rollback()

    def _should_void_no_score(self, match: Match) -> bool:
        if match.home_score is not None and match.away_score is not None:
            return False
        ref = match.live_updated_at
        if not ref and match.match_date:
            try:
                ref = parse_kickoff(match)
            except Exception:
                ref = None
        if not ref:
            return False
        return (_utcnow() - ref) >= timedelta(hours=72)

    def _void_stale_no_score(self, user: User, pred: GamePrediction, match: Match) -> None:
        pred.status = "void"
        pred.settled_at = _utcnow()
        if not pred.is_free and pred.stake_coins > 0:
            pred.coins_returned = pred.stake_coins
            self.wallet.add_coins(user, pred.stake_coins, "predict_void_no_score", "game_prediction", pred.id)
        logger.warning(
            "Voided prediction %s — match %s finished 72h+ without scores",
            pred.id,
            match.id,
        )

    def settle_all_pending(self) -> dict:
        """Manual/admin trigger: settle finished + void postponed."""
        settled = self.settle_finished_matches()
        voided = self.void_postponed_predictions()
        return {"settled": settled, "voided": voided}

    def pending_predictions_count(self, user_id: int) -> int:
        return (
            self.db.query(GamePrediction)
            .filter(GamePrediction.user_id == user_id, GamePrediction.status == "pending")
            .count()
        )

    def _settle_one(self, user: User, pred: GamePrediction, match: Match) -> dict | None:
        if pred.status != "pending":
            return None
        # home_score/away_score are normalized to team1/team2 in live sync
        result = result_pick_from_team_scores(match.home_score, match.away_score)
        if result is None:
            logger.warning(
                "Skip settlement match=%s pred=%s: finished without scores",
                match.id,
                pred.id,
            )
            return None

        won = pred.pick == result
        pred.settled_at = _utcnow()
        user_pick_label = self._pick_label(match, pred.pick)
        result_pick_label = self._pick_label(match, result)

        if won:
            pred.status = "won"
            prev_loss_streak = user.loss_streak or 0
            user.loss_streak = 0
            base_points = 30 if result != "draw" else 20
            if user.has_season_pass and user.season_pass_until and user.season_pass_until > _utcnow():
                base_points = int(base_points * 1.2)
            streak_bonus = min(user.win_streak, 5) * 10
            total_season = base_points + streak_bonus
            loss_protect = prev_loss_streak >= self.settings.loss_streak_protect_after
            if loss_protect:
                total_season = int(total_season * self.settings.loss_streak_win_multiplier)
            if (user.referral_tier_granted or 0) >= 10:
                total_season = int(total_season * 1.05)
            redeem_ratio = self.settings.predict_win_redeem_ratio
            total_redeem = int(total_season * redeem_ratio)
            pred.points_awarded = total_season
            pred.redeem_points_awarded = total_redeem
            user.win_streak = (user.win_streak or 0) + 1
            self.wallet.add_season_points(user, total_season, "predict_win", "game_prediction", pred.id)
            if total_redeem > 0:
                self.wallet.add_redeem_points(user, total_redeem, "predict_win_redeem", "game_prediction", pred.id)

            if not pred.is_free and pred.stake_coins > 0:
                returned = pred.stake_coins * 2
                pred.coins_returned = returned
                self.wallet.add_coins(user, returned, "predict_win_return", "game_prediction", pred.id)
            elif pred.is_free:
                self.wallet.add_coins(user, 15, "free_predict_win", "game_prediction", pred.id)

            if user.win_streak >= 3:
                self._award_badge(user, f"streak_{user.win_streak}", f"{user.win_streak} 连胜")
            ArenaService(self.db).on_predict_settle(user, pred, match)
        else:
            pred.status = "lost"
            user.win_streak = 0
            user.loss_streak = (user.loss_streak or 0) + 1
            if not pred.is_free:
                pred.coins_returned = 0
        final_score = (
            f"{match.home_score}:{match.away_score}"
            if match.home_score is not None and match.away_score is not None
            else None
        )
        next_match = self._next_predictable_match(user, after_match_id=match.id)
        cache_delete_prefix("arena:")
        return {
            "user_id": user.id,
            "prediction_id": pred.id,
            "match_id": match.id,
            "team1": match.team1_name,
            "team2": match.team2_name,
            "final_score": final_score,
            "status": pred.status,
            "points_awarded": pred.points_awarded,
            "redeem_points_awarded": pred.redeem_points_awarded or 0,
            "coins_returned": pred.coins_returned,
            "user_pick": pred.pick,
            "result_pick": result,
            "user_pick_label": user_pick_label,
            "result_pick_label": result_pick_label,
            "stake_coins": pred.stake_coins,
            "is_free": pred.is_free,
            "win_streak_after": user.win_streak or 0,
            "loss_streak_after": user.loss_streak or 0,
            "next_match_id": next_match["id"] if next_match else None,
            "next_match_label": next_match["label"] if next_match else None,
            "next_match_hours": next_match["hours_until"] if next_match else None,
        }

    def _award_badge(self, user: User, code: str, title: str) -> None:
        exists = (
            self.db.query(UserBadge)
            .filter(UserBadge.user_id == user.id, UserBadge.badge_code == code)
            .first()
        )
        if not exists:
            self.db.add(UserBadge(user_id=user.id, badge_code=code, title=title))

    def leaderboard(self, period: str = "season", limit: int = 50) -> list[dict]:
        from app.services.leaderboard_service import LeaderboardService

        return LeaderboardService(self.db).legacy_points_list(period, limit)

    def fan_rank(self, limit: int = 20) -> list[dict]:
        rows = (
            self.db.query(Team.name, func.count(User.id).label("fans"))
            .join(User, User.favorite_team_id == Team.id)
            .group_by(Team.id, Team.name)
            .order_by(desc("fans"))
            .limit(limit)
            .all()
        )
        return [{"team": name, "fans": fans} for name, fans in rows]

    def team_contribution_leaderboard(self, team_id: int | None = None, limit: int = 30) -> list[dict]:
        q = self.db.query(User).filter(User.status == "active", User.favorite_team_id.isnot(None))
        if team_id:
            q = q.filter(User.favorite_team_id == team_id)
        rows = q.order_by(desc(User.battalion_points_season)).limit(limit).all()
        return [
            {
                "user_id": u.id,
                "nickname": u.nickname,
                "season_points": u.season_points,
                "battalion_points": u.battalion_points_season or 0,
                "fan_cheers_total": u.fan_cheers_total,
                "arena_tier": u.arena_tier,
                "team_id": u.favorite_team_id,
            }
            for u in rows
        ]

    def get_cheer_status(self, match_id: int, user_id: int | None = None) -> dict:
        match = self.db.get(Match, match_id)
        if not match:
            raise NotFoundError("比赛不存在")
        t1 = self._team_id_by_name(match.team1_name)
        t2 = self._team_id_by_name(match.team2_name)
        cheers = {r.team_id: r.total_cheers for r in self.db.query(TeamCheer).filter(TeamCheer.match_id == match_id).all()}
        user_cheered = False
        user_team_id = None
        if user_id:
            uc = self.db.query(UserCheer).filter(UserCheer.user_id == user_id, UserCheer.match_id == match_id).first()
            if uc:
                user_cheered = True
                user_team_id = uc.team_id
        kick = parse_kickoff(match)
        now = _utcnow()
        close_min = self.settings.predict_close_minutes_before
        cheer_block_reason = None
        if match.status not in (None, "scheduled"):
            cheer_block_reason = "match_started"
        elif not kick:
            cheer_block_reason = "no_kickoff"
        elif kick - timedelta(minutes=close_min) <= now:
            cheer_block_reason = "closed_before_kickoff"
        can_cheer = cheer_block_reason is None
        cheer_extra_done = False
        if user_id:
            cheer_extra_done = ArenaService(self.db).user_has_cheer_extra(user_id, match_id)
        user_row = self.db.get(User, user_id) if user_id else None
        free_tickets = (user_row.free_cheer_tickets or 0) if user_row else 0
        arena = ArenaService(self.db).get_match_arena(match_id, user_id)
        return {
            "match_id": match_id,
            "match_date": match.match_date,
            "match_time": match.match_time,
            "team1": {"id": t1, "name": match.team1_name, "cheers": cheers.get(t1, 0) if t1 else 0},
            "team2": {"id": t2, "name": match.team2_name, "cheers": cheers.get(t2, 0) if t2 else 0},
            "user_cheered": user_cheered,
            "user_cheer_team_id": user_team_id,
            "user_cheer_extra_done": cheer_extra_done,
            "can_cheer": bool(can_cheer),
            "cheer_block_reason": cheer_block_reason,
            "kickoff_at": kick.isoformat() if kick else None,
            "cheer_close_minutes": close_min,
            "free_cheer_tickets": free_tickets,
            "cheer_cost": 0 if free_tickets > 0 else self.CHEER_COST,
            "arena": {
                "home_power": arena["home"]["power"],
                "away_power": arena["away"]["power"],
                "leader_name": arena["leader_name"],
                "lead_points": arena["lead_points"],
            },
        }

    def submit_cheer(self, user: User, match_id: int, team_id: int) -> dict:
        ProfileService(self.db).require_profile(user)
        match = self.db.get(Match, match_id)
        if not match:
            raise NotFoundError("比赛不存在")
        t1 = self._team_id_by_name(match.team1_name)
        t2 = self._team_id_by_name(match.team2_name)
        if team_id not in {t1, t2}:
            raise BadRequestError("只能为主队或客队助威")
        allowed = {user.favorite_team_id, user.secondary_team_id}
        if team_id not in allowed:
            raise BadRequestError("只能为您的主队或副队助威")

        kick = parse_kickoff(match)
        now = _utcnow()
        if not kick:
            raise BadRequestError("该比赛缺少开球时间，暂不可助威")
        if kick - timedelta(minutes=self.settings.predict_close_minutes_before) <= now:
            raise BadRequestError("该比赛已停止助威")
        if match.status not in (None, "scheduled"):
            raise BadRequestError("比赛已开始或结束")

        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked

        existing = self.db.query(UserCheer).filter(UserCheer.user_id == user.id, UserCheer.match_id == match_id).first()
        if existing:
            raise BadRequestError("您已为该场比赛助威过")

        used_ticket = False
        if (user.free_cheer_tickets or 0) > 0:
            user.free_cheer_tickets -= 1
            used_ticket = True
        else:
            self.wallet.deduct_coins(user, self.CHEER_COST, "cheer", "match", match_id)

        tc = (
            self.db.query(TeamCheer)
            .filter(TeamCheer.match_id == match_id, TeamCheer.team_id == team_id)
            .with_for_update()
            .first()
        )
        if not tc:
            tc = TeamCheer(match_id=match_id, team_id=team_id, total_cheers=0)
            self.db.add(tc)
            self.db.flush()
        tc.total_cheers += self.CHEER_POINTS
        user.fan_cheers_total = (user.fan_cheers_total or 0) + self.CHEER_POINTS
        self.db.add(
            UserCheer(
                user_id=user.id,
                match_id=match_id,
                team_id=team_id,
                coins_spent=0 if used_ticket else self.CHEER_COST,
                cheer_points=self.CHEER_POINTS,
            )
        )
        self._recalc_fan_level(user)
        ArenaService(self.db).on_cheer(user, match_id, team_id)
        self.db.commit()
        self._referral_first_action(user)
        return self.get_cheer_status(match_id, user.id)

    def get_quiz_today(self, user: User) -> dict:
        today = _utcnow().date()
        done = self.db.query(FanQuizLog).filter(FanQuizLog.user_id == user.id, FanQuizLog.quiz_date == today).first()
        q = self._build_quiz(user, today)
        q.pop("correct_index", None)
        return {**q, "answered": done is not None, "was_correct": done.correct if done else None}

    def answer_quiz(self, user: User, answer_index: int) -> dict:
        today = _utcnow().date()
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise NotFoundError("用户不存在")
        user = locked
        if self.db.query(FanQuizLog).filter(FanQuizLog.user_id == user.id, FanQuizLog.quiz_date == today).first():
            raise BadRequestError("今日问答已完成")
        q = self._build_quiz(user, today)
        correct = answer_index == q["correct_index"]
        coins = self.QUIZ_REWARD if correct else 0
        if correct and not user.favorite_team_id:
            coins = coins // 2
        if correct and coins > 0:
            self.wallet.add_coins(user, coins, "quiz_reward")
        self.db.add(FanQuizLog(user_id=user.id, quiz_date=today, correct=correct, coins_awarded=coins))
        battalion_added = 0
        if correct:
            battalion_added = ArenaService(self.db).on_quiz_correct(user, today).get("battalion_added", 0)
        self.db.commit()
        self.db.refresh(user)
        return {
            "correct": correct,
            "coins_awarded": coins,
            "fan_coins": user.fan_coins,
            "battalion_added": battalion_added,
        }

    def get_fan_card(self, user: User) -> dict:
        profile = ProfileService(self.db).get_status(user)
        preds = self.my_predictions(user.id, limit=200)
        settled = [p for p in preds if p.status in ("won", "lost")]
        wins = sum(1 for p in settled if p.status == "won")
        total = len(settled)
        win_rate = round(wins / total * 100, 1) if total else 0
        badges = (
            self.db.query(UserBadge)
            .filter(UserBadge.user_id == user.id)
            .order_by(desc(UserBadge.awarded_at))
            .limit(5)
            .all()
        )
        main = profile["main_team"]
        standing = ArenaService(self.db).get_my_standing(user)
        from app.db.models.commerce import ReferralBinding

        same_team_recruits = (
            self.db.query(ReferralBinding)
            .filter(
                ReferralBinding.inviter_id == user.id,
                ReferralBinding.same_team_bonus_applied.is_(True),
            )
            .count()
        )
        return {
            "nickname": user.nickname,
            "main_team": profile["main_team"],
            "secondary_team": profile["secondary_team"],
            "players": profile["players"],
            "fan_cheers_total": user.fan_cheers_total,
            "fan_level": user.fan_level,
            "season_points": user.season_points,
            "redeem_points": user.redeem_points or 0,
            "battalion_points": user.battalion_points_season or 0,
            "arena_tier": user.arena_tier,
            "team_rank": standing.get("rank"),
            "team_members": standing.get("total_members"),
            "star_contributions": standing.get("star_contributions", []),
            "win_rate": win_rate,
            "predictions_total": total,
            "badges": [{"title": b.title, "code": b.badge_code} for b in badges],
            "tagline": f"我在最后一舞为 {main['name'] if main else '世界杯'} 助威 {user.fan_cheers_total} 次"
            if main
            else "最后一舞 · 世界杯2026 球迷",
            "avatar_frame": user.avatar_frame,
            "theme_key": user.theme_key,
            "same_team_recruits": same_team_recruits,
            "invite_code": user.invite_code,
        }

    def _build_quiz(self, user: User, quiz_date: date | None = None) -> dict:
        quiz_date = quiz_date or _utcnow().date()
        seed = f"{user.id}:{quiz_date.isoformat()}"
        rng = random.Random(seed)

        team = self.db.get(Team, user.favorite_team_id) if user.favorite_team_id else None
        if team and team.coach:
            wrong = ["齐达内", "瓜迪奥拉", "穆里尼奥"]
            correct_answer = team.coach
            opts = [correct_answer] + [w for w in wrong if w != correct_answer][:3]
            while len(opts) < 4:
                opts.append("未知")
            opts = opts[:4]
            rng.shuffle(opts)
            return {
                "question": f"{team.name} 的主教练是谁？",
                "options": opts,
                "correct_index": opts.index(correct_answer),
            }
        if team and team.group_name:
            groups = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L"]
            wrong = [g for g in groups if g != team.group_name][:3]
            correct_answer = team.group_name
            opts = [correct_answer] + wrong
            rng.shuffle(opts)
            return {
                "question": f"{team.name} 位于哪个小组？",
                "options": opts,
                "correct_index": opts.index(correct_answer),
            }
        opts = ["32", "48", "64", "16"]
        correct_answer = "48"
        rng.shuffle(opts)
        return {
            "question": "2026 世界杯共有多少支参赛球队？",
            "options": opts,
            "correct_index": opts.index(correct_answer),
        }

    def _team_id_by_name(self, name: str | None) -> int | None:
        if not name:
            return None
        if name in _TEAM_NAME_ID_CACHE:
            return _TEAM_NAME_ID_CACHE[name]
        t = self.db.query(Team).filter(Team.name == name).first()
        team_id = t.id if t else None
        _TEAM_NAME_ID_CACHE[name] = team_id
        return team_id

    def _recalc_fan_level(self, user: User) -> None:
        score = (user.fan_cheers_total or 0) // 50 + (user.season_points or 0) // 100
        user.fan_level = max(1, min(99, 1 + score))

    def _pick_label(self, match: Match, pick: str) -> str:
        if pick == "home":
            return f"{match.team1_name} 胜"
        if pick == "away":
            return f"{match.team2_name} 胜"
        return "平局"

    def _next_signin_streak_bonus_day(self, current_streak: int) -> int | None:
        days = sorted(self.settings.signin_streak_bonus_map.keys())
        for d in days:
            if d > current_streak:
                return d
        return days[-1] if days else None

    def _free_predict_limit(self, user: User) -> int:
        bonus = 0
        try:
            from app.services.referral_service import ReferralService

            bonus = ReferralService(self.db, self.settings).bonus_free_predictions(user.id)
        except Exception:
            logger.exception("Referral bonus free predict lookup failed")
        return self.settings.daily_free_predict + bonus + (user.extra_free_predict_daily or 0)

    def _redeem_progress(self, user: User) -> dict | None:
        from app.db.models.commerce import Product

        have = user.redeem_points or 0
        avg_redeem_per_win = max(
            1,
            int(30 * self.settings.predict_win_redeem_ratio),
        )
        candidates = (
            self.db.query(Product)
            .filter(Product.pay_currency == "redeem", Product.active.is_(True))
            .order_by(Product.redeem_price.asc(), Product.sort_order.asc(), Product.id.asc())
            .all()
        )
        for product in candidates:
            need = product.redeem_price or 0
            if need <= 0:
                continue
            if have < need:
                gap = need - have
                return {
                    "next_sku": product.sku,
                    "next_name": product.name,
                    "need": need,
                    "have": have,
                    "gap": gap,
                    "pct": round(have / need * 100, 1) if need else 100,
                    "wins_estimate": math.ceil(gap / avg_redeem_per_win),
                    "avg_redeem_per_win": avg_redeem_per_win,
                }
        if candidates:
            last = candidates[-1]
            need = last.redeem_price or 0
            return {
                "next_sku": last.sku,
                "next_name": last.name,
                "need": need,
                "have": have,
                "gap": 0,
                "pct": 100,
                "wins_estimate": 0,
                "avg_redeem_per_win": avg_redeem_per_win,
            }
        return None

    def _next_pending_match(self, user_id: int) -> dict | None:
        row = (
            self.db.query(GamePrediction, Match)
            .join(Match, GamePrediction.match_id == Match.id)
            .filter(GamePrediction.user_id == user_id, GamePrediction.status == "pending")
            .order_by(Match.match_date, Match.match_time)
            .first()
        )
        if not row:
            return None
        pred, match = row
        kick = parse_kickoff(match)
        hours = None
        if kick:
            delta = kick - _utcnow()
            hours = max(0, round(delta.total_seconds() / 3600, 1))
        return {
            "prediction_id": pred.id,
            "match_id": match.id,
            "label": f"{match.team1_name} vs {match.team2_name}",
            "hours_until": hours,
        }

    def _next_predictable_match(self, user: User, after_match_id: int | None = None) -> dict | None:
        now = _utcnow()
        for m in self.list_predictable_matches():
            if after_match_id and m.id == after_match_id:
                continue
            kick = parse_kickoff(m)
            hours = round((kick - now).total_seconds() / 3600, 1) if kick else None
            return {
                "id": m.id,
                "label": f"{m.team1_name} vs {m.team2_name}",
                "hours_until": hours,
            }
        return None

    def _pass_benefits_today(self, user: User) -> dict | None:
        if not user.has_season_pass or not user.season_pass_until or user.season_pass_until <= _utcnow():
            return None
        today = _utcnow().date()
        claimed = user.last_season_pass_daily == today
        daily_coins = self.settings.season_pass_daily_coins
        from app.services.ai_billing_service import AiBillingService

        ai = AiBillingService(self.db, self.settings)
        base_ai = self.settings.ai_daily_free_analyses
        limit = ai.daily_free_limit(user)
        row = ai._get_usage_row(user.id, today)  # noqa: SLF001 — internal quota row
        free_used = row.free_used if row else 0
        extra_ai_used = max(0, min(free_used - base_ai, limit - base_ai))
        ai_saved = extra_ai_used * self.settings.ai_coin_cost_pre_match
        coins_saved = (daily_coins if claimed else 0) + ai_saved
        return {
            "active": True,
            "daily_coins_grant": daily_coins,
            "coins_claimed_today": claimed,
            "coins_saved_today": coins_saved,
            "points_bonus_pct": 20,
            "extra_ai_free_total": max(0, limit - base_ai),
            "extra_ai_free_used": extra_ai_used,
        }

    def get_daily_status(self, user: User) -> dict:
        today = _utcnow().date()
        free_used = self.wallet.count_free_predictions_today(user.id, today)
        free_limit = self._free_predict_limit(user)
        quiz_done = (
            self.db.query(FanQuizLog)
            .filter(FanQuizLog.user_id == user.id, FanQuizLog.quiz_date == today)
            .first()
        )
        streak = user.signin_streak or 0
        next_pending = self._next_pending_match(user.id)
        streak_risk = self._streak_risk_hint(user, next_pending)
        signed_today = user.last_signin_date == today
        quiz_answered = quiz_done is not None
        free_remaining = max(0, free_limit - free_used)
        pending_count = self.pending_predictions_count(user.id)
        match_day = RecommendationService(self.db).is_match_day_for_user(user, today)
        qq_claimed = self.qq_group_claimed(user.id)
        checklist = self._daily_checklist(
            signed_today, quiz_answered, free_remaining, free_limit, pending_count, match_day, qq_claimed
        )
        next_action = self._daily_next_action(
            user, checklist, free_remaining, pending_count, match_day, qq_claimed
        )
        return {
            "signed_today": signed_today,
            "last_signin_date": user.last_signin_date.isoformat() if user.last_signin_date else None,
            "signin_streak": streak,
            "signin_streak_bonus_next": self._next_signin_streak_bonus_day(streak),
            "today_signin_count": self._today_signin_count(),
            "free_predict": {
                "used": free_used,
                "limit": free_limit,
                "remaining": free_remaining,
            },
            "quiz": {"answered": quiz_answered},
            "pending_predictions": pending_count,
            "next_pending_match": next_pending,
            "streak_risk": streak_risk,
            "win_streak": user.win_streak or 0,
            "loss_streak": user.loss_streak or 0,
            "redeem_progress": self._redeem_progress(user),
            "match_day": match_day,
            "match_day_message": (
                "比赛日加成已开启 · 签到 +10 币 · 去擂台动员可为军团加分"
                if match_day
                else None
            ),
            "free_cheer_tickets": user.free_cheer_tickets or 0,
            "loss_streak_protect_after": self.settings.loss_streak_protect_after,
            "loss_streak_multiplier": self.settings.loss_streak_win_multiplier,
            "checklist": checklist,
            "next_action": next_action,
            "ritual_progress": self._ritual_progress(checklist),
            "qq_group_claimed": qq_claimed,
            "pass_benefits": self._pass_benefits_today(user),
        }

    def get_match_pick_stats(self, match_id: int) -> dict:
        cached = cache_get(f"game:pick_stats:{match_id}")
        if cached is not None:
            return cached
        result = self._pick_stats_for_match(match_id)
        cache_set(f"game:pick_stats:{match_id}", result, ttl=45)
        return result

    def _pick_stats_for_match(self, match_id: int) -> dict:
        rows = (
            self.db.query(GamePrediction.pick, func.count(GamePrediction.id))
            .filter(GamePrediction.match_id == match_id, GamePrediction.status == "pending")
            .group_by(GamePrediction.pick)
            .all()
        )
        counts = {pick: int(cnt) for pick, cnt in rows}
        total = sum(counts.values())
        distribution = {}
        for pick in self.PICKS:
            cnt = counts.get(pick, 0)
            distribution[pick] = {
                "count": cnt,
                "pct": round(cnt / total * 100, 1) if total else 0,
            }
        return {"match_id": match_id, "total": total, "distribution": distribution}

    def _get_pick_stats_map(self, match_ids: list[int]) -> dict[int, dict]:
        if not match_ids:
            return {}
        uncached: list[int] = []
        result: dict[int, dict] = {}
        for mid in match_ids:
            cached = cache_get(f"game:pick_stats:{mid}")
            if cached is not None:
                result[mid] = cached
            else:
                uncached.append(mid)
        if not uncached:
            return result
        rows = (
            self.db.query(GamePrediction.match_id, GamePrediction.pick, func.count(GamePrediction.id))
            .filter(
                GamePrediction.match_id.in_(uncached),
                GamePrediction.status == "pending",
            )
            .group_by(GamePrediction.match_id, GamePrediction.pick)
            .all()
        )
        by_match: dict[int, dict[str, int]] = {mid: {} for mid in uncached}
        for mid, pick, cnt in rows:
            by_match[mid][pick] = int(cnt)
        for mid in uncached:
            counts = by_match.get(mid, {})
            total = sum(counts.values())
            distribution = {}
            for pick in self.PICKS:
                c = counts.get(pick, 0)
                distribution[pick] = {
                    "count": c,
                    "pct": round(c / total * 100, 1) if total else 0,
                }
            item = {"match_id": mid, "total": total, "distribution": distribution}
            cache_set(f"game:pick_stats:{mid}", item, ttl=45)
            result[mid] = item
        return result

    def _daily_checklist(
        self,
        signed_today: bool,
        quiz_answered: bool,
        free_remaining: int,
        free_limit: int,
        pending_count: int,
        match_day: bool,
        qq_claimed: bool = True,
    ) -> list[dict]:
        signin_reward = "+20币"
        if match_day:
            signin_reward = "+30币(比赛日)"
        items = [
            {"key": "signin", "label": "每日签到", "done": signed_today, "reward": signin_reward},
            {"key": "quiz", "label": "主队问答", "done": quiz_answered, "reward": "+15币"},
            {
                "key": "predict",
                "label": "免费竞猜",
                "done": free_remaining <= 0,
                "reward": f"剩余 {free_remaining}/{free_limit}",
            },
            {
                "key": "pending",
                "label": "待开奖",
                "done": pending_count == 0,
                "reward": f"{pending_count} 场" if pending_count else "暂无",
                "optional": True,
            },
        ]
        if not qq_claimed:
            items.insert(
                1,
                {
                    "key": "qq_group",
                    "label": "加入官方 QQ 群",
                    "done": False,
                    "reward": f"+{self.QQ_GROUP_REWARD_COINS}币(一次)",
                },
            )
        return items

    def _ritual_progress(self, checklist: list[dict]) -> dict:
        core = [
            c for c in checklist if not c.get("optional") and c.get("key") != "qq_group"
        ]
        done = sum(1 for c in core if c["done"])
        total = len(core)
        return {
            "done": done,
            "total": total,
            "pct": round(done / total * 100) if total else 100,
        }

    def _daily_bonus_action(self, user: User, pending_count: int) -> dict | None:
        streak = user.win_streak or 0
        if streak >= 2 and pending_count == 0:
            nxt = self._next_predictable_match(user)
            if nxt:
                return {
                    "key": "streak_protect",
                    "label": f"连胜 {streak} 场 · 再猜一场守护加成",
                    "path": f"/predict?highlight={nxt['id']}",
                    "hint": f"下一场 {nxt['label']}",
                }
        gap = self._redeem_progress(user)
        if gap and gap.get("gap", 0) > 0:
            return {
                "key": "redeem_goal",
                "label": f"差 {gap['gap']} 可用积分换 {gap['next_name']}",
                "path": "/predict",
                "hint": "继续猜中为兑换助力",
            }
        try:
            from app.services.leaderboard_service import LeaderboardService

            summary = LeaderboardService(self.db).get_my_summary(user)
            season_gap = summary.get("season_gap_to_prev")
            if season_gap and season_gap > 0:
                return {
                    "key": "rank_up",
                    "label": f"累计积分再 +{season_gap} 可超过上一名",
                    "path": "/leaderboard",
                    "hint": "冲榜进行中",
                }
        except Exception:
            logger.exception("Leaderboard gap lookup failed for daily bonus action")
        today = _utcnow().date()
        pass_active = bool(
            user.has_season_pass
            and user.season_pass_until
            and user.season_pass_until > _utcnow()
        )
        if pass_active and user.last_season_pass_daily != today:
            return {
                "key": "pass_daily",
                "label": f"通行证每日 {self.settings.season_pass_daily_coins} 币未领",
                "path": "/shop",
                "hint": "猜中积分 +20%",
            }
        return {
            "key": "invite",
            "label": "邀球友一起猜 · 双方得球迷币",
            "path": "/invite",
            "hint": "有效邀请冲召友榜",
        }

    def _daily_next_action(
        self,
        user: User,
        checklist: list[dict],
        free_remaining: int,
        pending_count: int,
        match_day: bool,
        qq_claimed: bool = True,
    ) -> dict:
        by_key = {c["key"]: c for c in checklist}
        if not by_key["signin"]["done"]:
            return {
                "key": "signin",
                "label": "先签到领今日球迷币",
                "path": "/me?focus=signin",
                "hint": by_key["signin"]["reward"],
            }
        if not qq_claimed and "qq_group" in by_key:
            return {
                "key": "qq_group",
                "label": "加入官方 QQ 群领球迷币",
                "path": "/predict?qq=1",
                "hint": by_key["qq_group"]["reward"],
            }
        if not by_key["quiz"]["done"]:
            return {
                "key": "quiz",
                "label": "答一道主队题，再赚 15 币",
                "path": "/me?focus=quiz",
                "hint": "+15 币",
            }
        if free_remaining > 0:
            return {
                "key": "predict",
                "label": f"还有 {free_remaining} 次免费竞猜没用",
                "path": "/predict",
                "hint": "猜中得积分",
            }
        if pending_count > 0:
            return {
                "key": "pending",
                "label": f"{pending_count} 场待开奖，去看看结果",
                "path": "/me?focus=predictions",
                "hint": "结算后会通知你",
            }
        if match_day:
            return {
                "key": "arena",
                "label": "比赛日 · 去擂台动员助威",
                "path": "/arena",
                "hint": "为军团加分",
            }
        bonus = self._daily_bonus_action(user, pending_count)
        if bonus:
            return bonus
        return {
            "key": "done",
            "label": "今日核心任务已完成，明天再来",
            "path": "/predict",
            "hint": None,
        }

    def _streak_risk_hint(self, user: User, next_pending: dict | None) -> dict | None:
        streak = user.win_streak or 0
        if streak < 2:
            return None
        bonus_next = min(streak, 5) * 10
        hours = None
        label = None
        match_id = None
        if next_pending and next_pending.get("hours_until") is not None:
            hours = next_pending["hours_until"]
            label = next_pending.get("label")
            match_id = next_pending.get("match_id")
            if hours is not None and hours <= 2:
                return {
                    "match_id": match_id,
                    "label": label,
                    "hours_until": hours,
                    "win_streak": streak,
                    "streak_bonus_next": bonus_next,
                    "message": f"待开奖「{label}」约 {hours} 小时后出结果 · 当前 {streak} 连胜，猜中可 +{bonus_next} 分加成",
                }
        nxt = self._next_predictable_match(user)
        if nxt and nxt.get("hours_until") is not None and nxt["hours_until"] <= 2:
            return {
                "match_id": nxt["id"],
                "label": nxt["label"],
                "hours_until": nxt["hours_until"],
                "win_streak": streak,
                "streak_bonus_next": bonus_next,
                "message": f"下一场 {nxt['label']} 约 {nxt['hours_until']} 小时后开赛 · 再赢 1 场 +{bonus_next} 分，猜错连胜清零",
            }
        return None

    def preview_predict(
        self,
        user: User,
        pick: str,
        stake_coins: int = 0,
        use_free: bool = False,
    ) -> dict:
        pick = pick.strip().lower()
        if pick not in self.PICKS:
            raise BadRequestError("无效选项")
        base_points = 30 if pick != "draw" else 20
        if user.has_season_pass and user.season_pass_until and user.season_pass_until > _utcnow():
            base_points = int(base_points * 1.2)
        streak_bonus = min(user.win_streak or 0, 5) * 10
        total_season = base_points + streak_bonus
        if (user.loss_streak or 0) >= self.settings.loss_streak_protect_after:
            total_season = int(total_season * self.settings.loss_streak_win_multiplier)
        if (user.referral_tier_granted or 0) >= 10:
            total_season = int(total_season * 1.05)
        total_redeem = int(total_season * self.settings.predict_win_redeem_ratio)
        coins_return = 0
        free_win_coins = 0
        if use_free:
            free_win_coins = 15
        elif stake_coins > 0:
            coins_return = stake_coins * 2
        return {
            "pick": pick,
            "use_free": use_free,
            "stake_coins": stake_coins,
            "on_win": {
                "season_points": total_season,
                "redeem_points": total_redeem,
                "coins_returned": coins_return,
                "free_win_coins": free_win_coins,
                "streak_bonus": streak_bonus,
            },
        }

    def get_win_feed(self, limit: int = 20) -> dict:
        lim = min(limit, 50)
        cache_key = f"game:win_feed:{lim}"
        cached = cache_get(cache_key)
        if cached is not None:
            if isinstance(cached, list):
                return {"items": cached, "recent_count": len(cached)}
            return cached
        since = _utcnow() - timedelta(hours=6)
        recent_count = (
            self.db.query(func.count(GamePrediction.id))
            .filter(
                GamePrediction.status == "won",
                GamePrediction.settled_at.isnot(None),
                GamePrediction.settled_at >= since,
            )
            .scalar()
            or 0
        )
        rows = (
            self.db.query(GamePrediction, Match, User)
            .join(Match, GamePrediction.match_id == Match.id)
            .join(User, GamePrediction.user_id == User.id)
            .filter(GamePrediction.status == "won", GamePrediction.settled_at.isnot(None))
            .order_by(desc(GamePrediction.settled_at))
            .limit(lim)
            .all()
        )
        out = []
        for pred, match, user in rows:
            nick = user.nickname
            if len(nick) > 2:
                nick = nick[0] + "*" * (len(nick) - 2) + nick[-1]
            out.append(
                {
                    "nickname": nick,
                    "team1": match.team1_name,
                    "team2": match.team2_name,
                    "points_awarded": pred.points_awarded,
                    "settled_at": pred.settled_at.isoformat() if pred.settled_at else None,
                }
            )
        result = {"items": out, "recent_count": int(recent_count)}
        cache_set(cache_key, result, ttl=30)
        return result
