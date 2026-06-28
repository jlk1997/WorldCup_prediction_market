"""文昌链 AVATA integration for collectible NFT minting."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import CollectibleCard, User, UserChainAccount, UserCollectibleCard
from app.integrations.avata_client import AvataClient, AvataError

logger = logging.getLogger(__name__)

CHAIN_STATUS_NONE = "none"
CHAIN_STATUS_PENDING = "pending"
CHAIN_STATUS_MINTING = "minting"
CHAIN_STATUS_MINTED = "minted"
CHAIN_STATUS_FAILED = "failed"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class CollectibleChainService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.client = AvataClient()

    @property
    def active(self) -> bool:
        return self.settings.avata_active

    def queue_mint(self, user: User, row: UserCollectibleCard, card: CollectibleCard) -> None:
        if not self.active:
            return
        if row.chain_status in (CHAIN_STATUS_MINTING, CHAIN_STATUS_MINTED, CHAIN_STATUS_PENDING):
            return
        row.chain_status = CHAIN_STATUS_PENDING
        row.updated_at = _utcnow()
        self.db.flush()

    def process_pending(self, limit: int = 20) -> dict[str, int]:
        if not self.active:
            return {"processed": 0, "minted": 0, "failed": 0, "expired": 0}

        expired = self._expire_stale_pending()
        rows = (
            self.db.query(UserCollectibleCard, CollectibleCard, User)
            .join(CollectibleCard, UserCollectibleCard.card_id == CollectibleCard.id)
            .join(User, UserCollectibleCard.user_id == User.id)
            .filter(UserCollectibleCard.chain_status.in_([CHAIN_STATUS_PENDING, CHAIN_STATUS_MINTING]))
            .order_by(UserCollectibleCard.id.asc())
            .limit(limit)
            .all()
        )
        minted = failed = processed = 0
        for row, card, user in rows:
            processed += 1
            try:
                if row.chain_status == CHAIN_STATUS_MINTING and row.chain_operation_id:
                    if self._poll_mint(row):
                        minted += 1
                    continue
                if self._start_mint(user, row, card):
                    if row.chain_status == CHAIN_STATUS_MINTED:
                        minted += 1
                    elif row.chain_status == CHAIN_STATUS_FAILED:
                        failed += 1
            except Exception:
                logger.exception("Collectible chain mint failed row=%s", row.id)
                row.chain_status = CHAIN_STATUS_FAILED
                row.chain_error = "internal_error"
                failed += 1
        if processed or expired:
            self.db.commit()
        return {"processed": processed, "minted": minted, "failed": failed, "expired": expired}

    def _expire_stale_pending(self) -> int:
        """长时间 pending/minting 标记 failed，允许用户 retry。"""
        from datetime import timedelta

        from sqlalchemy import func

        cutoff = _utcnow() - timedelta(minutes=self.settings.chain_pending_timeout_minutes)
        ts = func.coalesce(UserCollectibleCard.updated_at, UserCollectibleCard.obtained_at)
        rows = (
            self.db.query(UserCollectibleCard)
            .filter(
                UserCollectibleCard.chain_status.in_([CHAIN_STATUS_PENDING, CHAIN_STATUS_MINTING]),
                ts < cutoff,
            )
            .all()
        )
        for row in rows:
            row.chain_status = CHAIN_STATUS_FAILED
            row.chain_error = "mint_timeout"
        return len(rows)

    def refresh_mint_status(self, user: User, user_card_id: int) -> dict[str, Any]:
        """轮询 minting 状态或触发 pending 处理（用户主动刷新）。"""
        if not self.active:
            raise BadRequestError("链上功能未启用")
        row = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.id == user_card_id, UserCollectibleCard.user_id == user.id)
            .with_for_update()
            .first()
        )
        if not row:
            raise NotFoundError("卡牌不存在")
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            raise NotFoundError("卡牌不存在")
        if row.chain_status == CHAIN_STATUS_MINTING and row.chain_operation_id:
            self._poll_mint(row)
        elif row.chain_status == CHAIN_STATUS_PENDING:
            self._start_mint(user, row, card)
        self.db.commit()
        return self.chain_brief(row) or {"status": row.chain_status}

    def ensure_user_chain_account(self, user: User) -> UserChainAccount | None:
        if not self.active:
            return None
        acct = self.db.query(UserChainAccount).filter(UserChainAccount.user_id == user.id).first()
        if acct and acct.status == "active" and acct.native_address:
            return acct
        if not acct:
            acct = UserChainAccount(user_id=user.id, chain_name=self.settings.avata_chain_name)
            self.db.add(acct)
            self.db.flush()

        if acct.status == "pending" and acct.operation_id and not acct.native_address:
            self._poll_account_creation(acct)
            if acct.native_address:
                acct.status = "active"
                return acct

        if acct.native_address and acct.status != "active":
            acct.status = "active"
            return acct

        op = self.client.new_operation_id(f"u{user.id}")
        acct.operation_id = op
        acct.status = "pending"
        try:
            resp = self.client.create_accounts(count=1, operation_id=op)
            addresses = (resp.get("data") or {}).get("addresses") or []
            if addresses:
                acct.native_address = addresses[0].get("native_address")
                acct.hex_address = addresses[0].get("hex_address")
                acct.status = "active"
            else:
                acct.status = "pending"
        except AvataError as exc:
            logger.warning("AVATA create account failed user=%s: %s", user.id, exc)
            acct.status = "failed"
        self.db.flush()
        return acct if acct.native_address else None

    def _poll_account_creation(self, acct: UserChainAccount) -> None:
        if not acct.operation_id:
            return
        try:
            resp = self.client.query_tx(acct.operation_id)
            data = resp.get("data") or {}
            status = data.get("status")
            if status == 2:
                acct.status = "failed"
                return
            if status != 1:
                return
            addr = self._extract_address_from_tx(data)
            if addr:
                acct.native_address = addr
                acct.hex_address = data.get("hex_address") or acct.hex_address
                acct.status = "active"
                return
            # 交易成功但未返回地址：清空 operation 以便下次 ensure 重新创建
            acct.operation_id = None
            acct.status = "pending"
        except AvataError:
            return

    @staticmethod
    def _extract_address_from_tx(data: dict[str, Any]) -> str | None:
        if data.get("native_address"):
            return str(data["native_address"])
        accounts = data.get("accounts") or data.get("addresses")
        if isinstance(accounts, list) and accounts:
            first = accounts[0]
            if isinstance(first, dict):
                return first.get("native_address") or first.get("address")
            if isinstance(first, str):
                return first
        account = data.get("account")
        if isinstance(account, dict):
            return account.get("native_address") or account.get("address")
        return None

    def _resolve_class_id(self) -> str | None:
        if self.settings.avata_nft_class_id:
            return self.settings.avata_nft_class_id
        return None

    def _resolve_class_owner(self) -> str | None:
        owner = (self.settings.avata_class_owner or "").strip()
        if owner:
            return owner
        return None

    def _ensure_class_owner(self) -> str | None:
        owner = self._resolve_class_owner()
        if owner:
            return owner
        try:
            op = self.client.new_operation_id("platform")
            resp = self.client.create_accounts(count=1, operation_id=op)
            addresses = (resp.get("data") or {}).get("addresses") or []
            owner = addresses[0].get("native_address") if addresses else None
            if owner:
                logger.info(
                    "Created platform AVATA chain account for NFT class owner=%s "
                    "(set AVATA_CLASS_OWNER in env to reuse)",
                    owner,
                )
            return owner
        except AvataError as exc:
            logger.error("Failed to create platform AVATA account: %s", exc)
            return None

    def _ensure_class_id(self) -> str | None:
        class_id = self._resolve_class_id()
        if class_id:
            return class_id
        owner = self._ensure_class_owner()
        if not owner:
            return None
        try:
            op = self.client.new_operation_id("class")
            resp = self.client.create_nft_class(
                self.settings.avata_nft_class_name,
                owner=owner,
                description="最后一舞 · 世界杯2026 合规数字藏品（玩法获得，不可交易）",
                operation_id=op,
            )
            data = resp.get("data") or {}
            class_id = data.get("class_id")
            if class_id:
                logger.info("Created AVATA NFT class_id=%s (set AVATA_NFT_CLASS_ID in env)", class_id)
                return class_id
            # Async: poll operation for class_id
            for _ in range(10):
                tx = self.client.query_tx(op)
                tx_data = tx.get("data") or {}
                if tx_data.get("status") == 1:
                    nft = tx_data.get("nft") or {}
                    class_id = nft.get("class_id")
                    if class_id:
                        logger.info("AVATA NFT class_id=%s (set AVATA_NFT_CLASS_ID in env)", class_id)
                        return class_id
                    break
                if tx_data.get("status") == 2:
                    break
                time.sleep(1.5)
            return None
        except AvataError as exc:
            logger.error("Failed to create AVATA NFT class: %s", exc)
            return None

    def _metadata_uri(self, user_card_id: int) -> str:
        base = self.settings.public_api_base_url.rstrip("/")
        return f"{base}/api/collectible/metadata/{user_card_id}.json"

    def _start_mint(self, user: User, row: UserCollectibleCard, card: CollectibleCard) -> bool:
        acct = self.ensure_user_chain_account(user)
        if not acct or not acct.native_address:
            row.chain_status = CHAIN_STATUS_FAILED
            row.chain_error = "chain_account_unavailable"
            return False

        class_id = self._ensure_class_id()
        if not class_id:
            row.chain_status = CHAIN_STATUS_FAILED
            row.chain_error = "nft_class_unavailable"
            return False

        op = self.client.new_operation_id(f"m{row.id}")
        row.chain_operation_id = op
        row.chain_class_id = class_id
        row.chain_status = CHAIN_STATUS_MINTING
        uri = self._metadata_uri(row.id)
        nft_name = f"{card.name} · ★{row.star}"
        try:
            self.client.mint_nft(
                class_id,
                name=nft_name,
                uri=uri,
                recipient=acct.native_address,
                operation_id=op,
                data=f"wc2026:{card.code}:u{user.id}",
            )
            self.db.flush()
            return self._poll_mint(row)
        except AvataError as exc:
            row.chain_status = CHAIN_STATUS_FAILED
            row.chain_error = str(exc)[:500]
            self._track_chain_event(row.user_id, "chain_mint_failed", row.id, row.chain_error)
            return False

    def _track_chain_event(
        self,
        user_id: int,
        event_name: str,
        user_card_id: int,
        error: str | None = None,
    ) -> None:
        try:
            from app.services.product_analytics_service import ProductAnalyticsService

            ProductAnalyticsService(self.db).track(
                event_name,
                user_id=user_id,
                payload={"user_card_id": user_card_id, "error": (error or "")[:120]},
                commit=False,
            )
        except Exception:
            logger.exception("chain analytics track failed card=%s", user_card_id)

    def _poll_mint(self, row: UserCollectibleCard) -> bool:
        if not row.chain_operation_id:
            return False
        try:
            resp = self.client.query_tx(row.chain_operation_id)
        except AvataError as exc:
            row.chain_error = str(exc)[:500]
            return False

        data = resp.get("data") or {}
        status = data.get("status")
        if status == 1:
            nft = (data.get("nft") or {}).get("mint") or {}
            row.chain_nft_id = nft.get("id") or row.chain_nft_id
            row.chain_class_id = nft.get("class_id") or row.chain_class_id
            row.chain_tx_hash = data.get("tx_hash")
            row.chain_status = CHAIN_STATUS_MINTED
            row.chain_minted_at = _utcnow()
            row.chain_error = None
            self._notify_minted(row)
            self._track_chain_event(row.user_id, "chain_mint_success", row.id)
            return True
        if status == 2:
            row.chain_status = CHAIN_STATUS_FAILED
            row.chain_error = (data.get("message") or "mint_failed")[:500]
            self._track_chain_event(row.user_id, "chain_mint_failed", row.id, row.chain_error)
            return False
        row.chain_status = CHAIN_STATUS_MINTING
        return False

    def retry_mint(self, user: User, user_card_id: int) -> dict[str, Any]:
        if not self.active:
            raise BadRequestError("链上功能未启用")
        row = (
            self.db.query(UserCollectibleCard)
            .filter(UserCollectibleCard.id == user_card_id, UserCollectibleCard.user_id == user.id)
            .with_for_update()
            .first()
        )
        if not row:
            raise NotFoundError("卡牌不存在")
        if row.chain_status not in (CHAIN_STATUS_FAILED, CHAIN_STATUS_NONE, CHAIN_STATUS_PENDING):
            if row.chain_status == CHAIN_STATUS_MINTING:
                raise BadRequestError("铸造进行中，请稍后在收藏册刷新状态")
            raise BadRequestError("当前状态不可重试")
        card = self.db.get(CollectibleCard, row.card_id)
        if not card:
            raise NotFoundError("卡牌不存在")
        row.chain_status = CHAIN_STATUS_PENDING
        row.chain_error = None
        row.chain_operation_id = None
        row.updated_at = _utcnow()
        self.db.flush()
        if self._start_mint(user, row, card):
            return self.chain_brief(row) or {}
        self.db.flush()
        brief = self.chain_brief(row)
        if brief and brief.get("status") == CHAIN_STATUS_FAILED:
            raise BadRequestError(brief.get("error") or "铸造失败")
        return brief or {"status": row.chain_status}

    def transfer_card_onchain(
        self,
        from_user: User,
        to_user: User,
        row: UserCollectibleCard,
    ) -> dict[str, Any]:
        """托管账户间转移已铸造 NFT。返回 {status, tx_hash, operation_id}。

        仅当链上功能开启且该卡已 minted 才真正调链；否则返回 skipped（DB 所有权迁移由上层处理）。
        """
        if not self.active:
            return {"status": "skipped", "reason": "chain_inactive"}
        if row.chain_status != CHAIN_STATUS_MINTED or not row.chain_nft_id or not row.chain_class_id:
            return {"status": "skipped", "reason": "not_minted"}

        from_acct = self.db.query(UserChainAccount).filter(UserChainAccount.user_id == from_user.id).first()
        to_acct = self.ensure_user_chain_account(to_user)
        if not from_acct or not from_acct.native_address or not to_acct or not to_acct.native_address:
            return {"status": "skipped", "reason": "chain_account_unavailable"}

        op = self.client.new_operation_id(f"xfer{row.id}")
        try:
            self.client.transfer_nft(
                row.chain_class_id,
                row.chain_nft_id,
                owner=from_acct.native_address,
                recipient=to_acct.native_address,
                operation_id=op,
            )
        except AvataError as exc:
            logger.warning("AVATA transfer failed row=%s: %s", row.id, exc)
            return {"status": "failed", "operation_id": op, "error": str(exc)[:200]}

        # 轮询结果
        tx_hash = None
        for _ in range(8):
            try:
                resp = self.client.query_tx(op)
            except AvataError:
                break
            data = resp.get("data") or {}
            status = data.get("status")
            if status == 1:
                tx_hash = data.get("tx_hash")
                break
            if status == 2:
                return {"status": "failed", "operation_id": op, "error": data.get("message")}
            time.sleep(1.0)
        return {"status": "minted", "operation_id": op, "tx_hash": tx_hash}

    def _notify_minted(self, row: UserCollectibleCard) -> None:
        try:
            from app.services.notification_service import NotificationService

            card = self.db.get(CollectibleCard, row.card_id)
            if not card:
                return
            NotificationService(self.db).notify_collectible_chain_minted(
                row.user_id,
                user_card_id=row.id,
                card_name=card.name,
                nft_id=row.chain_nft_id,
            )
        except Exception:
            logger.exception("Collectible chain mint notification failed row=%s", row.id)

    def build_metadata(self, row: UserCollectibleCard, card: CollectibleCard, user: User) -> dict[str, Any]:
        image = card.image_url or ""
        if image.startswith("/"):
            image = f"{self.settings.frontend_base_url.rstrip('/')}{image}"
        return {
            "name": card.name,
            "description": (
                f"最后一舞 · 世界杯2026 球星数字藏品。"
                f"玩法获得或合规流通，以可用积分计价，无金钱价值，不可提现。"
                f"发行链：{self.settings.avata_chain_name}（AVATA 托管）。"
            ),
            "image": image,
            "external_url": f"{self.settings.frontend_base_url.rstrip('/')}/collection",
            "attributes": [
                {"trait_type": "稀有度", "value": card.rarity},
                {"trait_type": "系列", "value": card.series},
                {"trait_type": "星级", "value": row.star},
                {"trait_type": "来源", "value": row.source},
                {"trait_type": "持有人", "value": user.nickname},
                {"trait_type": "序列号", "value": f"#{row.serial_no}" if row.serial_no else "—"},
                {"trait_type": "合规声明", "value": "虚拟收藏·积分计价流通"},
            ],
            "compliance_notice": (
                "数字藏品为平台内虚拟收藏，二级流通以可用积分计价，无金钱价值，不可提现。"
            ),
        }

    def chain_brief(self, row: UserCollectibleCard | None) -> dict[str, Any] | None:
        if not row or not self.active:
            return None
        return {
            "enabled": True,
            "chain_name": self.settings.avata_chain_name,
            "status": row.chain_status,
            "nft_id": row.chain_nft_id,
            "class_id": row.chain_class_id,
            "tx_hash": row.chain_tx_hash,
            "minted_at": row.chain_minted_at.isoformat() if row.chain_minted_at else None,
            "error": row.chain_error,
        }

    def mark_recalled(self, row: UserCollectibleCard) -> None:
        """回购后标记链上凭证已平台回收（不发链上 burn，仅 DB 标记）。"""
        row.chain_status = "recalled"
        row.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.flush()
