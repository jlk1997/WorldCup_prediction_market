import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError, NotFoundError
from app.db.models.commerce import Order, PaymentNotification, Product, User, UserBadge
from app.db.repositories.user_repository import UserRepository, WalletRepository

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

    def create_order(self, user_id: int, product_id: int) -> tuple[Order, str]:
        user = self.db.query(User).filter(User.id == user_id).with_for_update().first()
        if not user:
            raise NotFoundError("用户不存在")
        product = self.db.get(Product, product_id)
        if not product or not product.active:
            raise NotFoundError("商品不存在")
        if product.pay_currency == "redeem":
            raise BadRequestError("该商品请使用积分兑换")

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
            pay_url = self._build_pay_url(existing, product)
            return existing, pay_url

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

        pay_url = self._build_pay_url(order, product)
        return order, pay_url

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

    def _build_pay_url(self, order: Order, product: Product) -> str:
        if self.settings.alipay_mock or not self.settings.alipay_configured:
            return f"{self.settings.alipay_return_url}?mock=1&out_trade_no={order.out_trade_no}"

        try:
            alipay = self._build_alipay_client()
            order_string = alipay.api_alipay_trade_page_pay(
                out_trade_no=order.out_trade_no,
                total_amount=f"{order.amount_fen / 100:.2f}",
                subject=product.name,
                return_url=self.settings.alipay_return_url,
                notify_url=self.settings.alipay_notify_url,
            )
            gateway = (
                "https://openapi.alipaydev.com/gateway.do"
                if self.settings.alipay_sandbox
                else "https://openapi.alipay.com/gateway.do"
            )
            return f"{gateway}?{order_string}"
        except Exception as exc:
            logger.exception("Alipay build pay url failed")
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
            self.db.commit()
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

    def _fulfill_order(self, order: Order, alipay_trade_no: str) -> Order:
        if order.status == "paid":
            self.db.commit()
            return order

        product = self.db.get(Product, order.product_id)
        user = self.db.query(User).filter(User.id == order.user_id).with_for_update().first()
        if not product or not user:
            self.db.rollback()
            raise NotFoundError("订单数据异常")

        order.status = "paid"
        order.alipay_trade_no = alipay_trade_no
        order.paid_at = _utcnow()

        if product.coins_grant > 0:
            self.wallet.add_coins(user, product.coins_grant, "purchase", "order", order.id)

        if product.grant_season_pass_days > 0:
            user.has_season_pass = True
            base = user.season_pass_until or _utcnow()
            if base < _utcnow():
                base = _utcnow()
            user.season_pass_until = base + timedelta(days=product.grant_season_pass_days)
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
        if product.grant_season_pass_days > 0:
            pass_svc.grant_daily_if_eligible(user, commit=False)

        self.db.commit()
        self.db.refresh(order)
        return order

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
        return {
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
        }

    def list_user_orders(self, user_id: int, limit: int = 20) -> list[Order]:
        return (
            self.db.query(Order)
            .filter(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .limit(min(limit, 50))
            .all()
        )
