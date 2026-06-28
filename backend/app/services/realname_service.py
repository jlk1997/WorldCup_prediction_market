"""实名认证服务（合规前置）。

开发期 mock 直接通过；生产对接三要素/人脸核验。仅存储姓名+证件号的哈希，绝不存明文。
"""

from __future__ import annotations

import hashlib
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.db.models.commerce import User

_ID_RE = re.compile(r"^\d{17}[\dXx]$")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RealNameService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    @staticmethod
    def _hash(real_name: str, id_no: str) -> str:
        raw = f"{real_name.strip()}|{id_no.strip().upper()}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def status(self, user: User) -> dict:
        return {
            "verified": bool(user.real_name_verified),
            "verified_at": user.real_name_verified_at.isoformat() if user.real_name_verified_at else None,
        }

    def verify(self, user: User, real_name: str, id_no: str) -> dict:
        if user.real_name_verified:
            return self.status(user)
        real_name = (real_name or "").strip()
        id_no = (id_no or "").strip().upper()
        if len(real_name) < 2:
            raise BadRequestError("请输入真实姓名")
        if not _ID_RE.match(id_no):
            raise BadRequestError("身份证号格式不正确")

        # 生产环境应调用三要素/人脸核验；local 模式仅格式校验（staging）
        if not self.settings.realname_mock:
            provider = getattr(self.settings, "realname_provider", "api")
            allow_local = getattr(self.settings, "realname_allow_local", False)
            if provider == "local" and allow_local:
                pass
            elif provider == "mock":
                pass
            else:
                raise BadRequestError("实名认证渠道未配置")

        h = self._hash(real_name, id_no)
        # 防止同一证件绑定多账号（简单去重）
        dup = (
            self.db.query(User.id)
            .filter(User.real_name_hash == h, User.id != user.id)
            .first()
        )
        if dup:
            raise BadRequestError("该证件已被其他账号实名绑定")

        user.real_name_verified = True
        user.real_name_hash = h
        user.real_name_verified_at = _utcnow()
        self.db.flush()
        return self.status(user)
