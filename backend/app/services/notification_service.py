"""User in-app notifications."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.commerce import UserNotification

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class NotificationService:
    CATEGORY_PREDICT = "predict_settled"

    def __init__(self, db: Session):
        self.db = db

    def list_for_user(
        self,
        user_id: int,
        *,
        unread_only: bool = False,
        category: str | None = None,
        limit: int = 20,
    ) -> list[UserNotification]:
        q = self.db.query(UserNotification).filter(UserNotification.user_id == user_id)
        if unread_only:
            q = q.filter(UserNotification.read_at.is_(None))
        if category:
            q = q.filter(UserNotification.category == category)
        return q.order_by(UserNotification.id.desc()).limit(min(limit, 50)).all()

    def unread_count(self, user_id: int, category: str | None = None) -> int:
        q = self.db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        )
        if category:
            q = q.filter(UserNotification.category == category)
        return q.count()

    def unread_badge(self, user_id: int) -> dict[str, int]:
        from sqlalchemy import func

        rows = (
            self.db.query(UserNotification.category, func.count())
            .filter(
                UserNotification.user_id == user_id,
                UserNotification.read_at.is_(None),
            )
            .group_by(UserNotification.category)
            .all()
        )
        return {cat: int(cnt) for cat, cnt in rows}

    def mark_read(self, user_id: int, ids: list[int] | None) -> int:
        q = self.db.query(UserNotification).filter(
            UserNotification.user_id == user_id,
            UserNotification.read_at.is_(None),
        )
        if ids:
            q = q.filter(UserNotification.id.in_(ids))
        now = _utcnow()
        updated = 0
        for row in q.all():
            row.read_at = now
            updated += 1
        return updated

    def _upsert(
        self,
        user_id: int,
        category: str,
        title: str,
        body: str,
        *,
        ref_type: str | None = None,
        ref_id: int | None = None,
        payload: dict | None = None,
    ) -> UserNotification | None:
        existing = None
        if ref_type is not None and ref_id is not None:
            existing = (
                self.db.query(UserNotification)
                .filter(
                    UserNotification.user_id == user_id,
                    UserNotification.category == category,
                    UserNotification.ref_type == ref_type,
                    UserNotification.ref_id == ref_id,
                )
                .first()
            )
        if existing:
            existing.title = title
            existing.body = body
            existing.payload = payload
            existing.read_at = None
            return existing
        row = UserNotification(
            user_id=user_id,
            category=category,
            ref_type=ref_type,
            ref_id=ref_id,
            title=title,
            body=body,
            payload=payload,
        )
        self.db.add(row)
        return row

    def notify_predict_settled(
        self,
        user_id: int,
        prediction_id: int,
        *,
        team1: str | None,
        team2: str | None,
        final_score: str | None,
        status: str,
        points_awarded: int = 0,
        redeem_points_awarded: int = 0,
        coins_returned: int = 0,
        season_rank: int | None = None,
        void_reason: str | None = None,
        user_pick_label: str | None = None,
        result_pick_label: str | None = None,
        next_match_id: int | None = None,
        next_match_label: str | None = None,
        next_match_hours: float | None = None,
        match_id: int | None = None,
        user_pick: str | None = None,
        stake_coins: int = 0,
        is_free: bool = False,
        win_streak_after: int = 0,
        loss_streak_after: int = 0,
        ai_pick: str | None = None,
        ai_pick_label: str | None = None,
        user_followed_ai: bool | None = None,
        ai_pick_correct: bool | None = None,
    ) -> None:
        match_label = f"{team1 or '?'} vs {team2 or '?'}"
        if status == "won":
            title = "竞猜猜中了"
            parts = [f"{match_label} 比分 {final_score or '—'}"]
            if points_awarded:
                parts.append(f"猜对 +{points_awarded} 累计积分")
            if redeem_points_awarded:
                parts.append(f"+{redeem_points_awarded} 可用积分")
            if coins_returned:
                parts.append(f"返还 {coins_returned} 球迷币")
            if season_rank:
                parts.append(f"累计积分榜第 {season_rank} 名")
            body = " · ".join(parts)
        elif status == "void":
            title = "竞猜流局"
            if void_reason == "no_score":
                body = f"{match_label} 完场超过 72 小时仍无比分，质押已退还"
            else:
                body = f"{match_label} 比赛推迟，质押已退还"
        else:
            title = "竞猜未中"
            if user_pick_label and result_pick_label:
                body = f"你选「{user_pick_label}」，实际 {final_score or '—'}（{result_pick_label}），下次继续加油"
            else:
                body = f"{match_label} 比分 {final_score or '—'}，下次继续加油"
        payload = {
            "status": status,
            "match_id": match_id,
            "match_label": match_label,
            "team1": team1,
            "team2": team2,
            "final_score": final_score,
            "user_pick": user_pick,
            "user_pick_label": user_pick_label,
            "result_pick_label": result_pick_label,
            "stake_coins": stake_coins,
            "is_free": is_free,
            "points_awarded": points_awarded,
            "redeem_points_awarded": redeem_points_awarded,
            "coins_returned": coins_returned,
            "season_rank": season_rank,
            "void_reason": void_reason,
            "win_streak_after": win_streak_after,
            "loss_streak_after": loss_streak_after,
            "next_match_id": next_match_id,
            "next_match_label": next_match_label,
            "next_match_hours": next_match_hours,
            "prediction_id": prediction_id,
            "ai_pick": ai_pick,
            "ai_pick_label": ai_pick_label,
            "user_followed_ai": user_followed_ai,
            "ai_pick_correct": ai_pick_correct,
        }
        if next_match_id and next_match_label:
            hours_txt = f"{next_match_hours} 小时后" if next_match_hours is not None else "稍后"
            body = f"{body} · 下一场 {next_match_label} {hours_txt}开赛"
        try:
            self._upsert(
                user_id,
                self.CATEGORY_PREDICT,
                title,
                body,
                ref_type="game_prediction",
                ref_id=prediction_id,
                payload=payload,
            )
        except Exception:
            logger.exception("notify_predict_settled failed user=%s pred=%s", user_id, prediction_id)

    def notify_redeem_success(
        self,
        user_id: int,
        order_id: int,
        product_name: str,
        redeem_price: int,
        redeem_points_after: int,
    ) -> None:
        try:
            self._upsert(
                user_id,
                "redeem_success",
                "积分兑换成功",
                f"已兑换「{product_name}」，消耗 {redeem_price} 可用积分，余额 {redeem_points_after}",
                ref_type="redeem_order",
                ref_id=order_id,
                payload={
                    "product_name": product_name,
                    "redeem_price": redeem_price,
                    "redeem_points_after": redeem_points_after,
                },
            )
        except Exception:
            logger.exception("notify_redeem_success failed user=%s order=%s", user_id, order_id)

    def notify_referral_reward(
        self,
        user_id: int,
        *,
        title: str,
        body: str,
        milestone_key: str,
        binding_id: int,
        coins: int = 0,
        battalion: int = 0,
        points: int = 0,
        ref_type: str = "referral_milestone",
        action: str | None = None,
    ) -> None:
        try:
            self._upsert(
                user_id,
                "referral_reward",
                title,
                body,
                ref_type=ref_type,
                ref_id=binding_id,
                payload={
                    "milestone_key": milestone_key,
                    "coins": coins,
                    "battalion": battalion,
                    "points": points,
                    "action": action or "/invite",
                },
            )
        except Exception:
            logger.exception(
                "notify_referral_reward failed user=%s milestone=%s",
                user_id,
                milestone_key,
            )

    def notify_leaderboard_season_reward(
        self,
        user_id: int,
        *,
        title: str,
        body: str,
        season_key: str,
        board: str,
        rank: int,
        season_points: int = 0,
        coins: int = 0,
        redeem_points: int = 0,
    ) -> None:
        try:
            self._upsert(
                user_id,
                "leaderboard_reward",
                title,
                body,
                ref_type="leaderboard_season",
                ref_id=rank,
                payload={
                    "season_key": season_key,
                    "board": board,
                    "rank": rank,
                    "season_points": season_points,
                    "coins": coins,
                    "redeem_points": redeem_points,
                    "action": "/leaderboard",
                },
            )
        except Exception:
            logger.exception(
                "notify_leaderboard_season_reward failed user=%s rank=%s",
                user_id,
                rank,
            )

    def notify_collectible_drop(
        self,
        user_id: int,
        *,
        drop_log_id: int,
        result: dict,
    ) -> None:
        cards = result.get("cards") or []
        if not cards:
            return
        card = cards[0]
        source = str(result.get("source") or "drop")
        source_labels = {
            "predict_win": "猜中",
            "signin": "连签",
            "matchday": "比赛日",
            "referral": "召友",
            "synthesis": "合成",
            "collection_pass": "手册",
            "event_cheer": "活动应援",
        }
        src_label = source_labels.get(source, "玩法")
        if card.get("is_duplicate"):
            title = "获得球星碎片"
            body = f"{card.get('name', '球星卡')} 重复 · +{card.get('shards_gained', 0)} 碎片"
        else:
            title = "获得球星卡"
            body = f"{src_label}掉落 · {card.get('name', '球星卡')}"
        try:
            self._upsert(
                user_id,
                "collectible_drop",
                title,
                body,
                ref_type="collectible_drop_log",
                ref_id=drop_log_id,
                payload={
                    "action": "/collection",
                    "source": source,
                    "card_code": card.get("code"),
                    "card_name": card.get("name"),
                    "is_duplicate": bool(card.get("is_duplicate")),
                    "collectible_drop": result,
                },
            )
        except Exception:
            logger.exception("notify_collectible_drop failed user=%s log=%s", user_id, drop_log_id)

    def notify_collection_pass_level_up(
        self,
        user_id: int,
        level: int,
        season_code: str,
    ) -> None:
        try:
            self._upsert(
                user_id,
                "collection_pass",
                f"手册升至 Lv.{level}",
                "前往收藏册手册页领取对应等级奖励",
                ref_type="collection_pass_season",
                ref_id=level,
                payload={"action": "/collection?tab=pass", "level": level, "season_code": season_code},
            )
        except Exception:
            logger.exception(
                "notify_collection_pass_level_up failed user=%s level=%s",
                user_id,
                level,
            )

    def notify_collectible_set_claimed(
        self,
        user_id: int,
        *,
        set_id: int,
        set_name: str,
        reward: dict,
    ) -> None:
        parts = [f"集齐「{set_name}」"]
        if reward.get("badge_title"):
            parts.append(f"徽章 {reward['badge_title']}")
        if reward.get("fan_coins"):
            parts.append(f"+{reward['fan_coins']} 球迷币")
        if reward.get("redeem_points"):
            parts.append(f"+{reward['redeem_points']} 可用积分")
        try:
            self._upsert(
                user_id,
                "collectible_set",
                "套组奖励已领取",
                " · ".join(parts),
                ref_type="card_set",
                ref_id=set_id,
                payload={"action": "/collection", "set_name": set_name, "reward": reward},
            )
        except Exception:
            logger.exception("notify_collectible_set_claimed failed user=%s set=%s", user_id, set_id)

    def notify_collectible_chain_minted(
        self,
        user_id: int,
        *,
        user_card_id: int,
        card_name: str,
        nft_id: str | None = None,
    ) -> None:
        body = f"{card_name} 已铸造为文昌链数字藏品"
        if nft_id:
            body = f"{body} · ID {nft_id[:12]}…"
        try:
            self._upsert(
                user_id,
                "collectible_chain",
                "文昌链凭证已就绪",
                body,
                ref_type="user_collectible_card",
                ref_id=user_card_id,
                payload={"action": "/collection", "card_name": card_name, "nft_id": nft_id},
            )
        except Exception:
            logger.exception(
                "notify_collectible_chain_minted failed user=%s card=%s",
                user_id,
                user_card_id,
            )

    def notify_mint_purchase_success(
        self,
        user_id: int,
        card_name: str,
        serial_no: int | None,
        order_id: int,
    ) -> None:
        serial_text = f" · 序列号 #{serial_no}" if serial_no else ""
        try:
            self._upsert(
                user_id,
                "mint_purchase",
                "打新成功",
                f"已获得限量球星卡「{card_name}」{serial_text}，可前往收藏册查看并参与对决/阵容",
                ref_type="order",
                ref_id=order_id,
                payload={"action": "/collection", "card_name": card_name, "serial_no": serial_no},
            )
        except Exception:
            logger.exception("notify_mint_purchase_success failed user=%s order=%s", user_id, order_id)

    def notify_fantasy_weekly(
        self,
        user_id: int,
        *,
        period_key: str,
        rank: int,
        score: int,
        coins_awarded: int = 0,
        ref_id: int | None = None,
    ) -> None:
        if coins_awarded > 0:
            title = f"Fantasy 周榜第 {rank} 名"
            body = f"{period_key} 得分 {score}，奖励 {coins_awarded} 球迷币"
        else:
            title = "Fantasy 周报"
            body = f"{period_key} 排名第 {rank} 名，得分 {score}。调整阵容再战本周！"
        try:
            self._upsert(
                user_id,
                "fantasy_weekly",
                title,
                body,
                ref_type="fantasy_period",
                ref_id=ref_id if ref_id is not None else user_id,
                payload={
                    "action": "/fantasy",
                    "period_key": period_key,
                    "rank": rank,
                    "score": score,
                    "coins_awarded": coins_awarded,
                },
            )
        except Exception:
            logger.exception(
                "notify_fantasy_weekly failed user=%s period=%s", user_id, period_key
            )

    def notify_redeem_refund(
        self,
        user_id: int,
        order_id: int,
        product_name: str,
        redeem_price: int,
        redeem_points_after: int,
    ) -> None:
        try:
            self._upsert(
                user_id,
                "redeem_refund",
                "兑换已撤销",
                f"「{product_name}」兑换已撤销，退回 {redeem_price} 可用积分，当前余额 {redeem_points_after}",
                ref_type="redeem_order",
                ref_id=order_id,
                payload={
                    "product_name": product_name,
                    "redeem_price": redeem_price,
                    "redeem_points_after": redeem_points_after,
                },
            )
        except Exception:
            logger.exception("notify_redeem_refund failed user=%s order=%s", user_id, order_id)
