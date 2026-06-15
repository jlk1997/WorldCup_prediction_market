"""In-memory hub for user-scoped WebSocket push (predict_settled)."""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict, deque
from typing import Any

logger = logging.getLogger(__name__)

_MAX_QUEUE = 20
_pending: dict[int, deque[dict[str, Any]]] = defaultdict(lambda: deque(maxlen=_MAX_QUEUE))
_subscribers: dict[int, set[asyncio.Queue]] = defaultdict(set)


def push_predict_settled(user_id: int, payload: dict[str, Any]) -> None:
    msg = {"type": "predict_settled", "payload": payload}
    _pending[user_id].append(msg)
    for q in list(_subscribers.get(user_id, ())):
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            logger.debug("User WS queue full user=%s", user_id)


def drain_pending(user_id: int) -> list[dict[str, Any]]:
    items = list(_pending.get(user_id, ()))
    _pending[user_id].clear()
    return items


def subscribe(user_id: int) -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue(maxsize=_MAX_QUEUE)
    _subscribers[user_id].add(q)
    return q


def unsubscribe(user_id: int, q: asyncio.Queue) -> None:
    subs = _subscribers.get(user_id)
    if subs:
        subs.discard(q)
        if not subs:
            _subscribers.pop(user_id, None)
