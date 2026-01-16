"""
API Rate Limiting Middleware for Quantum Admin
Prevents API abuse with configurable rate limits per endpoint/user
"""
import time
import logging
from typing import Optional, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
import redis
from functools import wraps

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Redis-based rate limiter using sliding window algorithm

    Features:
    - Per-IP rate limiting
    - Per-user rate limiting
    - Per-endpoint custom limits
    - Sliding window for accurate rate limiting
    - Automatic cleanup of expired keys
    """

    def __init__(
        self,
        redis_host: str = "localhost",
        redis_port: int = 6379,
        redis_db: int = 0,
        redis_password: Optional[str] = None
    ):
        try:
            self.redis_client = redis.Redis(
                host=redis_host,
                port=redis_port,
                db=redis_db,
                password=redis_password,
                decode_responses=False,  # Binary for performance
                socket_connect_timeout=5
            )
            self.redis_client.ping()
            self.enabled = True
            logger.info("Rate limiter initialized with Redis")
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"Redis unavailable, rate limiting disabled: {e}")
            self.redis_client = None
            self.enabled = False

    def _get_identifier(self, request: Request) -> str:
        """
        Get unique identifier for rate limiting

        Priority: User ID > API Key > IP Address
        """
        # Try to get user ID from auth
        user_id = getattr(request.state, "user_id", None)
        if user_id:
            return f"user:{user_id}"

        # Try to get API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"apikey:{api_key[:16]}"

        # Fall back to IP address
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            ip = forwarded_for.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"

        return f"ip:{ip}"

    def _get_rate_limit_key(self, identifier: str, endpoint: str) -> str:
        """Generate Redis key for rate limit tracking"""
        return f"ratelimit:{identifier}:{endpoint}"

    def check_rate_limit(
        self,
        request: Request,
        max_requests: int,
        window_seconds: int,
        endpoint: Optional[str] = None
    ) -> dict:
        """
        Check if request is within rate limit using sliding window

        Args:
            request: FastAPI request object
            max_requests: Maximum requests allowed in window
            window_seconds: Time window in seconds
            endpoint: Endpoint name (default: uses request path)

        Returns:
            dict with allowed, remaining, reset_time
        """
        if not self.enabled:
            return {
                "allowed": True,
                "remaining": max_requests,
                "reset_time": 0,
                "retry_after": 0
            }

        identifier = self._get_identifier(request)
        endpoint = endpoint or request.url.path
        key = self._get_rate_limit_key(identifier, endpoint)

        now = time.time()
        window_start = now - window_seconds

        try:
            pipe = self.redis_client.pipeline()

            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)

            # Count requests in current window
            pipe.zcard(key)

            # Add current request
            pipe.zadd(key, {str(now): now})

            # Set expiry
            pipe.expire(key, window_seconds)

            # Execute pipeline
            results = pipe.execute()

            request_count = results[1]  # Count after cleanup

            if request_count >= max_requests:
                # Rate limit exceeded
                oldest_entry = self.redis_client.zrange(key, 0, 0, withscores=True)
                if oldest_entry:
                    oldest_time = oldest_entry[0][1]
                    reset_time = oldest_time + window_seconds
                    retry_after = int(reset_time - now)
                else:
                    reset_time = now + window_seconds
                    retry_after = window_seconds

                return {
                    "allowed": False,
                    "remaining": 0,
                    "reset_time": int(reset_time),
                    "retry_after": max(retry_after, 1)
                }

            # Within rate limit
            remaining = max_requests - request_count - 1
            reset_time = now + window_seconds

            return {
                "allowed": True,
                "remaining": max(remaining, 0),
                "reset_time": int(reset_time),
                "retry_after": 0
            }

        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            # On error, allow the request
            return {
                "allowed": True,
                "remaining": max_requests,
                "reset_time": 0,
                "retry_after": 0
            }

    def limit(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        endpoint: Optional[str] = None
    ):
        """
        Decorator for rate limiting endpoints

        Usage:
            @app.get("/api/data")
            @rate_limiter.limit(max_requests=10, window_seconds=60)
            async def get_data(request: Request):
                return {"data": "value"}
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Extract request from args/kwargs
                request = None
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if not request:
                    request = kwargs.get("request")

                if not request:
                    logger.warning("No request object found for rate limiting")
                    return await func(*args, **kwargs)

                # Check rate limit
                result = self.check_rate_limit(
                    request,
                    max_requests,
                    window_seconds,
                    endpoint
                )

                # Add rate limit headers to response
                response = None

                if not result["allowed"]:
                    # Rate limit exceeded
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "error": "Rate limit exceeded",
                            "retry_after": result["retry_after"],
                            "limit": max_requests,
                            "window": window_seconds
                        },
                        headers={
                            "X-RateLimit-Limit": str(max_requests),
                            "X-RateLimit-Remaining": "0",
                            "X-RateLimit-Reset": str(result["reset_time"]),
                            "Retry-After": str(result["retry_after"])
                        }
                    )

                # Execute the function
                response = await func(*args, **kwargs)

                # Add rate limit headers to successful response
                if hasattr(response, "headers"):
                    response.headers["X-RateLimit-Limit"] = str(max_requests)
                    response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
                    response.headers["X-RateLimit-Reset"] = str(result["reset_time"])

                return response

            return wrapper
        return decorator


class RateLimitMiddleware:
    """
    FastAPI middleware for global rate limiting

    Applies default rate limits to all endpoints
    """

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        default_limit: int = 1000,
        default_window: int = 3600,
        exempt_paths: Optional[list] = None
    ):
        self.app = app
        self.rate_limiter = rate_limiter
        self.default_limit = default_limit
        self.default_window = default_window
        self.exempt_paths = exempt_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    async def __call__(self, request: Request, call_next):
        """Process request with rate limiting"""

        # Check if path is exempt
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Check rate limit
        result = self.rate_limiter.check_rate_limit(
            request,
            self.default_limit,
            self.default_window
        )

        # Add rate limit headers
        if not result["allowed"]:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "retry_after": result["retry_after"],
                    "limit": self.default_limit,
                    "window": self.default_window
                },
                headers={
                    "X-RateLimit-Limit": str(self.default_limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result["reset_time"]),
                    "Retry-After": str(result["retry_after"])
                }
            )

        # Continue with request
        response = await call_next(request)

        # Add rate limit headers to response
        response.headers["X-RateLimit-Limit"] = str(self.default_limit)
        response.headers["X-RateLimit-Remaining"] = str(result["remaining"])
        response.headers["X-RateLimit-Reset"] = str(result["reset_time"])

        return response


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create rate limiter instance"""
    global _rate_limiter

    if _rate_limiter is None:
        import os
        _rate_limiter = RateLimiter(
            redis_host=os.getenv("REDIS_HOST", "localhost"),
            redis_port=int(os.getenv("REDIS_PORT", "6379")),
            redis_db=int(os.getenv("REDIS_DB", "0")),
            redis_password=os.getenv("REDIS_PASSWORD")
        )

    return _rate_limiter


# ============================================================================
# RATE LIMIT PROFILES
# ============================================================================

# Common rate limit configurations
RATE_LIMITS = {
    "strict": {"max_requests": 10, "window_seconds": 60},      # 10/min
    "normal": {"max_requests": 100, "window_seconds": 60},     # 100/min
    "relaxed": {"max_requests": 1000, "window_seconds": 60},   # 1000/min
    "hourly": {"max_requests": 1000, "window_seconds": 3600},  # 1000/hour
    "daily": {"max_requests": 10000, "window_seconds": 86400}, # 10k/day
}


# ============================================================================
# Example Usage
# ============================================================================

if __name__ == "__main__":
    from fastapi import FastAPI

    app = FastAPI()
    limiter = RateLimiter()

    @app.get("/limited")
    @limiter.limit(max_requests=5, window_seconds=60)
    async def limited_endpoint(request: Request):
        return {"message": "This endpoint is rate limited"}

    @app.get("/strict")
    @limiter.limit(**RATE_LIMITS["strict"])
    async def strict_endpoint(request: Request):
        return {"message": "Strict rate limiting"}

    # Or use middleware for global rate limiting
    # app.middleware("http")(RateLimitMiddleware(app, limiter))
