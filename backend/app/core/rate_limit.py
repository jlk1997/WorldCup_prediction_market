"""Simple rate limiting (Redis or in-memory)."""

import hashlib
import logging
import time
from collections import defaultdict

from fastapi import Request

from app.core.exceptions import RateLimitError
from app.core.redis_client import get_redis_client

logger = logging.getLogger(__name__)

_memory: dict[str, list[float]] = defaultdict(list)

_MSG_DEFAULT = "请求过于频繁，请稍后再试"
_MSG_GLOBAL = "访问有点快了，请稍等片刻再试"
_MSG_SEND_CODE = "验证码发送太频繁，请稍后再试"
_MSG_SEND_CODE_COOLDOWN = "验证码发送太频繁，请 1 分钟后再试"
_MSG_SEND_CODE_EMAIL = "验证码 1 小时内最多发送 3 次，请稍后再试"
_MSG_VERIFY = "验证码校验过于频繁，请稍后再试"
_MSG_PAY = "支付操作太频繁，请 1 分钟后再试"
_MSG_REDEEM = "兑换操作太频繁，请稍后再试"
_MSG_AGENT = "AI 分析请求过于频繁，请稍后再试"
_MSG_INSIGHT = "数据加载过于频繁，请稍后再试"


def _redis_incr(key: str, window_sec: int) -> int | None:
    r = get_redis_client()
    if not r:
        return None
    try:
        pipe = r.pipeline()
        pipe.incr(key)
        pipe.expire(key, window_sec)
        count, _ = pipe.execute()
        return int(count)
    except Exception as exc:
        logger.debug("Redis rate limit fallback: %s", exc)
        return None


def _memory_incr(key: str, window_sec: int) -> int:
    now = time.time()
    cutoff = now - window_sec
    bucket = _memory[key]
    _memory[key] = [t for t in bucket if t > cutoff]
    _memory[key].append(now)
    return len(_memory[key])


def check_rate_limit(
    key: str,
    limit: int,
    window_sec: int,
    *,
    message: str | None = None,
) -> None:
    count = _redis_incr(key, window_sec)
    if count is None:
        count = _memory_incr(key, window_sec)
    if count > limit:
        raise RateLimitError(message or _MSG_DEFAULT, retry_after_sec=window_sec)


def _ip_from_forwarded_headers(
    forwarded: str | None,
    real_ip: str | None,
    trusted: int,
    fallback: str,
) -> str:
    if trusted > 0:
        if real_ip:
            return real_ip.strip()
        if forwarded:
            parts = [p.strip() for p in forwarded.split(",") if p.strip()]
            if parts:
                return parts[0]
    return fallback


def client_ip(request: Request) -> str:
    from app.core.config import get_settings

    settings = get_settings()
    return _ip_from_forwarded_headers(
        request.headers.get("x-forwarded-for"),
        request.headers.get("x-real-ip"),
        max(0, settings.trusted_proxy_count),
        request.client.host if request.client else "unknown",
    )


def client_ip_websocket(websocket) -> str:
    """Real client IP for WebSocket (must read X-Forwarded-For from nginx)."""
    from app.core.config import get_settings

    settings = get_settings()
    return _ip_from_forwarded_headers(
        websocket.headers.get("x-forwarded-for"),
        websocket.headers.get("x-real-ip"),
        max(0, settings.trusted_proxy_count),
        websocket.client.host if websocket.client else "unknown",
    )


def rate_limit_ws_connect(websocket) -> None:
    """Limit WS handshake bursts per client IP (not per nginx worker)."""
    ip = client_ip_websocket(websocket)
    check_rate_limit(
        f"rl:ws:connect:{ip}",
        limit=40,
        window_sec=60,
        message="实时连接过于频繁，请稍后再试",
    )


def rate_limit_agent(request: Request, user_id: int | None) -> None:
    if user_id:
        check_rate_limit(
            f"rl:agent:user:{user_id}",
            limit=10,
            window_sec=60,
            message=_MSG_AGENT,
        )
    else:
        check_rate_limit(
            f"rl:agent:ip:{client_ip(request)}",
            limit=30,
            window_sec=60,
            message=_MSG_AGENT,
        )


def rate_limit_insight(request: Request) -> None:
    check_rate_limit(
        f"rl:insight:ip:{client_ip(request)}",
        limit=30,
        window_sec=60,
        message=_MSG_INSIGHT,
    )


def rate_limit_verify_code(email: str, ip: str | None = None) -> None:
    email = email.strip().lower()
    check_rate_limit(
        f"rl:verify:email:{email}",
        limit=10,
        window_sec=900,
        message=_MSG_VERIFY,
    )
    if ip:
        check_rate_limit(
            f"rl:verify:ip:{ip}",
            limit=30,
            window_sec=900,
            message=_MSG_VERIFY,
        )


def rate_limit_send_code(email: str, ip: str | None = None) -> None:
    email = email.strip().lower()
    check_rate_limit(
        f"rl:code:email:{email}",
        limit=3,
        window_sec=3600,
        message=_MSG_SEND_CODE_EMAIL,
    )
    check_rate_limit(
        f"rl:code:cooldown:{email}",
        limit=1,
        window_sec=60,
        message=_MSG_SEND_CODE_COOLDOWN,
    )
    if ip:
        check_rate_limit(
            f"rl:code:ip:{ip}",
            limit=10,
            window_sec=3600,
            message=_MSG_SEND_CODE,
        )


def rate_limit_pay(user_id: int) -> None:
    check_rate_limit(
        f"rl:pay:user:{user_id}",
        limit=5,
        window_sec=60,
        message=_MSG_PAY,
    )


def rate_limit_pay_sync(user_id: int) -> None:
    """Separate bucket from create-order; sync is safe to retry often."""
    check_rate_limit(
        f"rl:pay_sync:user:{user_id}",
        limit=30,
        window_sec=60,
        message=_MSG_PAY,
    )


def rate_limit_redeem(user_id: int) -> None:
    check_rate_limit(
        f"rl:redeem:user:{user_id}",
        limit=10,
        window_sec=60,
        message=_MSG_REDEEM,
    )


def rate_limit_arena_spend(user_id: int) -> None:
    """Coin-spend arena/cheer actions per user."""
    check_rate_limit(
        f"rl:arena:user:{user_id}",
        limit=30,
        window_sec=60,
        message="操作过于频繁，请稍后再试",
    )


def rate_limit_collection_pass_spend(user_id: int) -> None:
    """Coin-spend collection pass actions (xp boost, event cheer)."""
    check_rate_limit(
        f"rl:collection_pass:spend:{user_id}",
        limit=20,
        window_sec=60,
        message="操作过于频繁，请稍后再试",
    )


def rate_limit_refresh(request: Request, refresh_token: str | None = None) -> None:
    check_rate_limit(f"rl:refresh:ip:{client_ip(request)}", limit=30, window_sec=60)
    if refresh_token:
        digest = hashlib.sha256(refresh_token.encode()).hexdigest()[:24]
        check_rate_limit(f"rl:refresh:token:{digest}", limit=10, window_sec=3600)


def rate_limit_referral_register(inviter_id: int, ip: str | None, *, limit: int = 3) -> None:
    """Same inviter + IP: max N registered bindings per day."""
    if not ip:
        return
    check_rate_limit(
        f"rl:referral:inviter:{inviter_id}:ip:{ip}",
        limit=limit,
        window_sec=86400,
    )


def rate_limit_global_ip(request: Request) -> None:
    from app.core.config import get_settings

    settings = get_settings()
    check_rate_limit(
        f"rl:global:ip:{client_ip(request)}",
        limit=settings.global_rate_limit_per_minute,
        window_sec=settings.global_rate_limit_window_sec,
        message=_MSG_GLOBAL,
    )


def reset_rate_limit_memory() -> None:
    """Test helper: clear in-memory buckets."""
    _memory.clear()
