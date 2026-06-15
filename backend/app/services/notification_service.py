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
