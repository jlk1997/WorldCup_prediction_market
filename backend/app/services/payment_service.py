import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import Order, PaymentNotification, Product, User, UserBadge
from app.db.repositories.user_repository import UserRepository, WalletRepository
from app.utils.pay_channel import PayChannel, PayChannelRequest, resolve_pay_channel

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class PaymentService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.wallet = WalletRepository(db)

    def list_products(self) -> list[Product]:
        return (
            self.db.query(Product)
            .filter(Product.active.is_(True), Product.pay_currency == "cash")
            .order_by(Product.sort_order)
            .all()
        )

    def create_order(
        self,
        user_id: int,
        product_id: int,
        *,
        pay_channel: PayChannelRequest = "auto",
        user_agent: str | None = None,
    ) -> tuple[Order, str, PayChannel]:
        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user:
            raise NotFoundError("用户不存在")
        product = self.db.get(Product, product_id)
        if not product or not product.active:
            raise NotFoundError("商品不存在")
        if product.pay_currency == "redeem":
            raise BadRequestError("该商品请使用积分兑换")

        self._assert_cash_product_eligible(user_id, product)

        channel = resolve_pay_channel(pay_channel, user_agent)

        reuse_cutoff = _utcnow() - timedelta(minutes=self.settings.order_pending_reuse_minutes)
        existing = (
            self.db.query(Order)
            .filter(
                Order.user_id == user_id,
                Order.product_id == product_id,
                Order.status == "pending",
                Order.created_at >= reuse_cutoff,
            )
            .order_by(Order.id.desc())
            .first()
        )
        if existing:
            if existing.amount_fen != product.price_fen:
                existing.amount_fen = product.price_fen
                self.db.commit()
                self.db.refresh(existing)
            pay_url = self._build_pay_url(existing, product, channel)
            return existing, pay_url, channel

        out_trade_no = f"WC{datetime.now().strftime('%Y%m%d%H%M%S')}{uuid.uuid4().hex[:8].upper()}"
        order = Order(
            out_trade_no=out_trade_no,
            user_id=user_id,
            product_id=product.id,
            amount_fen=product.price_fen,
            status="pending",
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)

        pay_url = self._build_pay_url(order, product, channel)
        return order, pay_url, channel

    def _assert_cash_product_eligible(self, user_id: int, product: Product) -> None:
        limit = product.per_user_limit or 0
        if limit > 0:
            paid_count = (
                self.db.query(Order)
                .filter(
                    Order.user_id == user_id,
                    Order.product_id == product.id,
                    Order.status == "paid",
                )
                .count()
            )
            if paid_count >= limit:
                raise BadRequestError("已达该商品购买上限")

        payload = product.grant_payload or {}
        if payload.get("collection_pass_premium") or product.product_type in (
            "collection_pass",
            "season_ultimate",
        ):
            from app.services.collection_pass_service import CollectionPassService

            user = self.db.get(User, user_id)
            if user:
                progress = CollectionPassService(self.db)._get_or_create_progress(
                    user, CollectionPassService(self.db)._get_active_season()
                )
                if progress.premium_unlocked:
                    raise BadRequestError("已解锁藏品赛季手册尊享版，无需重复购买")

    def _build_alipay_client(self):
        from alipay import DCAliPay

        private_key = self.settings.alipay_private_key_file.read_text(encoding="utf-8")
        app_cert = self.settings.alipay_app_cert_file.read_text(encoding="utf-8")
        alipay_cert = self.settings.alipay_alipay_cert_file.read_text(encoding="utf-8")
        root_cert = self.settings.alipay_root_cert_file.read_text(encoding="utf-8")
        return DCAliPay(
            appid=self.settings.alipay_app_id,
            app_notify_url=self.settings.alipay_notify_url,
            app_private_key_string=private_key,
            app_public_key_cert_string=app_cert,
            alipay_public_key_cert_string=alipay_cert,
            alipay_root_cert_string=root_cert,
        )

    def _build_pay_url(self, order: Order, product: Product, channel: PayChannel = "page") -> str:
        if self.settings.alipay_mock or not self.settings.alipay_configured:
            return f"{self.settings.alipay_return_url}?mock=1&out_trade_no={order.out_trade_no}"

        try:
            alipay = self._build_alipay_client()
            pay_kwargs = {
                "out_trade_no": order.out_trade_no,
                "total_amount": f"{order.amount_fen / 100:.2f}",
                "subject": product.name,
                "return_url": self.settings.alipay_return_url,
                "notify_url": self.settings.alipay_notify_url,
            }
            if channel == "wap":
                order_string = alipay.api_alipay_trade_wap_pay(**pay_kwargs)
            else:
                order_string = alipay.api_alipay_trade_page_pay(**pay_kwargs)
            gateway = (
                "https://openapi.alipaydev.com/gateway.do"
                if self.settings.alipay_sandbox
                else "https://openapi.alipay.com/gateway.do"
            )
            return f"{gateway}?{order_string}"
        except Exception as exc:
            logger.exception("Alipay build pay url failed channel=%s", channel)
            raise BadRequestError(f"支付初始化失败: {exc}") from exc

    def _verify_notify_signature(self, data: dict) -> bool:
        if not self.settings.alipay_configured:
            logger.warning("Alipay notify received but keys not configured")
            return False
        try:
            alipay = self._build_alipay_client()
            sign = data.get("sign")
            if not sign:
                return False
            payload = {
                k: v for k, v in data.items() if k not in ("sign", "sign_type") and v is not None and v != ""
            }
            return bool(alipay.verify(payload, sign))
        except Exception:
            logger.exception("Alipay notify signature verification failed")
            return False

    def _amount_matches_order(self, order: Order, notify_data: dict) -> bool:
        raw = notify_data.get("total_amount") or notify_data.get("buyer_pay_amount")
        if raw is None:
            return False
        try:
            paid_fen = int((Decimal(str(raw)) * 100).quantize(Decimal("1")))
        except (InvalidOperation, ValueError):
            return False
        return paid_fen == order.amount_fen

    def mock_pay_success(self, out_trade_no: str, user_id: int) -> Order:
        if not self.settings.alipay_mock:
            raise BadRequestError("mock 支付未开启")
        if self.settings.production_mode:
            raise BadRequestError("生产环境禁止使用 mock 支付")
        order = (
            self.db.query(Order)
            .filter(Order.out_trade_no == out_trade_no)
            .with_for_update()
            .first()
        )
        if not order:
            raise NotFoundError("订单不存在")
        if order.user_id != user_id:
            raise BadRequestError("无权操作该订单")
        return self._fulfill_order(order, alipay_trade_no=f"MOCK{uuid.uuid4().hex[:12]}")

    def handle_notify(self, data: dict) -> str:
        """Return 'success' or 'failure' for Alipay async notify."""
        out_trade_no = data.get("out_trade_no", "")
        verified = self._verify_notify_signature(data)

        self.db.add(
            PaymentNotification(
                out_trade_no=out_trade_no,
                payload=data,
                verified=verified,
            )
        )

        if not verified:
            self.db.commit()
            logger.warning("Rejected Alipay notify: bad signature out_trade_no=%s", out_trade_no)
            return "failure"

        trade_status = data.get("trade_status")
        if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            self.db.commit()
            return "success"

        order = (
            self.db.query(Order)
            .filter(Order.out_trade_no == out_trade_no)
            .with_for_update()
            .first()
        )
        if not order:
            self.db.commit()
            logger.error("Alipay notify for unknown order: %s", out_trade_no)
            return "failure"

        if order.status == "paid":
            if not order.grant_result_json:
                self._fulfill_order(
                    order,
                    alipay_trade_no=trade_no or order.alipay_trade_no or "",
                )
            else:
                self.db.commit()
            return "success"

        if order.status == "cancelled":
            self.db.commit()
            logger.warning("Alipay notify for cancelled order: %s", order.out_trade_no)
            return "success"

        if not self._amount_matches_order(order, data):
            self.db.commit()
            logger.error(
                "Alipay amount mismatch order=%s expected_fen=%s got=%s",
                out_trade_no,
                order.amount_fen,
                data.get("total_amount"),
            )
            return "failure"

        trade_no = data.get("trade_no", "")
        if order.alipay_trade_no and order.alipay_trade_no != trade_no:
            self.db.commit()
            logger.error("Alipay trade_no conflict order=%s", out_trade_no)
            return "failure"

        self._fulfill_order(order, alipay_trade_no=trade_no)
        return "success"

    def sync_order_from_alipay(self, out_trade_no: str, user_id: int) -> Order:
        """Query Alipay for payment status and fulfill pending orders (notify fallback)."""
        if self.settings.alipay_mock or not self.settings.alipay_configured:
            raise BadRequestError("支付宝未配置，无法同步订单")
        order = (
            self.db.query(Order)
            .filter(Order.out_trade_no == out_trade_no)
            .with_for_update()
            .first()
        )
        if not order:
            raise NotFoundError("订单不存在")
        if order.user_id != user_id:
            raise BadRequestError("无权操作该订单")
        if order.status == "cancelled":
            self.db.commit()
            raise BadRequestError("订单已取消，请重新下单")
        if order.status == "paid":
            if not order.grant_result_json:
                self._fulfill_order(
                    order,
                    alipay_trade_no=order.alipay_trade_no or "",
                )
            else:
                self.db.commit()
            return order

        try:
            alipay = self._build_alipay_client()
            result = alipay.api_alipay_trade_query(out_trade_no=out_trade_no)
        except Exception as exc:
            logger.exception("Alipay trade query failed out_trade_no=%s", out_trade_no)
            raise BadRequestError(f"查询支付宝订单失败: {exc}") from exc

        if result.get("code") != "10000":
            self.db.commit()
            logger.warning(
                "Alipay query not ready out_trade_no=%s code=%s sub=%s",
                out_trade_no,
                result.get("code"),
                result.get("sub_code") or result.get("sub_msg"),
            )
            return order

        trade_status = result.get("trade_status")
        if trade_status not in ("TRADE_SUCCESS", "TRADE_FINISHED"):
            self.db.commit()
            return order

        if not self._amount_matches_order(
            order,
            {"total_amount": result.get("total_amount"), "buyer_pay_amount": result.get("buyer_pay_amount")},
        ):
            self.db.commit()
            logger.error(
                "Alipay sync amount mismatch order=%s expected_fen=%s got=%s",
                out_trade_no,
                order.amount_fen,
                result.get("total_amount"),
            )
            raise BadRequestError("支付金额与订单不一致，请联系客服")

        trade_no = result.get("trade_no") or ""
        if order.alipay_trade_no and order.alipay_trade_no != trade_no:
            self.db.commit()
            raise BadRequestError("支付宝交易号冲突，请联系客服")

        return self._fulfill_order(order, alipay_trade_no=trade_no)

    def _fulfill_order(self, order: Order, alipay_trade_no: str | None = None) -> Order:
        product = self.db.get(Product, order.product_id)
        user = self.db.query(User).filter(User.id == order.user_id).with_for_update().first()
        if not product or not user:
            self.db.rollback()
            raise NotFoundError("订单数据异常")

        if order.grant_result_json:
            if order.status != "paid":
                order.status = "paid"
                if alipay_trade_no:
                    order.alipay_trade_no = alipay_trade_no
                if not order.paid_at:
                    order.paid_at = _utcnow()
            self.db.commit()
            self.db.refresh(order)
            return order

        if order.status != "paid":
            order.status = "paid"
            order.alipay_trade_no = alipay_trade_no or order.alipay_trade_no or ""
            order.paid_at = _utcnow()
        elif alipay_trade_no and not order.alipay_trade_no:
            order.alipay_trade_no = alipay_trade_no

        self._apply_product_grants(order, product, user)

        from app.core.user_surface_cache import invalidate_user_surface

        invalidate_user_surface(user.id)
        self.db.commit()
        self.db.refresh(order)
        return order

    def _apply_product_grants(self, order: Order, product: Product, user: User) -> None:
        payload = product.grant_payload or {}
        is_mint = product.product_type == "mint_event" or (
            product.product_type != "mint_bundle"
            and (order.mint_event_id or payload.get("mint_event_id"))
        )

        if is_mint:
            from app.services.primary_mint_service import PrimaryMintService

            PrimaryMintService(self.db).fulfill_paid_order(order)
            return

        if product.product_type == "mint_bundle":
            from app.services.mint_bundle_service import MintBundleService
            from app.services.season_pass_service import SeasonPassService

            MintBundleService(self.db).grant(user, product, order)
            SeasonPassService(self.db).apply_cosmetic_purchase(user, product)
            return

        grant_result: dict = {
            "product_type": product.product_type,
            "sku": product.sku,
            "order_id": order.id,
        }

        if product.product_type == "ai_pack":
            from app.services.ai_billing_service import AiBillingService

            AiBillingService(self.db).grant_ai_pack(user, payload)
            grant_result["ai_pack"] = True

        if product.coins_grant > 0:
            self.wallet.add_coins(user, product.coins_grant, "purchase", "order", order.id)
            grant_result["coins_grant"] = product.coins_grant

        if product.grant_season_pass_days > 0:
            user.has_season_pass = True
            base = user.season_pass_until or _utcnow()
            if base < _utcnow():
                base = _utcnow()
            user.season_pass_until = base + timedelta(days=product.grant_season_pass_days)
            grant_result["season_pass_days"] = product.grant_season_pass_days
            if not self.db.query(UserBadge).filter(
                UserBadge.user_id == user.id, UserBadge.badge_code == "season_pass_2026"
            ).first():
                self.db.add(
                    UserBadge(
                        user_id=user.id,
                        badge_code="season_pass_2026",
                        title="2026 赛季通行证",
                    )
                )

        from app.services.season_pass_service import SeasonPassService

        pass_svc = SeasonPassService(self.db)
        pass_svc.apply_cosmetic_purchase(user, product)
        payload = product.grant_payload or {}
        if payload.get("collection_pass_premium") or product.product_type in (
            "collection_pass",
            "season_ultimate",
        ):
            from app.services.collection_pass_service import CollectionPassService

            pass_collection = CollectionPassService(self.db)
            if skip := payload.get("collection_pass_level_skip"):
                pass_collection.grant_level_skip(user, int(skip))
                grant_result["collection_pass_level_skip"] = int(skip)
            pass_collection.unlock_premium(user)
            grant_result["collection_pass_premium"] = True
        if product.grant_season_pass_days > 0:
            pass_svc.grant_daily_if_eligible(user, commit=False)

        order.grant_result_json = grant_result

    def get_order(self, order_id: int, user_id: int) -> Order:
        order = self.db.get(Order, order_id)
        if not order or order.user_id != user_id:
            raise NotFoundError("订单不存在")
        return order

    def get_order_by_trade_no(self, out_trade_no: str, user_id: int) -> Order:
        order = self.db.query(Order).filter(Order.out_trade_no == out_trade_no).first()
        if not order or order.user_id != user_id:
            raise NotFoundError("订单不存在")
        return order

    def order_detail(self, order: Order) -> dict:
        from app.services.entitlements import build_product_grant_summary

        product = self.db.get(Product, order.product_id)
        if not product:
            raise NotFoundError("订单商品不存在")
        grant = order.grant_result_json or {}
        detail = {
            "id": order.id,
            "out_trade_no": order.out_trade_no,
            "amount_fen": order.amount_fen,
            "status": order.status,
            "paid_at": order.paid_at,
            "product_name": product.name,
            "product_type": product.product_type,
            "coins_grant": product.coins_grant,
            "grant_season_pass_days": product.grant_season_pass_days,
            "alipay_trade_no": order.alipay_trade_no,
            "grant_summary": build_product_grant_summary(product, self.settings),
            "mint_event_id": order.mint_event_id,
            "mint_serial_no": grant.get("serial_no"),
            "mint_card_name": grant.get("card_name"),
            "mint_user_card_id": grant.get("user_card_id"),
            "mint_notice": grant.get("notice"),
            "created_at": order.created_at,
        }
        if grant and product.product_type == "mint_event":
            serial = grant.get("serial_no")
            name = grant.get("card_name") or product.name
            detail["grant_summary"] = [
                f"限量球星卡「{name}」",
                f"序列号 #{serial}" if serial else "序列号分配中",
                "链上铸造将在数分钟内完成",
            ]
        return detail

    def cancel_pending_order(self, user_id: int, order: Order) -> Order:
        if order.user_id != user_id:
            raise BadRequestError("无权操作该订单")
        if order.status != "pending":
            raise BadRequestError("仅待支付订单可取消")
        order.status = "cancelled"
        if order.mint_event_id:
            from app.services.primary_mint_service import PrimaryMintService

            PrimaryMintService(self.db).release_mint_lock_for_order(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def expire_abandoned_pending_orders(self, limit: int = 200) -> dict[str, int]:
        from app.services.primary_mint_service import PrimaryMintService

        mint_result = PrimaryMintService(self.db).expire_pending_mint_orders(limit=limit)
        reuse_cutoff = _utcnow() - timedelta(minutes=self.settings.order_pending_reuse_minutes * 2)
        stale = (
            self.db.query(Order)
            .filter(
                Order.status == "pending",
                Order.mint_event_id.is_(None),
                Order.created_at < reuse_cutoff,
            )
            .limit(limit)
            .all()
        )
        generic_expired = 0
        for order in stale:
            order.status = "cancelled"
            generic_expired += 1
        if generic_expired:
            self.db.commit()
        return {"mint_expired": mint_result.get("expired", 0), "generic_expired": generic_expired}

    def admin_refund_order(self, order_id: int) -> dict:
        """Admin 退款：支付宝原路退款（生产）+ 标记 refunded + 回收 mint 发卡。"""
        order = self.db.query(Order).filter(Order.id == order_id).with_for_update().first()
        if not order:
            raise NotFoundError("订单不存在")
        if order.status not in ("paid",):
            raise BadRequestError("仅已支付订单可退款")
        alipay_refund_id = None
        if (
            not self.settings.alipay_mock
            and self.settings.alipay_configured
            and order.alipay_trade_no
            and order.amount_fen > 0
        ):
            try:
                alipay = self._build_alipay_client()
                refund_no = f"RF{order.out_trade_no}"[:64]
                result = alipay.api_alipay_trade_refund(
                    out_trade_no=order.out_trade_no,
                    refund_amount=f"{order.amount_fen / 100:.2f}",
                    out_request_no=refund_no,
                )
                alipay_refund_id = result.get("trade_no") or refund_no
            except Exception as exc:
                logger.exception("Alipay refund failed order=%s", order.id)
                raise BadRequestError(f"支付宝退款失败: {exc}") from exc
        order.status = "refunded"
        note = "admin_refund"
        if alipay_refund_id:
            note = f"alipay_refund:{alipay_refund_id}"
        grant = order.grant_result_json or {}
        user_card_id = grant.get("user_card_id")
        if user_card_id:
            from app.db.models.commerce import UserCollectibleCard

            row = self.db.get(UserCollectibleCard, user_card_id)
            if row and row.user_id == order.user_id:
                row.tradable = False
                note = "card_recalled"
        self.db.commit()
        return {"ok": True, "order_id": order.id, "status": order.status, "note": note}

    def list_user_orders(self, user_id: int, limit: int = 20) -> list[Order]:
        return (
            self.db.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .limit(min(limit, 50))
            .all()
        )
