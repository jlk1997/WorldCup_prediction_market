import hashlib
import logging
import secrets
import smtplib
import string
from datetime import datetime, timedelta, timezone
from email.header import Header
from email.mime.text import MIMEText
from email.utils import formataddr, parseaddr

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.exceptions import BadRequestError, UnauthorizedError
from app.db.models.commerce import AuthCode, User, UserSession
from app.db.repositories.user_repository import UserRepository, WalletRepository

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _hash_code(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def verify_token_hash(token: str, token_hash: str) -> bool:
    return secrets.compare_digest(_hash_token(token), token_hash)


class AuthService:
    def __init__(self, db: Session, settings: Settings | None = None):
        self.db = db
        self.settings = settings or get_settings()
        self.users = UserRepository(db)
        self.wallet = WalletRepository(db)

    def send_code(self, email: str, client_ip: str | None = None, age_confirmed: bool = False) -> None:
        email = email.strip().lower()
        if "@" not in email or len(email) > 255:
            raise BadRequestError("邮箱格式不正确")
        if not age_confirmed:
            raise BadRequestError("请先确认已满 18 周岁并同意用户协议")

        from app.core.rate_limit import rate_limit_send_code

        rate_limit_send_code(email, client_ip)

        code = "".join(secrets.choice(string.digits) for _ in range(6))
        expires = _utcnow() + timedelta(minutes=self.settings.auth_code_expire_minutes)

        self.db.add(
            AuthCode(
                email=email,
                code_hash=_hash_code(code),
                expires_at=expires,
            )
        )
        self.db.commit()

        if self.settings.smtp_configured:
            self._send_email(email, code)
        elif self.settings.auth_dev_mode:
            logger.warning("[DEV AUTH] %s code=%s (expires %s)", email, code, expires)
        else:
            raise BadRequestError("邮件服务未配置，请联系管理员")

    def _resolve_from(self) -> tuple[str, str]:
        """Build RFC5322/2047 compliant From header; envelope must match SMTP login (QQ rule)."""
        envelope = self.settings.smtp_user.strip()
        name, addr = parseaddr(self.settings.smtp_from or envelope)
        if not addr:
            addr = envelope
        if not name and addr == envelope and "@" in (self.settings.smtp_from or ""):
            name = "最后一舞"
        # QQ 邮箱要求发信地址与登录账号一致
        addr = envelope
        if name:
            header_from = formataddr((str(Header(name, "utf-8")), addr))
        else:
            header_from = addr
        return header_from, envelope

    def _send_email(self, email: str, code: str) -> None:
        header_from, envelope_from = self._resolve_from()
        msg = MIMEText(
            f"您的「最后一舞：世界杯2026」登录验证码是：{code}\n"
            f"有效期 {self.settings.auth_code_expire_minutes} 分钟，请勿泄露。",
            "plain",
            "utf-8",
        )
        msg["Subject"] = str(Header("最后一舞 · 登录验证码", "utf-8"))
        msg["From"] = header_from
        msg["To"] = email

        try:
            if self.settings.smtp_use_tls:
                with smtplib.SMTP_SSL(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as server:
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                    server.send_message(msg, from_addr=envelope_from, to_addrs=[email])
            else:
                with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=30) as server:
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
                    server.login(self.settings.smtp_user, self.settings.smtp_password)
                    server.send_message(msg, from_addr=envelope_from, to_addrs=[email])
        except smtplib.SMTPException as exc:
            logger.exception("SMTP send failed to %s", email)
            raise BadRequestError(f"验证码邮件发送失败：{exc}") from exc

    def _issue_tokens(self, user: User, is_new: bool) -> tuple[User, str, str, bool]:
        access = self._create_access_token(user.id)
        refresh = secrets.token_urlsafe(32)
        self.db.add(
            UserSession(
                user_id=user.id,
                refresh_token_hash=_hash_token(refresh),
                expires_at=_utcnow() + timedelta(days=self.settings.jwt_refresh_expire_days),
            )
        )
        self.db.commit()
        self.db.refresh(user)
        return user, access, refresh, is_new

    def _try_replay_used_code(self, email: str, code_hash: str) -> tuple[User, str, str, bool] | None:
        """5 分钟内已用过的正确验证码仍允许登录（防双点/重复请求）。"""
        used_row = (
            self.db.query(AuthCode)
            .filter(
                AuthCode.email == email,
                AuthCode.code_hash == code_hash,
                AuthCode.used_at.isnot(None),
            )
            .order_by(AuthCode.id.desc())
            .first()
        )
        if not used_row or not used_row.used_at:
            return None
        if (_utcnow() - used_row.used_at).total_seconds() > 300:
            return None
        user = self.users.get_by_email(email)
        if not user:
            return None
        return self._issue_tokens(user, is_new=False)

    def verify_and_login(
        self,
        email: str,
        code: str,
        age_confirmed: bool = False,
        client_ip: str | None = None,
        invite_code: str | None = None,
    ) -> tuple[User, str, str, bool]:
        email = email.strip().lower()
        if not age_confirmed:
            raise BadRequestError("请先确认已满 18 周岁并同意用户协议")

        from app.core.rate_limit import rate_limit_verify_code

        rate_limit_verify_code(email, client_ip)

        code_hash = _hash_code(code.strip())

        row = (
            self.db.query(AuthCode)
            .filter(AuthCode.email == email, AuthCode.used_at.is_(None))
            .order_by(AuthCode.id.desc())
            .with_for_update()
            .first()
        )

        if not row or row.code_hash != code_hash:
            replay = self._try_replay_used_code(email, code_hash)
            if replay:
                return replay
            if row and row.code_hash != code_hash:
                raise BadRequestError("验证码错误，请使用最新一封邮件中的验证码")
            raise BadRequestError("验证码错误或已失效，请重新获取")

        if row.expires_at < _utcnow():
            raise BadRequestError("验证码已过期，请重新获取")

        row.used_at = _utcnow()
        is_new = False
        user = self.users.get_by_email(email)
        if not user:
            is_new = True
            nickname = email.split("@")[0][:20] or "球迷"
            user = self.users.create(email=email, nickname=nickname, fan_coins=0)
            self._grant_coins(user, self.settings.new_user_coins, "register_bonus")
            self.db.flush()
            try:
                from app.services.referral_service import ReferralService

                ReferralService(self.db, self.settings).bind_on_register(
                    user, invite_code, client_ip, is_new=True
                )
            except Exception:
                logger.exception("Referral bind failed for new user %s", email)

        return self._issue_tokens(user, is_new)

    def refresh_tokens(self, refresh_token: str) -> tuple[str, str, int]:
        token_hash = _hash_token(refresh_token)
        session = (
            self.db.query(UserSession)
            .filter(UserSession.refresh_token_hash == token_hash, UserSession.expires_at > _utcnow())
            .with_for_update()
            .first()
        )
        if not session:
            raise UnauthorizedError("refresh token 无效")
        user_id = session.user_id

        self.db.query(UserSession).filter(UserSession.id == session.id).delete()
        user = self.users.get_by_id(user_id)
        if not user:
            raise UnauthorizedError("用户不存在")

        access = self._create_access_token(user.id)
        new_refresh = secrets.token_urlsafe(32)
        self.db.add(
            UserSession(
                user_id=user.id,
                refresh_token_hash=_hash_token(new_refresh),
                expires_at=_utcnow() + timedelta(days=self.settings.jwt_refresh_expire_days),
            )
        )
        self.db.commit()
        return access, new_refresh, user.id

    def _create_access_token(self, user_id: int) -> str:
        expire = _utcnow() + timedelta(minutes=self.settings.jwt_access_expire_minutes)
        return jwt.encode(
            {"sub": str(user_id), "exp": expire, "type": "access"},
            self.settings.jwt_secret,
            algorithm=ALGORITHM,
        )

    def decode_user_id(self, token: str) -> int:
        try:
            payload = jwt.decode(token, self.settings.jwt_secret, algorithms=[ALGORITHM])
            if payload.get("type") != "access":
                raise UnauthorizedError()
            return int(payload["sub"])
        except (JWTError, ValueError, KeyError) as exc:
            raise UnauthorizedError("登录已过期，请重新登录") from exc

    def _grant_coins(self, user: User, amount: int, reason: str) -> None:
        self.wallet.add_coins(user, amount, reason, "user", user.id)

    @staticmethod
    def purge_expired_sessions(db) -> int:
        """Remove expired refresh token rows."""
        deleted = (
            db.query(UserSession)
            .filter(UserSession.expires_at <= _utcnow())
            .delete(synchronize_session=False)
        )
        if deleted:
            db.commit()
        return int(deleted or 0)
