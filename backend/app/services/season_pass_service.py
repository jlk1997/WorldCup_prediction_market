"""Season pass daily coin grant."""

from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.db.models.commerce import Product, User
from app.db.repositories.user_repository import WalletRepository
from app.services.ai_billing_service import _has_active_pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class SeasonPassService:
    def __init__(self, db: Session):
        self.db = db
        self.wallet = WalletRepository(db)

    def _apply_daily_grant(self, user: User, today: date | None = None) -> int:
        from app.core.config import get_settings

        settings = get_settings()
        today = today or _utcnow().date()
        if not _has_active_pass(user):
            return 0
        if user.last_season_pass_daily == today:
            return 0
        coins = settings.season_pass_daily_coins
        self.wallet.add_coins(user, coins, "season_pass_daily", "user", user.id)
        user.last_season_pass_daily = today
        return coins

    def grant_daily_if_eligible(self, user: User, *, commit: bool = True) -> dict:
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            return {"granted": 0, "reason": "no_user"}
        coins = self._apply_daily_grant(locked)
        if coins <= 0:
            return {"granted": 0, "reason": "no_pass" if not _has_active_pass(locked) else "already_claimed"}
        if commit:
            self.db.commit()
            self.db.refresh(locked)
        return {"granted": coins, "reason": "ok", "fan_coins": locked.fan_coins}

    def grant_daily_batch(self, limit: int = 300) -> dict:
        today = _utcnow().date()
        now = _utcnow()
        rows = (
            self.db.query(User)
            .filter(
                User.has_season_pass.is_(True),
                User.season_pass_until.isnot(None),
                User.season_pass_until > now,
            )
            .limit(limit)
            .all()
        )
        granted_users = 0
        total_coins = 0
        for user in rows:
            if user.last_season_pass_daily == today:
                continue
            locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
            if not locked:
                continue
            coins = self._apply_daily_grant(locked, today)
            if coins > 0:
                granted_users += 1
                total_coins += coins
                self.db.commit()
        return {"granted_users": granted_users, "total_coins": total_coins, "scanned": len(rows)}

    def apply_cosmetic_purchase(self, user: User, product_or_sku: Product | str) -> None:
        if isinstance(product_or_sku, Product):
            product = product_or_sku
        else:
            product = self.db.query(Product).filter(Product.sku == product_or_sku).first()
            if not product:
                if product_or_sku == "team_cosmetic":
                    user.avatar_frame = "gold_wc"
                    user.theme_key = "team_spirit"
                    self.db.flush()
                return

        payload = product.grant_payload or {}
        if not payload and product.sku == "team_cosmetic":
            payload = {"avatar_frame": "gold_wc", "theme_key": "team_spirit"}
        if not payload and product.product_type != "cosmetic":
            return

        if frame := payload.get("avatar_frame"):
            user.avatar_frame = str(frame)
        if theme := payload.get("theme_key"):
            user.theme_key = str(theme)
        extra = payload.get("extra_free_predict_daily")
        if extra:
            user.extra_free_predict_daily = (user.extra_free_predict_daily or 0) + int(extra)
        self.db.flush()
