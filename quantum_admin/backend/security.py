"""
Quantum Admin - Security Middleware & Utilities

Provides enterprise-grade security features:
- Security headers (HSTS, CSP, X-Frame-Options, etc.)
- Rate limiting
- Input sanitization
- CSRF protection
- Request validation
"""

import hashlib
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from functools import wraps
from typing import Callable, Dict, Optional, Set, List
from urllib.parse import urlparse

from fastapi import Request, Response, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.datastructures import Headers

from .observability import get_logger

logger = get_logger()


# ============================================================================
# Security Headers Middleware
# ============================================================================

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS)
    - X-Content-Type-Options
    - X-Frame-Options
    - X-XSS-Protection
    - Content-Security-Policy (CSP)
    - Referrer-Policy
    - Permissions-Policy
    """

    def __init__(
        self,
        app,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = True,
        frame_options: str = "DENY",  # DENY, SAMEORIGIN, or ALLOW-FROM
        csp_directives: Optional[Dict[str, str]] = None,
        enable_cors: bool = True,
        allowed_origins: Optional[List[str]] = None,
    ):
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.frame_options = frame_options
        self.enable_cors = enable_cors
        self.allowed_origins = allowed_origins or ["http://localhost:3000", "http://localhost:8000"]

        # Default CSP directives (strict but functional)
        self.csp_directives = csp_directives or {
            "default-src": "'self'",
            "script-src": "'self' 'unsafe-inline' 'unsafe-eval'",  # Needed for React
            "style-src": "'self' 'unsafe-inline'",  # Needed for styled-components
            "img-src": "'self' data: https:",
            "font-src": "'self' data:",
            "connect-src": "'self' ws: wss:",  # WebSocket support
            "frame-ancestors": "'none'",
            "base-uri": "'self'",
            "form-action": "'self'",
        }

    def _build_csp_header(self) -> str:
        """Build Content-Security-Policy header value"""
        return "; ".join(
            f"{directive} {value}"
            for directive, value in self.csp_directives.items()
        )

    def _build_hsts_header(self) -> str:
        """Build Strict-Transport-Security header value"""
        parts = [f"max-age={self.hsts_max_age}"]
        if self.hsts_include_subdomains:
            parts.append("includeSubDomains")
        if self.hsts_preload:
            parts.append("preload")
        return "; ".join(parts)

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        # Skip for health checks to reduce noise
        if request.url.path in ["/health", "/metrics"]:
            return await call_next(request)

        response = await call_next(request)

        # HSTS - Force HTTPS
        response.headers["Strict-Transport-Security"] = self._build_hsts_header()

        # Prevent MIME-sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Clickjacking protection
        response.headers["X-Frame-Options"] = self.frame_options

        # XSS Protection (legacy but still good)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy
        response.headers["Content-Security-Policy"] = self._build_csp_header()

        # Referrer Policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (formerly Feature-Policy)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # Remove server identification
        response.headers.pop("Server", None)
        response.headers.pop("X-Powered-By", None)

        # CORS headers (if enabled)
        if self.enable_cors:
            origin = request.headers.get("origin")
            if origin in self.allowed_origins:
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS, PATCH"
                response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization, X-CSRF-Token"
                response.headers["Access-Control-Max-Age"] = "3600"

        logger.info("Security headers added", extra={
            "path": request.url.path,
            "method": request.method,
            "origin": request.headers.get("origin", "none")
        })

        return response


# ============================================================================
# Rate Limiting
# ============================================================================

class RateLimiter:
    """
    Token bucket rate limiter.

    Limits requests per IP address or per user.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        cleanup_interval: int = 300,  # 5 minutes
    ):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.cleanup_interval = cleanup_interval

        # Storage: {identifier: {"tokens": float, "last_update": float}}
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": float(burst_size), "last_update": time.time()}
        )

        self.last_cleanup = time.time()

    def _cleanup_old_buckets(self):
        """Remove old buckets to prevent memory leak"""
        now = time.time()
        if now - self.last_cleanup > self.cleanup_interval:
            cutoff = now - self.cleanup_interval
            self.buckets = {
                k: v for k, v in self.buckets.items()
                if v["last_update"] > cutoff
            }
            self.last_cleanup = now

    def _refill_bucket(self, identifier: str) -> Dict[str, float]:
        """Refill tokens based on time elapsed"""
        bucket = self.buckets[identifier]
        now = time.time()

        # Calculate tokens to add
        elapsed = now - bucket["last_update"]
        tokens_to_add = elapsed * (self.requests_per_minute / 60.0)

        # Update bucket
        bucket["tokens"] = min(
            self.burst_size,
            bucket["tokens"] + tokens_to_add
        )
        bucket["last_update"] = now

        return bucket

    def is_allowed(self, identifier: str) -> bool:
        """
        Check if request is allowed.

        Args:
            identifier: IP address or user ID

        Returns:
            True if allowed, False if rate limited
        """
        self._cleanup_old_buckets()

        bucket = self._refill_bucket(identifier)

        if bucket["tokens"] >= 1.0:
            bucket["tokens"] -= 1.0
            return True

        return False

    def get_retry_after(self, identifier: str) -> int:
        """Get seconds until next request allowed"""
        bucket = self.buckets[identifier]
        tokens_needed = 1.0 - bucket["tokens"]
        seconds_per_token = 60.0 / self.requests_per_minute
        return int(tokens_needed * seconds_per_token) + 1


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limits"""

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int = 10,
        exclude_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.limiter = RateLimiter(requests_per_minute, burst_size)
        self.exclude_paths = exclude_paths or {"/health", "/metrics"}

    def _get_identifier(self, request: Request) -> str:
        """Get unique identifier for rate limiting"""
        # Use authenticated user if available
        if hasattr(request.state, "user") and request.state.user:
            return f"user:{request.state.user.id}"

        # Fall back to IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()

        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        """Check rate limit before processing request"""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        identifier = self._get_identifier(request)

        if not self.limiter.is_allowed(identifier):
            retry_after = self.limiter.get_retry_after(identifier)

            logger.warning("Rate limit exceeded", extra={
                "identifier": identifier,
                "path": request.url.path,
                "retry_after": retry_after
            })

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": True,
                    "message": "Rate limit exceeded",
                    "retry_after": retry_after
                },
                headers={"Retry-After": str(retry_after)}
            )

        response = await call_next(request)

        # Add rate limit info headers
        response.headers["X-RateLimit-Limit"] = str(self.limiter.requests_per_minute)

        return response


# ============================================================================
# CSRF Protection
# ============================================================================

class CSRFProtection:
    """
    CSRF token generation and validation.

    Uses double-submit cookie pattern.
    """

    def __init__(self, secret_key: str):
        self.secret_key = secret_key

    def generate_token(self) -> str:
        """Generate a new CSRF token"""
        return secrets.token_urlsafe(32)

    def validate_token(self, token: str, cookie_token: str) -> bool:
        """
        Validate CSRF token.

        Args:
            token: Token from request header/body
            cookie_token: Token from cookie

        Returns:
            True if valid, False otherwise
        """
        if not token or not cookie_token:
            return False

        return secrets.compare_digest(token, cookie_token)


class CSRFMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce CSRF protection"""

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS", "TRACE"}

    def __init__(
        self,
        app,
        secret_key: str,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        exclude_paths: Optional[Set[str]] = None,
    ):
        super().__init__(app)
        self.csrf = CSRFProtection(secret_key)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.exclude_paths = exclude_paths or {
            "/health", "/metrics", "/api/docs", "/api/redoc", "/api/openapi.json"
        }

    async def dispatch(self, request: Request, call_next):
        """Validate CSRF token for unsafe methods"""
        # Skip excluded paths
        if request.url.path in self.exclude_paths:
            return await call_next(request)

        # Skip safe methods
        if request.method in self.SAFE_METHODS:
            response = await call_next(request)

            # Set CSRF cookie if not present
            if self.cookie_name not in request.cookies:
                token = self.csrf.generate_token()
                response.set_cookie(
                    key=self.cookie_name,
                    value=token,
                    httponly=True,
                    secure=True,
                    samesite="strict",
                    max_age=3600 * 24  # 24 hours
                )

            return response

        # Validate CSRF token for unsafe methods
        request_token = request.headers.get(self.header_name)
        cookie_token = request.cookies.get(self.cookie_name)

        if not self.csrf.validate_token(request_token, cookie_token):
            logger.warning("CSRF validation failed", extra={
                "path": request.url.path,
                "method": request.method,
                "has_token": bool(request_token),
                "has_cookie": bool(cookie_token)
            })

            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error": True,
                    "message": "CSRF validation failed",
                    "details": "Invalid or missing CSRF token"
                }
            )

        return await call_next(request)


# ============================================================================
# Input Sanitization
# ============================================================================

class InputSanitizer:
    """Utility class for input sanitization"""

    # Common XSS patterns
    XSS_PATTERNS = [
        r"<script[^>]*>.*?</script>",
        r"javascript:",
        r"on\w+\s*=",
        r"<iframe",
        r"<object",
        r"<embed",
    ]

    # SQL injection patterns
    SQL_PATTERNS = [
        r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|CREATE|ALTER|EXEC|EXECUTE)\b)",
        r"(--|\#|\/\*)",
        r"(\bOR\b.*=.*)",
        r"(\bAND\b.*=.*)",
        r"(\bUNION\b)",
    ]

    @staticmethod
    def sanitize_string(value: str, max_length: int = 1000) -> str:
        """
        Sanitize string input.

        Args:
            value: Input string
            max_length: Maximum allowed length

        Returns:
            Sanitized string
        """
        if not isinstance(value, str):
            return str(value)

        # Trim
        value = value.strip()

        # Limit length
        if len(value) > max_length:
            value = value[:max_length]

        # Remove null bytes
        value = value.replace("\x00", "")

        return value

    @staticmethod
    def sanitize_filename(filename: str) -> str:
        """
        Sanitize filename to prevent directory traversal.

        Args:
            filename: Original filename

        Returns:
            Safe filename
        """
        import os
        import re

        # Remove path separators
        filename = os.path.basename(filename)

        # Remove non-alphanumeric characters (keep dots, dashes, underscores)
        filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)

        # Remove leading dots (hidden files)
        filename = filename.lstrip('.')

        # Limit length
        if len(filename) > 255:
            name, ext = os.path.splitext(filename)
            filename = name[:255 - len(ext)] + ext

        return filename or "unnamed"

    @staticmethod
    def validate_email(email: str) -> bool:
        """
        Validate email format.

        Args:
            email: Email address

        Returns:
            True if valid, False otherwise
        """
        import re

        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    @staticmethod
    def validate_url(url: str, allowed_schemes: Set[str] = {"http", "https"}) -> bool:
        """
        Validate URL format and scheme.

        Args:
            url: URL to validate
            allowed_schemes: Set of allowed schemes

        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = urlparse(url)
            return parsed.scheme in allowed_schemes and bool(parsed.netloc)
        except Exception:
            return False


# ============================================================================
# Security Decorators
# ============================================================================

def require_https(func: Callable) -> Callable:
    """Decorator to require HTTPS for endpoint"""
    @wraps(func)
    async def wrapper(request: Request, *args, **kwargs):
        if not request.url.scheme == "https" and not request.url.hostname == "localhost":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="HTTPS required"
            )
        return await func(request, *args, **kwargs)

    return wrapper


def validate_content_type(allowed_types: Set[str]):
    """Decorator to validate request content type"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(request: Request, *args, **kwargs):
            content_type = request.headers.get("content-type", "")

            # Extract base content type (ignore charset)
            base_type = content_type.split(";")[0].strip()

            if base_type not in allowed_types:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail=f"Content-Type must be one of: {', '.join(allowed_types)}"
                )

            return await func(request, *args, **kwargs)

        return wrapper

    return decorator


# ============================================================================
# Security Utilities
# ============================================================================

def hash_sensitive_data(data: str) -> str:
    """
    Hash sensitive data for logging/storage.

    Args:
        data: Sensitive data (email, IP, etc.)

    Returns:
        SHA256 hash (first 16 chars)
    """
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def is_safe_redirect_url(url: str, allowed_hosts: Set[str]) -> bool:
    """
    Check if redirect URL is safe (prevents open redirect).

    Args:
        url: Redirect URL
        allowed_hosts: Set of allowed hostnames

    Returns:
        True if safe, False otherwise
    """
    try:
        parsed = urlparse(url)

        # Relative URLs are safe
        if not parsed.netloc:
            return True

        # Check if hostname is allowed
        return parsed.netloc in allowed_hosts
    except Exception:
        return False


def generate_secure_token(length: int = 32) -> str:
    """
    Generate cryptographically secure random token.

    Args:
        length: Token length in bytes

    Returns:
        URL-safe token string
    """
    return secrets.token_urlsafe(length)


# ============================================================================
# Export all
# ============================================================================

__all__ = [
    "SecurityHeadersMiddleware",
    "RateLimiter",
    "RateLimitMiddleware",
    "CSRFProtection",
    "CSRFMiddleware",
    "InputSanitizer",
    "require_https",
    "validate_content_type",
    "hash_sensitive_data",
    "is_safe_redirect_url",
    "generate_secure_token",
]
