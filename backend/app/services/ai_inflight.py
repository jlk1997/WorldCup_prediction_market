"""In-flight deduplication for identical match AI analysis requests."""

from __future__ import annotations

import hashlib
import logging
import time
from collections.abc import Callable
from dataclasses import dataclass

from app.core.distributed_lock import release_lock, try_acquire_lock
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)

INFLIGHT_TTL = 300
POLL_INTERVAL = 2.0
HEARTBEAT_INTERVAL = 5.0
FAILED_MARKER_TTL = 120

_local_failed: dict[str, float] = {}


def inflight_key(team1: str, team2: str, mode: str, live_fingerprint: str | None) -> str:
    a, b = sorted([team1.strip(), team2.strip()])
    fp = live_fingerprint or "-"
    raw = f"{a}|{b}|{mode}|{fp}"
    digest = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return f"ai:inflight:{digest}"


def _failed_key(key: str) -> str:
    return f"{key}:failed"


def _redis_set_failed(key: str, ttl_sec: int) -> None:
    from app.core.redis_client import get_redis_client

    r = get_redis_client()
    if r is None:
        _local_failed[key] = time.time() + ttl_sec
        return
    try:
        r.set(_failed_key(key), "1", ex=max(1, ttl_sec))
    except Exception as exc:
        logger.debug("Redis inflight failed marker: %s", exc)
        _local_failed[key] = time.time() + ttl_sec


def is_inflight_failed(key: str) -> bool:
    from app.core.redis_client import get_redis_client

    r = get_redis_client()
    if r is not None:
        try:
            if r.get(_failed_key(key)):
                return True
        except Exception:
            pass
    expiry = _local_failed.get(key)
    if expiry and expiry > time.time():
        return True
    if expiry:
        _local_failed.pop(key, None)
    return False


def mark_inflight_failed(key: str, ttl_sec: int = FAILED_MARKER_TTL) -> None:
    _redis_set_failed(key, ttl_sec)


@dataclass
class InflightAcquireResult:
    cached: dict | None = None
    token: str | None = None


def acquire_inflight_or_wait(
    key: str,
    wait_for_cache: Callable[[], dict | None],
    *,
    timeout_sec: int = INFLIGHT_TTL,
    on_poll: Callable[[float], None] | None = None,
) -> InflightAcquireResult:
    """
    Acquire leader lock or wait for another leader's cached result.
    Returns token for leaders (must release in finally) or cached payload for followers.
    """
    token = try_acquire_lock(key, ttl_sec=timeout_sec)
    if token:
        return InflightAcquireResult(token=token)

    start = time.time()
    last_heartbeat = start
    while time.time() - start < timeout_sec:
        if is_inflight_failed(key):
            raise ServiceUnavailableError("同对阵分析刚失败，请稍后重新发起")

        hit = wait_for_cache()
        if hit:
            return InflightAcquireResult(cached=hit)

        elapsed = time.time() - start
        if on_poll and time.time() - last_heartbeat >= HEARTBEAT_INTERVAL:
            on_poll(elapsed)
            last_heartbeat = time.time()

        token = try_acquire_lock(key, ttl_sec=timeout_sec)
        if token:
            return InflightAcquireResult(token=token)

        time.sleep(POLL_INTERVAL)

    raise ServiceUnavailableError("相同对阵分析正在进行中，请稍后再试")


def release_inflight(key: str, token: str | None) -> None:
    if token:
        release_lock(key, token)


# Backward-compatible alias
def run_as_leader_or_wait(
    key: str,
    wait_for_cache: Callable[[], dict | None],
    timeout_sec: int = INFLIGHT_TTL,
) -> tuple[bool, dict | None]:
    result = acquire_inflight_or_wait(key, wait_for_cache, timeout_sec=timeout_sec)
    if result.cached:
        return False, result.cached
    return True, None if result.token else None
