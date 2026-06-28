"""反作弊：打新/竞猜/AI 限频与设备指纹 v2。"""

from __future__ import annotations

import logging

from fastapi import Request

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class AntiCheatService:
    def __init__(self):
        self.settings = get_settings()

    def _key(self, scope: str, ident: str) -> str:
        return f"anticheat:{scope}:{ident}"

    @staticmethod
    def device_id(request: Request) -> str | None:
        raw = request.headers.get("X-Device-Id") or request.headers.get("X-Device-ID")
        if not raw:
            return None
        cleaned = raw.strip()[:64]
        if len(cleaned) < 8:
            return None
        return cleaned

    def check_rate(self, scope: str, ident: str, *, limit: int, window_sec: int) -> None:
        r = get_redis_client()
        if r is None:
            return
        key = self._key(scope, ident)
        try:
            count = r.incr(key)
            if count == 1:
                r.expire(key, window_sec)
            if count > limit:
                r.decr(key)
                raise BadRequestError("操作过于频繁，请稍后再试")
        except BadRequestError:
            raise
        except Exception:
            logger.debug("anticheat redis skip scope=%s", scope)

    def _check_device(self, request: Request, scope: str, *, limit: int, window_sec: int) -> None:
        did = self.device_id(request)
        if did:
            self.check_rate(f"{scope}_device", did, limit=limit, window_sec=window_sec)

    def check_mint_order(self, request: Request, user_id: int) -> None:
        ip = request.client.host if request.client else "unknown"
        self.check_rate("mint_user", str(user_id), limit=5, window_sec=60)
        self.check_rate("mint_ip", ip, limit=20, window_sec=60)
        self._check_device(request, "mint", limit=8, window_sec=3600)

    def check_predict_submit(self, request: Request, user_id: int) -> None:
        ip = request.client.host if request.client else "unknown"
        self.check_rate("predict_user", str(user_id), limit=30, window_sec=60)
        self.check_rate("predict_ip", ip, limit=60, window_sec=60)
        self._check_device(request, "predict", limit=45, window_sec=3600)
