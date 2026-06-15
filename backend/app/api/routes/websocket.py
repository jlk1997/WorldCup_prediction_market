"""WebSocket live score broadcast."""

from __future__ import annotations

import asyncio
import logging
import threading

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from starlette.websockets import WebSocketState

from app.core.cache import cache_get
from app.core.exceptions import RateLimitError
from app.core.rate_limit import rate_limit_ws_connect
from app.db.repositories.match_repository import MatchRepository
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])

_ws_connections = 0
_ws_lock = threading.Lock()
MAX_WS_CONNECTIONS = 100

_CLIENT_GONE_ERRORS = (
    WebSocketDisconnect,
    ConnectionResetError,
    BrokenPipeError,
    RuntimeError,
)


def _ws_client_ip(websocket: WebSocket) -> str:
    from app.core.rate_limit import client_ip_websocket

    return client_ip_websocket(websocket)


async def _reject_ws(websocket: WebSocket, code: int = 1013) -> None:
    try:
        await websocket.close(code=code)
    except Exception:
        pass


def _client_gone(exc: BaseException) -> bool:
    if isinstance(exc, _CLIENT_GONE_ERRORS):
        if isinstance(exc, RuntimeError):
            return "disconnect" in str(exc).lower() or "closed" in str(exc).lower()
        return True
    if isinstance(exc, OSError) and getattr(exc, "winerror", None) == 10054:
        return True
    return False


async def _safe_send_json(websocket: WebSocket, payload: dict) -> None:
    if websocket.client_state != WebSocketState.CONNECTED:
        raise WebSocketDisconnect(code=1000)
    try:
        await websocket.send_json(payload)
    except Exception as exc:
        if _client_gone(exc):
            raise WebSocketDisconnect(code=1000) from exc
        raise


async def _safe_close(websocket: WebSocket, code: int = 1000) -> None:
    try:
        if websocket.client_state == WebSocketState.CONNECTED:
            await websocket.close(code=code)
    except Exception as exc:
        if not _client_gone(exc):
            logger.debug("WebSocket close ignored: %s", exc)


def _live_payload(db: Session) -> list[dict]:
    cached = cache_get("live:matches:full")
    if cached:
        return cached

    repo = MatchRepository(db)
    payload = [
        {
            "id": m.id,
            "group": m.group_name,
            "date": m.match_date,
            "time": m.match_time,
            "team1": m.team1_name,
            "team2": m.team2_name,
            "stadium": m.stadium,
            "status": m.status or "scheduled",
            "home_score": m.home_score,
            "away_score": m.away_score,
            "minute": m.minute,
            "period": m.period,
            "is_live": m.status == "live",
        }
        for m in repo.list_schedule()
    ]
    return payload


@router.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    global _ws_connections
    try:
        rate_limit_ws_connect(websocket)
    except RateLimitError as exc:
        logger.warning(
            "WebSocket connect rate limited ip=%s msg=%s",
            _ws_client_ip(websocket),
            exc.message,
        )
        await _reject_ws(websocket, code=1013)
        return

    with _ws_lock:
        if _ws_connections >= MAX_WS_CONNECTIONS:
            await websocket.close(code=1013)
            return
        _ws_connections += 1

    await websocket.accept()
    try:
        while True:
            payload = cache_get("live:matches:full")
            if payload is None:
                db = SessionLocal()
                try:
                    payload = _live_payload(db)
                finally:
                    db.close()
            live_only = [m for m in payload if m.get("is_live") or m.get("home_score") is not None]
            await _safe_send_json(websocket, {"type": "live_update", "matches": live_only})
            try:
                await asyncio.sleep(30)
            except asyncio.CancelledError:
                raise WebSocketDisconnect(code=1000) from None
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as exc:
        if _client_gone(exc):
            logger.info("WebSocket client disconnected (%s)", type(exc).__name__)
        else:
            logger.warning("WebSocket error: %s", exc)
            await _safe_close(websocket)
    finally:
        await _safe_close(websocket)
        with _ws_lock:
            _ws_connections = max(0, _ws_connections - 1)


@router.websocket("/ws/user")
async def websocket_user(websocket: WebSocket):
    """Authenticated channel for predict_settled and other user events."""
    from app.core.user_ws_hub import drain_pending, subscribe, unsubscribe
    from app.db.repositories.user_repository import UserRepository
    from app.services.auth_service import AuthService

    token = websocket.query_params.get("token")
    if not token:
        await _reject_ws(websocket, code=4401)
        return
    try:
        rate_limit_ws_connect(websocket)
    except RateLimitError:
        await _reject_ws(websocket, code=1013)
        return

    db = SessionLocal()
    user_id: int | None = None
    try:
        user_id = AuthService(db).decode_user_id(token)
        user = UserRepository(db).get_by_id(user_id)
        if not user or user.status != "active":
            await _reject_ws(websocket, code=4401)
            return
    except Exception:
        await _reject_ws(websocket, code=4401)
        return
    finally:
        db.close()

    await websocket.accept()
    queue = subscribe(user_id)
    try:
        for msg in drain_pending(user_id):
            await _safe_send_json(websocket, msg)
        while True:
            try:
                msg = await asyncio.wait_for(queue.get(), timeout=25.0)
                await _safe_send_json(websocket, msg)
            except asyncio.TimeoutError:
                await _safe_send_json(websocket, {"type": "ping"})
    except WebSocketDisconnect:
        logger.info("User WebSocket disconnected user=%s", user_id)
    except Exception as exc:
        if not _client_gone(exc):
            logger.warning("User WebSocket error user=%s: %s", user_id, exc)
    finally:
        unsubscribe(user_id, queue)
        await _safe_close(websocket)
