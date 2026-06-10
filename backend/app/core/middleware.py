import logging
import sys
import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.exceptions import RateLimitError, rate_limit_error_body
from app.core.rate_limit import client_ip, rate_limit_global_ip

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"

_SKIP_GLOBAL_RL = frozenset({"/health", "/docs", "/redoc", "/openapi.json"})


def setup_logging(level: str = "INFO") -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=LOG_FORMAT,
        handlers=[logging.StreamHandler(sys.stdout)],
    )
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])
        start = time.perf_counter()
        logger = logging.getLogger("wc2026.request")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.exception(
                "request failed id=%s %s %s %.1fms",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "id=%s %s %s -> %s %.1fms",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    """IP-level fallback rate limit for all API routes."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        path = request.url.path
        if path.startswith("/api") and path not in _SKIP_GLOBAL_RL:
            try:
                rate_limit_global_ip(request)
            except RateLimitError as exc:
                logger.warning(
                    "global rate limit path=%s ip=%s msg=%s",
                    path,
                    client_ip(request),
                    exc.message,
                )
                return JSONResponse(
                    status_code=exc.status_code,
                    content=rate_limit_error_body(exc),
                    headers={"Retry-After": str(exc.retry_after_sec)},
                )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
        response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        return response
