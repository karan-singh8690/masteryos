"""Correlation ID and request logging middleware.

Every request gets:
- A unique Request ID (UUID v4)
- A Correlation ID (from X-Correlation-Id header or generated)
- Request duration logging
- All bound to the structlog context for structured logging
"""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.shared.logging import bind_context, clear_context, get_logger

logger = get_logger(__name__)

REQUEST_ID_HEADER = "X-Request-ID"
CORRELATION_ID_HEADER = "X-Correlation-ID"


class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns request/correlation IDs and logs each request.

    IDs are:
    1. Read from request headers if provided by the client.
    2. Generated if not provided.
    3. Added to response headers.
    4. Bound to structlog context for structured logging.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Extract or generate IDs
        request_id = request.headers.get(REQUEST_ID_HEADER) or str(uuid.uuid4())
        correlation_id = request.headers.get(CORRELATION_ID_HEADER) or str(uuid.uuid4())

        # Bind to logging context
        bind_context(
            request_id=request_id,
            correlation_id=correlation_id,
            method=request.method,
            path=request.url.path,
        )

        # Process request
        start_time = time.perf_counter()
        status_code = 500  # default in case of unhandled exception

        try:
            response = await call_next(request)
            status_code = response.status_code

            # Add IDs to response headers
            response.headers[REQUEST_ID_HEADER] = request_id
            response.headers[CORRELATION_ID_HEADER] = correlation_id

            return response
        finally:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.info(
                "request_completed",
                status_code=status_code,
                duration_ms=duration_ms,
            )

            # Clear context for the next request
            clear_context()
