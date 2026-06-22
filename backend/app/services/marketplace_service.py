"""球星卡交易行（合规·可用积分计价二级市场）。

一口价 / 英式竞拍；成交抽积分手续费(sink)；行情中心(地板价/成交量/历史曲线)；
结算经 AVATA 托管账户间转移。人民币永不参与二级。
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import (
    CardListing,
    CardTransferLog,
    CollectibleCard,
    MarketBid,
    MarketPricePoint,
    User,
    UserCollectibleCard,
)
from app.db.repositories.user_repository import WalletRepository
from app.services.card_asset_service import CardAssetService

MARKET_DISCLAIMER = (
    "行情以可用积分计价，为站内虚拟收藏体验数据，无现金价值、不可提现，不构成任何投资建议。"
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _unique_ref_id(base: int) -> int:
    """生成唯一 ledger ref_id，避免同 listing 多次退款被幂等拦截。"""
    return int(base * 1_000_000 + (int(time.time() * 1000) % 1_000_000))


class MarketplaceService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.wallet = WalletRepository(db)
        self.asset = CardAssetService(db)

    def _lock_user(self, user_id: int) -> User | None:
        return self.db.query(User).filter(User.id == user_id).with_for_update().first()

    # ----------------------- 挂牌 -----------------------
    def create_listing(
        self,
        user: User,
        user_card_id: int,
        *,
        list_type: str = "fixed",
        price_points: int,
        duration_hours: int | None = None,
    ) -> dict[str, Any]:
        self.asset.assert_real_name(user)
        if list_type not in ("fixed", "auction"):
            raise BadRequestError("挂牌类型不合法")
        lo, hi = self.settings.asset_listing_min_points, self.settings.asset_listing_max_points
        if price_points < lo or price_points > hi:
            raise BadRequestError(f"价格区间 {lo}-{hi} 可用积分")

        row = self.asset.owned_row(user, user_card_id, for_update=True)
        self.asset.assert_tradable(row)
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            raise NotFoundError("卡牌不存在")

        hours = duration_hours or self.settings.asset_listing_default_hours
        expires = _utcnow() + timedelta(hours=max(1, min(hours, 24 * 14)))
        listing = CardListing(
            seller_id=user.id,
            user_card_id=row.id,
            card_id=row.card_id,
            list_type=list_type,
            price_points=price_points,
            min_increment=self.settings.asset_auction_min_increment if list_type == "auction" else 0,
            status="active",
            expires_at=expires,
        )
        self.db.add(listing)
        row.lock_state = "listed"
        self.db.flush()
        self.db.commit()
        return {"ok": True, "listing_id": listing.id, "expires_at": expires.isoformat()}

    def cancel_listing(self, user: User, listing_id: int) -> dict[str, Any]:
        listing = (
            self.db.query(CardListing)
            .filter(CardListing.id == listing_id, CardListing.seller_id == user.id)
            .with_for_update()
            .first()
        )
        if not listing:
            raise NotFoundError("挂牌不存在")
        if listing.status != "active":
            raise BadRequestError("该挂牌已结束")
        if listing.list_type == "auction" and listing.current_bidder_id:
            self._refund_current_bid(listing)
        listing.status = "cancelled"
        row = self.db.get(UserCollectibleCard, listing.user_card_id)
        if row and row.lock_state == "listed":
            row.lock_state = "none"
        self.db.commit()
        return {"ok": True}

    # ----------------------- 一口价购买 -----------------------
    def buy_now(self, buyer: User, listing_id: int) -> dict[str, Any]:
        self.asset.assert_real_name(buyer)
        listing = (
            self.db.query(CardListing)
            .filter(CardListing.id == listing_id)
            .with_for_update()
            .first()
        )
        if not listing or listing.status != "active":
            raise BadRequestError("该挂牌不可购买")
        if listing.list_type != "fixed":
            raise BadRequestError("竞拍商品请出价")
        if listing.seller_id == buyer.id:
            raise BadRequestError("不能购买自己的挂牌")
        if listing.expires_at and listing.expires_at <= _utcnow():
            raise BadRequestError("挂牌已过期")

        buyer_locked = self._lock_user(buyer.id)
        if not buyer_locked:
            raise NotFoundError("买家不存在")
        seller = self._lock_user(listing.seller_id)
        if not seller:
            raise NotFoundError("卖家不存在")

        price = listing.price_points
        if (buyer_locked.redeem_points or 0) < price:
            raise BadRequestError("可用积分不足")

        row = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.id == listing.user_card_id)
            .with_for_update()
            .first()
        )
        if not row or row.user_id != seller.id or row.lock_state != "listed":
            raise BadRequestError("卡牌状态已变更，无法成交")

        self._settle_sale(listing, seller, buyer_locked, row, price)
        self.db.commit()
        return {"ok": True, "price_points": price, "notice": "购买成功（可用积分结算，无现金价值）"}

    # ----------------------- 竞拍出价 -----------------------
    def place_bid(self, bidder: User, listing_id: int, amount: int) -> dict[str, Any]:
        self.asset.assert_real_name(bidder)
        listing = (
            self.db.query(CardListing)
            .filter(CardListing.id == listing_id)
            .with_for_update()
            .first()
        )
        if not listing or listing.status != "active":
            raise BadRequestError("该竞拍不可出价")
        if listing.list_type != "auction":
            raise BadRequestError("一口价商品请直接购买")
        if listing.seller_id == bidder.id:
            raise BadRequestError("不能给自己的拍品出价")
        if listing.expires_at and listing.expires_at <= _utcnow():
            raise BadRequestError("竞拍已结束")

        floor = listing.current_bid or listing.price_points
        min_next = floor + (listing.min_increment if listing.current_bid else 0)
        if amount < min_next:
            raise BadRequestError(f"出价需 ≥ {min_next} 可用积分")
        bidder_locked = self._lock_user(bidder.id)
        if not bidder_locked:
            raise NotFoundError("用户不存在")
        if (bidder_locked.redeem_points or 0) < amount:
            raise BadRequestError("可用积分不足")

        # 退还上一位出价人（含同一人加价场景）
        if listing.current_bidder_id and listing.current_bid:
            self._refund_current_bid(listing)

        # 先创建出价记录，用 bid.id 作为 ledger ref_id 保证幂等唯一
        bid_row = MarketBid(listing_id=listing.id, bidder_id=bidder_locked.id, amount_points=amount, status="active")
        self.db.add(bid_row)
        self.db.flush()
        self.wallet.deduct_redeem_points(
            bidder_locked, amount, "market_bid_escrow", "market_bid", bid_row.id
        )
        listing.current_bid = amount
        listing.current_bidder_id = bidder_locked.id

        if listing.expires_at and (listing.expires_at - _utcnow()).total_seconds() < 120:
            listing.expires_at = _utcnow() + timedelta(minutes=2)
        self.db.commit()
        return {
            "ok": True,
            "current_bid": amount,
            "expires_at": listing.expires_at.isoformat() if listing.expires_at else None,
        }

    def _refund_current_bid(self, listing: CardListing) -> None:
        if not listing.current_bidder_id or not listing.current_bid:
            return
        prev = self._lock_user(listing.current_bidder_id)
        if not prev:
            return
        active_bid = (
            self.db.query(MarketBid)
            .filter(
                MarketBid.listing_id == listing.id,
                MarketBid.bidder_id == listing.current_bidder_id,
                MarketBid.status == "active",
            )
            .order_by(MarketBid.id.desc())
            .first()
        )
        ref_id = active_bid.id if active_bid else _unique_ref_id(listing.id)
        self.wallet.add_redeem_points(
            prev, listing.current_bid, "market_bid_refund", "market_bid", ref_id
        )
        if active_bid:
            active_bid.status = "outbid"
        else:
            self.db.query(MarketBid).filter(
                MarketBid.listing_id == listing.id,
                MarketBid.bidder_id == listing.current_bidder_id,
                MarketBid.status == "active",
            ).update({MarketBid.status: "outbid"})

    def _expire_auction(self, listing: CardListing) -> None:
        """流拍：退还当前出价托管并解锁卡牌。"""
        if listing.current_bidder_id and listing.current_bid:
            self._refund_current_bid(listing)
            listing.current_bid = 0
            listing.current_bidder_id = None
        listing.status = "expired"
        row = self.db.get(UserCollectibleCard, listing.user_card_id)
        if row and row.lock_state == "listed":
            row.lock_state = "none"

    def _expire_fixed(self, listing: CardListing) -> None:
        """一口价到期：解锁卡牌。"""
        listing.status = "expired"
        row = self.db.get(UserCollectibleCard, listing.user_card_id)
        if row and row.lock_state == "listed":
            row.lock_state = "none"

    def expire_stale_listings(self, limit: int = 100) -> dict[str, int]:
        """到期一口价自动下架（scheduler 周期调用）。"""
        now = _utcnow()
        ids = [
            r[0]
            for r in (
                self.db.query(CardListing.id)
                .filter(
                    CardListing.status == "active",
                    CardListing.list_type == "fixed",
                    CardListing.expires_at.isnot(None),
                    CardListing.expires_at <= now,
                )
                .limit(limit)
                .all()
            )
        ]
        expired = 0
        for lid in ids:
            locked = (
                self.db.query(CardListing)
                .filter(CardListing.id == lid)
                .with_for_update()
                .first()
            )
            if not locked or locked.status != "active" or locked.list_type != "fixed":
                continue
            if locked.expires_at and locked.expires_at <= now:
                self._expire_fixed(locked)
                expired += 1
        if ids:
            self.db.commit()
        return {"expired": expired}

    def settle_expired_auctions(self, limit: int = 50) -> dict[str, int]:
        """结算到期竞拍（scheduler 周期调用）。"""
        now = _utcnow()
        ids = [
            r[0]
            for r in (
                self.db.query(CardListing.id)
                .filter(
                    CardListing.status == "active",
                    CardListing.list_type == "auction",
                    CardListing.expires_at.isnot(None),
                    CardListing.expires_at <= now,
                )
                .limit(limit)
                .all()
            )
        ]
        settled = expired = 0
        for lid in ids:
            locked = (
                self.db.query(CardListing)
                .filter(CardListing.id == lid)
                .with_for_update()
                .first()
            )
            if not locked or locked.status != "active":
                continue
            if locked.current_bidder_id and locked.current_bid:
                seller = self._lock_user(locked.seller_id)
                winner = self._lock_user(locked.current_bidder_id)
                row = (
                    self.db.query(UserCollectibleCard)
                    .filter(UserCollectibleCard.id == locked.user_card_id)
                    .with_for_update()
                    .first()
                )
                if seller and winner and row and row.user_id == seller.id and row.lock_state == "listed":
                    try:
                        self._settle_auction_win(locked, seller, winner, row)
                        settled += 1
                        continue
                    except BadRequestError:
                        self._expire_auction(locked)
                        expired += 1
                        continue
            self._expire_auction(locked)
            expired += 1
        if ids:
            self.db.commit()
        return {"settled": settled, "expired": expired}

    # ----------------------- 成交结算（公共） -----------------------
    def _fee(self, price: int) -> int:
        return int(round(price * self.settings.asset_market_fee_pct))

    def _settle_sale(
        self, listing: CardListing, seller: User, buyer: User, row: UserCollectibleCard, price: int
    ) -> None:
        existing = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == buyer.id, UserCollectibleCard.card_id == row.card_id)
            .first()
        )
        if existing:
            raise BadRequestError("你已拥有该卡，暂不支持购买重复卡")

        self.wallet.deduct_redeem_points(buyer, price, "market_buy", "listing", listing.id)
        fee = self._fee(price)
        seller_gain = max(0, price - fee)
        if seller_gain > 0:
            self.wallet.add_redeem_points(seller, seller_gain, "market_sale", "listing", listing.id)

        row.lock_state = "none"
        self.asset.transfer_ownership(
            row,
            seller,
            buyer,
            kind="trade",
            points_amount=price,
            fee_points=fee,
            apply_cooldown=True,
            record_price=True,
        )
        listing.status = "sold"
        listing.sold_to_id = buyer.id
        listing.sold_price = price
        self.asset.evaluate_achievements(buyer)
        self.asset.evaluate_achievements(seller)

    def _settle_auction_win(
        self, listing: CardListing, seller: User, winner: User, row: UserCollectibleCard
    ) -> None:
        price = listing.current_bid or 0
        if price <= 0:
            raise BadRequestError("无有效出价")

        existing = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.user_id == winner.id, UserCollectibleCard.card_id == row.card_id)
            .first()
        )
        if existing:
            self._refund_current_bid(listing)
            raise BadRequestError("中标者已拥有该卡，流拍处理")

        fee = self._fee(price)
        seller_gain = max(0, price - fee)
        if seller_gain > 0:
            self.wallet.add_redeem_points(seller, seller_gain, "market_sale", "listing", listing.id)

        row.lock_state = "none"
        self.asset.transfer_ownership(
            row,
            seller,
            winner,
            kind="trade",
            points_amount=price,
            fee_points=fee,
            apply_cooldown=True,
            record_price=True,
        )
        listing.status = "sold"
        listing.sold_to_id = winner.id
        listing.sold_price = price
        self.db.query(MarketBid).filter(
            MarketBid.listing_id == listing.id,
            MarketBid.bidder_id == winner.id,
            MarketBid.status == "active",
        ).update({MarketBid.status: "won"})
        self.asset.evaluate_achievements(winner)
        self.asset.evaluate_achievements(seller)

    # ----------------------- 浏览 / 行情 -----------------------
    def browse(
        self,
        *,
        rarity: str | None = None,
        series: str | None = None,
        list_type: str | None = None,
        sort: str = "recent",
        page: int = 1,
        limit: int = 24,
    ) -> dict[str, Any]:
        now = _utcnow()
        q = (
            self.db.query(CardListing, CollectibleCard)
            .join(CollectibleCard, CardListing.card_id == CollectibleCard.id)
            .filter(
                CardListing.status == "active",
                or_(CardListing.expires_at.is_(None), CardListing.expires_at > now),
            )
        )
        if rarity:
            q = q.filter(CollectibleCard.rarity == rarity)
        if series:
            q = q.filter(CollectibleCard.series == series)
        if list_type:
            q = q.filter(CardListing.list_type == list_type)
        if sort == "price_asc":
            q = q.order_by(func.coalesce(func.nullif(CardListing.current_bid, 0), CardListing.price_points).asc())
        elif sort == "price_desc":
            q = q.order_by(func.coalesce(func.nullif(CardListing.current_bid, 0), CardListing.price_points).desc())
        elif sort == "ending":
            q = q.order_by(CardListing.expires_at.asc())
        else:
            q = q.order_by(CardListing.id.desc())
        total = q.count()
        page = max(1, page)
        limit = max(1, min(limit, 60))
        rows = q.offset((page - 1) * limit).limit(limit).all()

        uc_ids = [listing.user_card_id for listing, _ in rows]
        uc_map: dict[int, UserCollectibleCard] = {}
        if uc_ids:
            uc_map = {r.id: r for r in self.db.query(UserCollectibleCard).filter(UserCollectibleCard.id.in_(uc_ids)).all()}

        items = [self._listing_brief(listing, card, uc_map.get(listing.user_card_id)) for listing, card in rows]
        return {
            "items": items,
            "total": total,
            "page": page,
            "has_more": page * limit < total,
            "disclaimer": MARKET_DISCLAIMER,
        }

    def _listing_brief(self, listing: CardListing, card: CollectibleCard, row: UserCollectibleCard | None) -> dict:
        cur = listing.current_bid or listing.price_points
        return {
            "listing_id": listing.id,
            "list_type": listing.list_type,
            "card_code": card.code,
            "card_name": card.name,
            "rarity": card.rarity,
            "series": card.series,
            "image_url": card.image_url,
            "price_points": listing.price_points,
            "current_bid": listing.current_bid,
            "current_price": cur,
            "min_increment": listing.min_increment,
            "star": row.star if row else 1,
            "serial_no": row.serial_no if row else None,
            "mint_total": row.mint_total if row else None,
            "expires_at": listing.expires_at.isoformat() if listing.expires_at else None,
            "seller_id": listing.seller_id,
        }

    def listing_detail(self, listing_id: int) -> dict[str, Any]:
        listing = self.db.get(CardListing, listing_id)
        if not listing:
            raise NotFoundError("挂牌不存在")
        card = self.db.get(CollectibleCard, listing.card_id)
        row = self.db.get(UserCollectibleCard, listing.user_card_id)
        brief = self._listing_brief(listing, card, row)
        brief["status"] = listing.status
        brief["market"] = self.card_market_data(listing.card_id)
        brief["disclaimer"] = MARKET_DISCLAIMER
        bids = (
            self.db.query(MarketBid)
            .filter(MarketBid.listing_id == listing_id)
            .order_by(MarketBid.id.desc())
            .limit(10)
            .all()
        )
        brief["recent_bids"] = [
            {"amount": b.amount_points, "at": b.created_at.isoformat() if b.created_at else None}
            for b in bids
        ]
        return brief

    def card_market_data(self, card_id: int) -> dict[str, Any]:
        now = _utcnow()
        day_ago = now - timedelta(hours=24)
        floor = (
            self.db.query(
                func.min(func.coalesce(func.nullif(CardListing.current_bid, 0), CardListing.price_points))
            )
            .filter(
                CardListing.card_id == card_id,
                CardListing.status == "active",
                or_(CardListing.expires_at.is_(None), CardListing.expires_at > now),
            )
            .scalar()
        )
        active_count = (
            self.db.query(func.count(CardListing.id))
            .filter(
                CardListing.card_id == card_id,
                CardListing.status == "active",
                or_(CardListing.expires_at.is_(None), CardListing.expires_at > now),
            )
            .scalar()
            or 0
        )
        vol24 = (
            self.db.query(func.coalesce(func.sum(MarketPricePoint.price_points), 0))
            .filter(
                MarketPricePoint.card_id == card_id,
                MarketPricePoint.kind == "trade",
                MarketPricePoint.created_at >= day_ago,
            )
            .scalar()
            or 0
        )
        trades24 = (
            self.db.query(func.count(MarketPricePoint.id))
            .filter(
                MarketPricePoint.card_id == card_id,
                MarketPricePoint.kind == "trade",
                MarketPricePoint.created_at >= day_ago,
            )
            .scalar()
            or 0
        )
        history = (
            self.db.query(MarketPricePoint)
            .filter(MarketPricePoint.card_id == card_id, MarketPricePoint.kind.in_(["trade", "primary"]))
            .order_by(MarketPricePoint.id.desc())
            .limit(60)
            .all()
        )
        history_points = [
            {"price": h.price_points, "at": h.created_at.isoformat() if h.created_at else None}
            for h in reversed(history)
        ]
        last_price = history_points[-1]["price"] if history_points else None
        card = self.db.get(CollectibleCard, card_id)
        buyback_floor = self.settings.asset_buyback_floor_map.get(card.rarity, 0) if card else 0
        return {
            "floor_price": int(floor) if floor else None,
            "active_listings": int(active_count),
            "volume_24h": int(vol24),
            "trades_24h": int(trades24),
            "last_price": last_price,
            "history": history_points,
            "buyback_floor": buyback_floor,
            "currency": "redeem_points",
        }

    def my_listings(self, user: User) -> list[dict[str, Any]]:
        now = _utcnow()
        rows = (
            self.db.query(CardListing, CollectibleCard)
            .join(CollectibleCard, CardListing.card_id == CollectibleCard.id)
            .filter(
                CardListing.seller_id == user.id,
                CardListing.status == "active",
                or_(CardListing.expires_at.is_(None), CardListing.expires_at > now),
            )
            .order_by(CardListing.id.desc())
            .all()
        )
        uc_ids = [listing.user_card_id for listing, _ in rows]
        uc_map: dict[int, UserCollectibleCard] = {}
        if uc_ids:
            uc_map = {r.id: r for r in self.db.query(UserCollectibleCard).filter(UserCollectibleCard.id.in_(uc_ids)).all()}
        return [self._listing_brief(listing, card, uc_map.get(listing.user_card_id)) for listing, card in rows]
