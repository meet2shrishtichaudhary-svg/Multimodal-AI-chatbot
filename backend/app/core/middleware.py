import time
import uuid
import logging
from typing import Dict, Tuple
from fastapi import Request, Response, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.metrics import metrics_collector

logger = logging.getLogger("mm_chatbot.security")

# Rate Limiter Bucket: {ip_address: (last_reset_timestamp, request_count)}
_rate_limit_store: Dict[str, Tuple[float, int]] = {}

AUTH_RATE_LIMIT = 15  # Max requests per window for auth routes
GENERAL_RATE_LIMIT = 120  # Max requests per window for general routes
RATE_LIMIT_WINDOW_SECONDS = 60.0

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Applies security headers to prevent clickjacking, MIME-sniffing,
    and restrict untrusted cross-origin frame embedding.
    """
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "microphone=(self), camera=()"
        return response

class CorrelationIdAndLoggingMiddleware(BaseHTTPMiddleware):
    """
    Attaches a unique Correlation ID (X-Correlation-ID) to each request
    and measures processing latency.
    """
    async def dispatch(self, request: Request, call_next):
        correlation_id = request.headers.get("X-Correlation-ID") or uuid.uuid4().hex
        request.state.correlation_id = correlation_id

        start_time = time.perf_counter()
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            metrics_collector.record_request(duration_ms, is_error=True)
            logger.error(f"[{correlation_id}] {request.method} {request.url.path} FAILED after {duration_ms:.1f}ms: {exc}")
            raise exc

        duration_ms = (time.perf_counter() - start_time) * 1000
        metrics_collector.record_request(duration_ms, is_error=(response.status_code >= 400))
        response.headers["X-Correlation-ID"] = correlation_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"

        # Redact query params in logs if sensitive
        path = request.url.path
        if not path.endswith("/health"):
            logger.info(f"[{correlation_id}] {request.method} {path} -> {response.status_code} ({duration_ms:.1f}ms)")

        return response

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Protects sensitive auth endpoints against brute force and DDoS attacks.
    """
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        client_ip = request.client.host if request.client else "127.0.0.1"

        # Check if route is rate-limited
        is_auth = any(endpoint in path for endpoint in ["/auth/login", "/auth/register", "/auth/forgot-password"])
        limit = AUTH_RATE_LIMIT if is_auth else GENERAL_RATE_LIMIT
        key = f"{client_ip}:{is_auth}"

        now = time.time()
        window_start, count = _rate_limit_store.get(key, (now, 0))

        if now - window_start > RATE_LIMIT_WINDOW_SECONDS:
            # New window
            _rate_limit_store[key] = (now, 1)
        else:
            if count >= limit:
                logger.warning(f"Rate limit exceeded for {client_ip} on {path} ({count}/{limit})")
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "detail": f"Rate limit exceeded. Please wait {int(RATE_LIMIT_WINDOW_SECONDS - (now - window_start))}s before retrying.",
                        "retry_after": int(RATE_LIMIT_WINDOW_SECONDS - (now - window_start))
                    },
                    headers={"Retry-After": str(int(RATE_LIMIT_WINDOW_SECONDS - (now - window_start)))}
                )
            _rate_limit_store[key] = (window_start, count + 1)

        return await call_next(request)
