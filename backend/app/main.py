import asyncio
import logging
import threading
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agent, arena, asset, card_duel, collectible, collection_pass, commerce, health, legal, live, marketplace, mint, news, players, predictions, profile, referral, schedule, stats, sync, teams, ui_config, websocket
from app.core.config import get_settings
from app.core.exceptions import AppError, RateLimitError, rate_limit_error_body
from app.core.middleware import GlobalRateLimitMiddleware, RequestLoggingMiddleware, SecurityHeadersMiddleware, setup_logging

logger = logging.getLogger(__name__)

_WIN_CONN_RESET_MARKERS = (
    "_ProactorBasePipeTransport._call_connection_lost",
    "远程主机强迫关闭了一个现有的连接",
    "An existing connection was forcibly closed",
)


def _asyncio_exception_handler(loop: asyncio.AbstractEventLoop, context: dict) -> None:
    """Suppress noisy Windows proactor errors when browsers close WebSocket tabs."""
    exc = context.get("exception")
    message = context.get("message", "")
    if isinstance(exc, ConnectionResetError):
        logger.debug("Client connection reset: %s", exc)
        return
    if any(marker in message for marker in _WIN_CONN_RESET_MARKERS):
        logger.debug("Asyncio transport closed after client disconnect: %s", exc or message)
        return
    loop.default_exception_handler(context)


_WEAK_JWT_SECRETS = frozenset({"change-me-in-production", "wc2026-jwt-a8f3k2m9p7x1n5q4r6t0v2w8y3z7b1c5d9e2f4"})


def _validate_production_settings(settings) -> None:
    if not settings.production_mode:
        return
    if settings.jwt_secret in _WEAK_JWT_SECRETS or len(settings.jwt_secret) < 32:
        raise RuntimeError("生产环境 JWT_SECRET 必须为 32 字符以上强随机串")
    if settings.alipay_mock:
        raise RuntimeError("生产环境必须关闭 ALIPAY_MOCK")
    if settings.auth_dev_mode:
        raise RuntimeError("生产环境必须关闭 AUTH_DEV_MODE")
    if settings.allow_manual_sync and not settings.admin_sync_secret:
        raise RuntimeError("生产环境开启手动同步时必须设置 ADMIN_SYNC_SECRET")
    if not settings.redis_url:
        raise RuntimeError("生产环境必须配置 REDIS_URL")
    if settings.db_password == "postgres":
        raise RuntimeError("生产环境 DB_PASSWORD 不能使用默认值 postgres")
    if settings.alipay_sandbox:
        raise RuntimeError("生产环境必须关闭 ALIPAY_SANDBOX")
    if not settings.alipay_configured:
        raise RuntimeError("生产环境必须配置完整支付宝证书（AppID + 私钥 + 三份证书）")
    if any("localhost" in o.lower() for o in settings.cors_origin_list):
        raise RuntimeError("生产环境 CORS_ORIGINS 不能包含 localhost")
    if not settings.smtp_host:
        raise RuntimeError("生产环境必须配置 SMTP 以发送登录验证码")


def _background_ingest_loop() -> None:
    from app.core.distributed_lock import distributed_lock
    from app.ingest.scheduler import run_once

    settings = get_settings()
    logger.info(
        "Background ingest started (live=%ss idle=%ss)",
        settings.live_poll_interval_live,
        settings.live_poll_interval_idle,
    )
    while True:
        sleep_sec = settings.live_poll_interval_idle
        with distributed_lock("ingest:leader", ttl_sec=max(120, settings.live_poll_interval_idle + 60)) as leader:
            if not leader:
                time.sleep(min(30, settings.live_poll_interval_idle))
                continue
            try:
                has_live = run_once()
            except Exception:
                logger.exception("Background ingest cycle failed")
                has_live = False
            sleep_sec = settings.live_poll_interval_live if has_live else settings.live_poll_interval_idle
        time.sleep(sleep_sec)


@asynccontextmanager
async def _lifespan(_: FastAPI):
    settings = get_settings()
    _validate_production_settings(settings)
    loop = asyncio.get_running_loop()
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(_asyncio_exception_handler)
    if settings.enable_background_ingest:
        thread = threading.Thread(
            target=_background_ingest_loop,
            daemon=True,
            name="wc2026-ingest",
        )
        thread.start()
    try:
        from app.db.session import SessionLocal
        from app.services.ai_analysis_job_service import AiAnalysisJobService

        db = SessionLocal()
        try:
            AiAnalysisJobService(db).recover_stale_jobs()
        finally:
            db.close()
    except Exception:
        logger.exception("Stale AI job recovery on startup failed")
    if not settings.production_mode:
        try:
            from app.services.primary_mint_service import PrimaryMintService

            db = SessionLocal()
            try:
                PrimaryMintService(db).seed_collab_events()
                db.commit()
                logger.info("Dev collab catalog/events seeded")
            finally:
                db.close()
        except Exception:
            logger.exception("Dev collab seed on startup failed")
    try:
        yield
    finally:
        loop.set_exception_handler(previous_handler)


def create_app() -> FastAPI:
    settings = get_settings()
    setup_logging()
    app = FastAPI(
        title="世界杯预测协助系统 API",
        version="2.0.0",
        docs_url=None if settings.production_mode else "/docs",
        redoc_url=None if settings.production_mode else "/redoc",
        openapi_url=None if settings.production_mode else "/openapi.json",
        lifespan=_lifespan,
    )

    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=800)
    app.add_middleware(GlobalRateLimitMiddleware)
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Admin-Secret", "X-Request-ID"],
    )

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError):
        if isinstance(exc, RateLimitError):
            return JSONResponse(
                status_code=exc.status_code,
                content=rate_limit_error_body(exc),
                headers={"Retry-After": str(exc.retry_after_sec)},
            )
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": "error", "message": exc.message},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_: Request, exc: RequestValidationError):
        content = {"status": "error", "message": "请求参数校验失败"}
        if not settings.production_mode:
            content["details"] = exc.errors()
        return JSONResponse(status_code=422, content=content)

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_: Request, exc: Exception):
        logger.exception("Unhandled error: %s", exc)
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "服务器内部错误"},
        )

    app.include_router(health.router)
    app.include_router(schedule.router)
    app.include_router(stats.router)
    app.include_router(live.router)
    app.include_router(news.router)
    app.include_router(sync.router)
    app.include_router(agent.router)
    app.include_router(teams.router)
    app.include_router(players.router)
    app.include_router(predictions.router)
    app.include_router(websocket.router)
    app.include_router(commerce.router_auth)
    app.include_router(commerce.router_game)
    app.include_router(commerce.router_shop)
    app.include_router(commerce.router_pay)
    app.include_router(commerce.router_wallet)
    app.include_router(profile.router)
    app.include_router(arena.router)
    app.include_router(collectible.router)
    app.include_router(collection_pass.router)
    app.include_router(asset.router)
    app.include_router(card_duel.router)
    app.include_router(marketplace.router)
    app.include_router(mint.router)
    app.include_router(referral.router)
    app.include_router(legal.router)
    app.include_router(ui_config.router)

    from app.api.routes import share as share_routes
    from app.api.routes import widget as widget_routes
    from app.api.routes import analytics as analytics_routes

    app.include_router(share_routes.router)
    app.include_router(widget_routes.router)
    app.include_router(analytics_routes.router)

    return app


app = create_app()
