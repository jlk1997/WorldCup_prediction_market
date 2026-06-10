from datetime import date, datetime

from sqlalchemy.orm import Session

from app.db.models.commerce import CoinLedger, PointLedger, User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, user_id: int) -> User | None:
        return self.db.get(User, user_id)

    def get_by_email(self, email: str) -> User | None:
        return self.db.query(User).filter(User.email == email).first()

    def create(self, email: str, nickname: str, fan_coins: int = 0) -> User:
        user = User(email=email, nickname=nickname, fan_coins=fan_coins)
        self.db.add(user)
        self.db.flush()
        return user

    def update_profile(
        self,
        user: User,
        nickname: str | None = None,
        favorite_team_id: int | None = None,
        *,
        commit: bool = True,
    ) -> User:
        if nickname is not None:
            user.nickname = nickname[:100]
        if favorite_team_id is not None:
            user.favorite_team_id = favorite_team_id if favorite_team_id > 0 else None
        if commit:
            self.db.commit()
            self.db.refresh(user)
        return user

    def change_nickname(self, user: User, new_nickname: str) -> User:
        from app.core.config import get_settings
        from app.core.exceptions import BadRequestError

        settings = get_settings()
        new_nickname = new_nickname.strip()
        if not new_nickname:
            raise BadRequestError("昵称不能为空")
        if new_nickname == user.nickname:
            return user
        locked = self.db.query(User).filter(User.id == user.id).with_for_update().first()
        if not locked:
            raise BadRequestError("用户不存在")
        cost = settings.nickname_change_cost
        wallet = WalletRepository(self.db)
        wallet.deduct_coins(locked, cost, "nickname_change", "user", locked.id)
        locked.nickname = new_nickname[:100]
        self.db.commit()
        self.db.refresh(locked)
        return locked


class WalletRepository:
    def __init__(self, db: Session):
        self.db = db

    def _coin_ledger_exists(
        self, user_id: int, reason: str, ref_type: str | None, ref_id: int | None
    ) -> bool:
        if ref_id is None:
            return False
        return (
            self.db.query(CoinLedger.id)
            .filter(
                CoinLedger.user_id == user_id,
                CoinLedger.reason == reason,
                CoinLedger.ref_type == ref_type,
                CoinLedger.ref_id == ref_id,
            )
            .first()
            is not None
        )

    def _point_ledger_exists(
        self,
        user_id: int,
        reason: str,
        ref_type: str | None,
        ref_id: int | None,
        bucket: str,
    ) -> bool:
        if ref_id is None:
            return False
        return (
            self.db.query(PointLedger.id)
            .filter(
                PointLedger.user_id == user_id,
                PointLedger.reason == reason,
                PointLedger.ref_type == ref_type,
                PointLedger.ref_id == ref_id,
                PointLedger.point_bucket == bucket,
            )
            .first()
            is not None
        )

    def add_coins(self, user: User, delta: int, reason: str, ref_type: str | None = None, ref_id: int | None = None) -> User:
        if delta == 0:
            return user
        if self._coin_ledger_exists(user.id, reason, ref_type, ref_id):
            return user
        user.fan_coins = max(0, (user.fan_coins or 0) + delta)
        self.db.add(
            CoinLedger(
                user_id=user.id,
                delta=delta,
                balance_after=user.fan_coins,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
            )
        )
        self.db.flush()
        return user

    def deduct_coins(self, user: User, amount: int, reason: str, ref_type: str | None = None, ref_id: int | None = None) -> User:
        if amount <= 0:
            return user
        if (user.fan_coins or 0) < amount:
            from app.core.exceptions import BadRequestError

            raise BadRequestError("球迷币不足")
        user.fan_coins -= amount
        self.db.add(
            CoinLedger(
                user_id=user.id,
                delta=-amount,
                balance_after=user.fan_coins,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
            )
        )
        return user

    def add_points(self, user: User, delta: int, reason: str, ref_type: str | None = None, ref_id: int | None = None) -> User:
        """Alias for cumulative season points (never decreases on redeem)."""
        return self.add_season_points(user, delta, reason, ref_type, ref_id)

    def add_season_points(
        self, user: User, delta: int, reason: str, ref_type: str | None = None, ref_id: int | None = None
    ) -> User:
        if delta == 0:
            return user
        if self._point_ledger_exists(user.id, reason, ref_type, ref_id, "season"):
            return user
        user.season_points = max(0, (user.season_points or 0) + delta)
        self.db.add(
            PointLedger(
                user_id=user.id,
                delta=delta,
                balance_after=user.season_points,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
                point_bucket="season",
            )
        )
        self.db.flush()
        return user

    def add_redeem_points(
        self, user: User, delta: int, reason: str, ref_type: str | None = None, ref_id: int | None = None
    ) -> User:
        if delta == 0:
            return user
        if delta > 0 and self._point_ledger_exists(user.id, reason, ref_type, ref_id, "redeem"):
            return user
        user.redeem_points = max(0, (user.redeem_points or 0) + delta)
        self.db.add(
            PointLedger(
                user_id=user.id,
                delta=delta,
                balance_after=user.redeem_points,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
                point_bucket="redeem",
            )
        )
        self.db.flush()
        return user

    def deduct_redeem_points(
        self, user: User, amount: int, reason: str, ref_type: str | None = None, ref_id: int | None = None
    ) -> User:
        if amount <= 0:
            return user
        if (user.redeem_points or 0) < amount:
            from app.core.exceptions import BadRequestError

            raise BadRequestError("可用积分不足")
        user.redeem_points -= amount
        self.db.add(
            PointLedger(
                user_id=user.id,
                delta=-amount,
                balance_after=user.redeem_points,
                reason=reason,
                ref_type=ref_type,
                ref_id=ref_id,
                point_bucket="redeem",
            )
        )
        return user

    def list_point_ledger(
        self, user_id: int, bucket: str | None = None, limit: int = 50
    ) -> list[dict]:
        q = self.db.query(PointLedger).filter(PointLedger.user_id == user_id)
        if bucket:
            q = q.filter(PointLedger.point_bucket == bucket)
        rows = q.order_by(PointLedger.id.desc()).limit(min(limit, 100)).all()
        return [
            {
                "id": r.id,
                "delta": r.delta,
                "balance_after": r.balance_after,
                "reason": r.reason,
                "point_bucket": r.point_bucket,
                "ref_type": r.ref_type,
                "ref_id": r.ref_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]

    def count_free_predictions_today(self, user_id: int, today: date) -> int:
        from app.db.models.commerce import GamePrediction

        start = datetime.combine(today, datetime.min.time())
        return (
            self.db.query(GamePrediction)
            .filter(
                GamePrediction.user_id == user_id,
                GamePrediction.is_free.is_(True),
                GamePrediction.created_at >= start,
            )
            .count()
        )

    def list_coin_ledger(self, user_id: int, limit: int = 50) -> list[dict]:
        rows = (
            self.db.query(CoinLedger)
            .filter(CoinLedger.user_id == user_id)
            .order_by(CoinLedger.id.desc())
            .limit(min(limit, 100))
            .all()
        )
        return [
            {
                "id": r.id,
                "delta": r.delta,
                "balance_after": r.balance_after,
                "reason": r.reason,
                "ref_type": r.ref_type,
                "ref_id": r.ref_id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
