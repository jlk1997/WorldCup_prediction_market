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
            return {"processed": 0, "minted": 0, "failed": 0}

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
        if processed:
            self.db.commit()
        return {"processed": processed, "minted": minted, "failed": failed}

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
                acct.status = "minting"
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
            if data.get("status") == 1:
                # Account creation may not return address in tx query; re-create if missing
                pass
        except AvataError:
            return

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
            return False

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
            return True
        if status == 2:
            row.chain_status = CHAIN_STATUS_FAILED
            row.chain_error = (data.get("message") or "mint_failed")[:500]
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
        if row.chain_status not in (CHAIN_STATUS_FAILED, CHAIN_STATUS_NONE):
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
                f"玩法获得，无金钱价值，不可交易/转赠/提现。"
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
                {"trait_type": "合规声明", "value": "虚拟收藏·不可交易"},
            ],
            "compliance_notice": "数字藏品为平台内虚拟收藏，无金钱价值，不可交易、不可转赠、不可提现。",
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
