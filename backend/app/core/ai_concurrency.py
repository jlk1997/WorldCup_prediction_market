"""Global LLM concurrency guard (process + Redis)."""

from __future__ import annotations

import asyncio
import logging
import threading
import time
import uuid

from app.core.config import get_settings
from app.core.exceptions import ServiceUnavailableError

logger = logging.getLogger(__name__)

_sync_semaphore: threading.Semaphore | None = None
_async_semaphore: asyncio.Semaphore | None = None

LLM_SLOT_KEY = "ai:llm:inflight"
LLM_SLOT_TTL = 600
LLM_SLOT_WAIT_SEC = 180


def _limit() -> int:
    return max(1, get_settings().ai_max_concurrent_llm)


def _redis_client():
    from app.core.redis_client import get_redis_client

    return get_redis_client()


def get_sync_semaphore() -> threading.Semaphore:
    global _sync_semaphore
    if _sync_semaphore is None:
        _sync_semaphore = threading.Semaphore(_limit())
    return _sync_semaphore


def reset_sync_semaphore() -> None:
    """Test helper: rebuild semaphore after settings change."""
    global _sync_semaphore
    _sync_semaphore = None


class _LocalSlot:
    __slots__ = ("token",)

    def __init__(self, token: str):
        self.token = token


_local_slots: set[str] = set()
_local_slots_guard = threading.Lock()


def _local_acquire() -> _LocalSlot | None:
    limit = _limit()
    token = uuid.uuid4().hex
    deadline = time.time() + LLM_SLOT_WAIT_SEC
    while time.time() < deadline:
        with _local_slots_guard:
            if len(_local_slots) < limit:
                _local_slots.add(token)
                return _LocalSlot(token)
        time.sleep(0.15)
    return None


def _local_release(slot: _LocalSlot | None) -> None:
    if not slot:
        return
    with _local_slots_guard:
        _local_slots.discard(slot.token)


def acquire_llm_slot(timeout_sec: float = LLM_SLOT_WAIT_SEC) -> _LocalSlot | str:
    """
    Acquire one LLM slot. Returns 'redis' when using Redis counter, else _LocalSlot.
    Falls back to threading.Semaphore when Redis unavailable.
    """
    r = _redis_client()
    if r is None:
        if not get_sync_semaphore().acquire(timeout=max(0.1, timeout_sec)):
            raise ServiceUnavailableError("AI 分析排队已满，请稍后再试")
        return "thread"

    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            active = int(r.incr(LLM_SLOT_KEY))
            r.expire(LLM_SLOT_KEY, LLM_SLOT_TTL)
            if active <= _limit():
                return "redis"
            r.decr(LLM_SLOT_KEY)
        except Exception as exc:
            logger.debug("Redis LLM slot fallback to local: %s", exc)
            slot = _local_acquire()
            if slot:
                return slot
            raise ServiceUnavailableError("AI 分析排队已满，请稍后再试") from exc
        time.sleep(0.15)

    raise ServiceUnavailableError("AI 分析排队已满，请稍后再试")


def release_llm_slot(handle: _LocalSlot | str | None) -> None:
    if not handle:
        return
    if handle == "thread":
        get_sync_semaphore().release()
        return
    if handle == "redis":
        r = _redis_client()
        if r is not None:
            try:
                r.decr(LLM_SLOT_KEY)
            except Exception as exc:
                logger.debug("Redis LLM slot release: %s", exc)
        return
    if isinstance(handle, _LocalSlot):
        _local_release(handle)


def llm_queue_depth() -> dict:
    """Best-effort active/waiting depth for status APIs."""
    limit = _limit()
    r = _redis_client()
    if r is not None:
        try:
            active = int(r.get(LLM_SLOT_KEY) or 0)
            return {"active": max(0, active), "limit": limit, "source": "redis"}
        except Exception:
            pass
    with _local_slots_guard:
        active = len(_local_slots)
    return {"active": active, "limit": limit, "source": "local"}


class LLMSemaphore:
    """Context manager wrapping acquire_llm_slot / release_llm_slot."""

    def __init__(self):
        self._handle: _LocalSlot | str | None = None

    def __enter__(self):
        self._handle = acquire_llm_slot()
        return self

    def __exit__(self, *args):
        release_llm_slot(self._handle)
        self._handle = None
