import secrets
from collections.abc import Generator

from fastapi import Header
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import ForbiddenError, UnauthorizedError
from app.db.session import SessionLocal


def require_manual_sync(x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret")) -> None:
    settings = get_settings()
    if not settings.allow_manual_sync:
        raise ForbiddenError("手动同步已关闭，数据由后台自动更新")
    secret = (settings.admin_sync_secret or "").strip()
    if not secret:
        raise ForbiddenError("必须设置 ADMIN_SYNC_SECRET 才能使用管理接口")
    if not x_admin_secret or not secrets.compare_digest(x_admin_secret, secret):
        raise UnauthorizedError("缺少有效的管理员同步密钥")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def require_admin_secret_in_production(
    x_admin_secret: str | None = Header(default=None, alias="X-Admin-Secret"),
) -> None:
    """In production, sensitive ops require ADMIN_SYNC_SECRET even if manual sync is disabled."""
    settings = get_settings()
    if not settings.production_mode:
        return
    secret = (settings.admin_sync_secret or "").strip()
    if not secret:
        raise ForbiddenError("生产环境必须设置 ADMIN_SYNC_SECRET")
    if not x_admin_secret or not secrets.compare_digest(x_admin_secret, secret):
        raise UnauthorizedError("缺少有效的管理员同步密钥")
