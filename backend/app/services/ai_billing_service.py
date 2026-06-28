"""AI analysis billing: daily free quota + coin deduction."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

import time

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError
from app.db.models.commerce import AiUsageDaily, User
from app.db.repositories.user_repository import WalletRepository


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _has_active_pass(user: User, now: datetime | None = None) -> bool:
    now = now or _utcnow()
    return bool(
        user.has_season_pass
        and user.season_pass_until
        and user.season_pass_until > now
    )


@dataclass
class BillingDecision:
    charge_coins: int
    used_free_quota: bool
    free_remaining: int
    daily_free_limit: int
    mode: str
    force_refresh: bool
    used_pack_credit: bool = False

    def to_dict(self) -> dict:
        return {
            "charge_coins": self.charge_coins,
            "used_free_quota": self.used_free_quota,
            "free_remaining": self.free_remaining,
            "daily_free_limit": self.daily_free_limit,
            "mode": self.mode,
            "force_refresh": self.force_refresh,
            "used_pack_credit": self.used_pack_credit,
        }


class AiBillingService:
    REASON_CHARGE = "ai_analysis"
    REASON_REFUND = "ai_analysis_refund"

    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.wallet = WalletRepository(db)

    def daily_free_limit(self, user: User) -> int:
        base = self.settings.ai_daily_free_analyses
        if _has_active_pass(user):
            base += self.settings.season_pass_extra_ai_free
        return base

    def mode_coin_cost(self, mode: str, force_refresh: bool, discount_pct: float = 0.0) -> int:
        if mode == "live":
            cost = self.settings.ai_coin_cost_live
        else:
            cost = self.settings.ai_coin_cost_pre_match
        if force_refresh:
            cost += self.settings.ai_coin_cost_force_refresh
        if discount_pct > 0 and cost > 0:
            cost = max(1, int(round(cost * (1 - min(discount_pct, 0.9)))))
        return cost

    def card_discount_pct(self, user: User, team_ids: set[int] | None) -> float:
        """持有或质押相关球队卡 → AI 分析折扣（赋能）。"""
        if not team_ids:
            return 0.0
        try:
            from app.db.models.commerce import CardStake, CollectibleCard, UserCollectibleCard

            holds = (
                self.db.query(UserCollectibleCard.id)
                .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
                .filter(
                    UserCollectibleCard.user_id == user.id,
                    CollectibleCard.team_id.in_(team_ids),
                )
                .first()
            )
            staked = (
                self.db.query(CardStake.id)
                .join(CollectibleCard, CardStake.card_id == CollectibleCard.id)
                .filter(
                    CardStake.user_id == user.id,
                    CardStake.status == "active",
                    CollectibleCard.team_id.in_(team_ids),
                )
                .first()
            )
            return self.settings.asset_ai_card_discount_pct if (holds or staked) else 0.0
        except Exception:
            return 0.0

    def resolve_team_ids(self, *team_names: str | None) -> set[int]:
        names = [n for n in team_names if n]
        if not names:
            return set()
        try:
            from app.db.models import Team

            rows = self.db.query(Team.id).filter(Team.name.in_(names)).all()
            return {r[0] for r in rows}
        except Exception:
            return set()

    def preview(
        self,
        user: User,
        mode: str,
        force_refresh: bool,
        cache_hit: bool,
        team_ids: set[int] | None = None,
    ) -> BillingDecision:
        if cache_hit:
            return BillingDecision(
                charge_coins=0,
                used_free_quota=False,
                free_remaining=self._free_remaining(user),
                daily_free_limit=self.daily_free_limit(user),
                mode=mode,
                force_refresh=force_refresh,
            )
        return self._decide_charge(user, mode, force_refresh, dry_run=True, team_ids=team_ids)

    def charge_before_llm(
        self, user_id: int, mode: str, force_refresh: bool, team_ids: set[int] | None = None
    ) -> BillingDecision:
        self.assert_global_token_budget()
        locked = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if not locked:
            raise BadRequestError("用户不存在")
        decision = self._decide_charge(locked, mode, force_refresh, dry_run=False, team_ids=team_ids)
        if decision.charge_coins > 0:
            ref_id = int(time.time() * 1000) & 0x7FFFFFFF
            self.wallet.deduct_coins(
                locked,
                decision.charge_coins,
                self.REASON_CHARGE,
                "ai_mode",
                ref_id,
            )
        if decision.used_free_quota:
            self._inc_free_used(locked.id)
        elif decision.charge_coins > 0:
            self._inc_paid_count(locked.id)
        self.db.flush()
        return decision

    def refund(self, user_id: int, amount: int, ref_id: int | None = None) -> None:
        if amount <= 0:
            return
        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user:
            return
        self.wallet.add_coins(user, amount, self.REASON_REFUND, "ai_refund", ref_id)
        row = self._get_usage_row(user_id, _utcnow().date(), for_update=True)
        if row and amount > 0:
            if row.paid_count > 0:
                row.paid_count -= 1
            elif row.free_used > 0:
                row.free_used -= 1
        self.db.flush()

    def refund_charge(self, user_id: int, decision: BillingDecision, ref_id: int | None = None) -> None:
        """Rollback coins or free quota after failed LLM run."""
        if decision.charge_coins > 0:
            self.refund(user_id, decision.charge_coins, ref_id)
            return
        if not decision.used_free_quota:
            return
        row = self._get_usage_row(user_id, _utcnow().date(), for_update=True)
        if row and row.free_used > 0:
            row.free_used -= 1
            self.db.flush()

    def add_tokens(self, user_id: int, tokens: int) -> None:
        if tokens <= 0:
            return
        row = self._get_usage_row(user_id, _utcnow().date(), for_update=True)
        if not row:
            row = AiUsageDaily(user_id=user_id, usage_date=_utcnow().date(), free_used=0, paid_count=0, tokens_total=0)
            self.db.add(row)
            self.db.flush()
        row.tokens_total += tokens

    def assert_global_token_budget(self) -> None:
        from app.services.ai_token_budget import AiTokenBudgetService

        AiTokenBudgetService(self.db).assert_can_reserve(0)

    def quota_status(self, user: User) -> dict:
        limit = self.daily_free_limit(user)
        row = self._get_usage_row(user.id, _utcnow().date())
        used = row.free_used if row else 0
        return {
            "daily_free_limit": limit,
            "free_used_today": used,
            "free_remaining": max(0, limit - used),
            "fan_coins": user.fan_coins,
            "has_season_pass": _has_active_pass(user),
            "ai_pack_live_credits": getattr(user, "ai_pack_live_credits", 0) or 0,
            "ai_pack_refresh_credits": getattr(user, "ai_pack_refresh_credits", 0) or 0,
            "costs": {
                "pre_match": self.settings.ai_coin_cost_pre_match,
                "live": self.settings.ai_coin_cost_live,
                "force_refresh_extra": self.settings.ai_coin_cost_force_refresh,
            },
        }

    def _free_remaining(self, user: User) -> int:
        limit = self.daily_free_limit(user)
        row = self._get_usage_row(user.id, _utcnow().date())
        used = row.free_used if row else 0
        return max(0, limit - used)

    def grant_ai_pack(self, user: User, payload: dict) -> None:
        live = int(payload.get("ai_live_credits") or 0)
        refresh = int(payload.get("ai_refresh_credits") or 0)
        if live:
            user.ai_pack_live_credits = (getattr(user, "ai_pack_live_credits", 0) or 0) + live
        if refresh:
            user.ai_pack_refresh_credits = (getattr(user, "ai_pack_refresh_credits", 0) or 0) + refresh

    def _decide_charge(
        self,
        user: User,
        mode: str,
        force_refresh: bool,
        dry_run: bool,
        team_ids: set[int] | None = None,
    ) -> BillingDecision:
        limit = self.daily_free_limit(user)
        row = self._get_usage_row(user.id, _utcnow().date(), for_update=not dry_run)
        free_used = row.free_used if row else 0
        discount = self.card_discount_pct(user, team_ids)
        coin_cost = self.mode_coin_cost(mode, force_refresh, discount)

        live_credits = getattr(user, "ai_pack_live_credits", 0) or 0
        refresh_credits = getattr(user, "ai_pack_refresh_credits", 0) or 0
        if mode == "live" and live_credits > 0:
            if not dry_run:
                user.ai_pack_live_credits = live_credits - 1
                if force_refresh and refresh_credits > 0:
                    user.ai_pack_refresh_credits = refresh_credits - 1
            return BillingDecision(
                charge_coins=0,
                used_free_quota=False,
                free_remaining=max(0, limit - free_used),
                daily_free_limit=limit,
                mode=mode,
                force_refresh=force_refresh,
                used_pack_credit=True,
            )

        if free_used < limit:
            return BillingDecision(
                charge_coins=0,
                used_free_quota=True,
                free_remaining=max(0, limit - free_used - (0 if dry_run else 1)),
                daily_free_limit=limit,
                mode=mode,
                force_refresh=force_refresh,
            )

        if force_refresh and refresh_credits > 0 and not dry_run:
            user.ai_pack_refresh_credits = refresh_credits - 1
            return BillingDecision(
                charge_coins=0,
                used_free_quota=False,
                free_remaining=max(0, limit - free_used),
                daily_free_limit=limit,
                mode=mode,
                force_refresh=force_refresh,
                used_pack_credit=True,
            )

        if (user.fan_coins or 0) < coin_cost:
            raise BadRequestError(
                f"今日免费 AI 次数已用完，本次需 {coin_cost} 球迷币，余额不足"
            )
        return BillingDecision(
            charge_coins=coin_cost,
            used_free_quota=False,
            free_remaining=0,
            daily_free_limit=limit,
            mode=mode,
            force_refresh=force_refresh,
        )

    def _get_usage_row(self, user_id: int, d: date, for_update: bool = False) -> AiUsageDaily | None:
        q = self.db.query(AiUsageDaily).filter(AiUsageDaily.user_id == user_id, AiUsageDaily.usage_date == d)
        if for_update:
            q = q.with_for_update()
        return q.first()

    def _inc_free_used(self, user_id: int) -> None:
        row = self._get_usage_row(user_id, _utcnow().date(), for_update=True)
        if not row:
            row = AiUsageDaily(user_id=user_id, usage_date=_utcnow().date(), free_used=1, paid_count=0, tokens_total=0)
            self.db.add(row)
        else:
            row.free_used += 1

    def _inc_paid_count(self, user_id: int) -> None:
        row = self._get_usage_row(user_id, _utcnow().date(), for_update=True)
        if not row:
            row = AiUsageDaily(user_id=user_id, usage_date=_utcnow().date(), free_used=0, paid_count=1, tokens_total=0)
            self.db.add(row)
        else:
            row.paid_count += 1
