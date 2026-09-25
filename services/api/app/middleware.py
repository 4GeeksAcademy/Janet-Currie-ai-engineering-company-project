"""Optional structured request timing. Never logs bodies, tokens, or emails."""

from __future__ import annotations

import logging
import os
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp

logger = logging.getLogger("healthcore.timing")


def request_timing_enabled() -> bool:
    raw = os.getenv("REQUEST_TIMING", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


class RequestTimingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):
        if not request_timing_enabled():
            return await call_next(request)
        started = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            return response
        except Exception:
            status = 500
            raise
        finally:
            elapsed_ms = (time.perf_counter() - started) * 1000
            route = request.scope.get("route")
            path = getattr(route, "path", None) or request.url.path
            logger.info(
                "request_timing method=%s path=%s status=%s elapsed_ms=%.2f",
                request.method,
                path,
                status,
                elapsed_ms,
            )
