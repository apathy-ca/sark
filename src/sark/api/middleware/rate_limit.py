"""Rate limiting middleware for FastAPI."""

from collections.abc import Callable
import logging

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from sark.config.settings import Settings
from sark.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to enforce rate limiting based on API key, user, or IP.

    Rate limits are applied in the following order of precedence:
    1. API Key: If X-API-Key header is present
    2. JWT User: If Authorization header with valid JWT is present
    3. IP Address: Fallback for unauthenticated requests

    Admin users can bypass rate limits if configured.

    Attributes:
        rate_limiter: RateLimiter service instance
        settings: Application settings
    """

    def __init__(
        self,
        app: ASGIApp,
        rate_limiter: RateLimiter,
        settings: Settings,
    ):
        """Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter service instance
            settings: Application settings
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.settings = settings

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        """Process request with rate limiting.

        Args:
            request: Incoming request
            call_next: Next middleware/route handler

        Returns:
            Response with rate limit headers
        """
        # Skip rate limiting if disabled
        if not self.settings.rate_limit_enabled:
            return await call_next(request)

        # Skip rate limiting for health check endpoints
        if request.url.path in ["/health", "/api/health", "/metrics"]:
            return await call_next(request)

        # Determine identifier and limit based on auth method
        identifier, limit = await self._get_identifier_and_limit(request)

        # Check if user is admin and can bypass
        if self.settings.rate_limit_admin_bypass and await self._is_admin(request):
            logger.debug(f"Admin bypass for {identifier}")
            response = await call_next(request)
            self._add_rate_limit_headers(
                response,
                limit=999999,
                remaining=999999,
                reset_at=0,
            )
            return response

        # Check rate limit
        rate_info = await self.rate_limiter.check_rate_limit(
            identifier=identifier,
            limit=limit,
        )

        # If rate limit exceeded, return 429
        if not rate_info.allowed:
            logger.warning(
                f"Rate limit exceeded for {identifier}: "
                f"{rate_info.limit} requests per window"
            )
            response = JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {rate_info.limit} per hour",
                    "retry_after": rate_info.retry_after,
                },
            )
            self._add_rate_limit_headers(
                response,
                limit=rate_info.limit,
                remaining=rate_info.remaining,
                reset_at=rate_info.reset_at,
                retry_after=rate_info.retry_after,
            )
            return response

        # Process request
        response = await call_next(request)

        # Add rate limit headers to response
        self._add_rate_limit_headers(
            response,
            limit=rate_info.limit,
            remaining=rate_info.remaining,
            reset_at=rate_info.reset_at,
        )

        return response

    async def _get_identifier_and_limit(self, request: Request) -> tuple[str, int]:
        """Determine rate limit identifier and limit for request.

        Priority order:
        1. API Key (X-API-Key header)
        2. JWT User (Authorization header)
        3. IP Address (fallback)

        Args:
            request: Incoming request

        Returns:
            Tuple of (identifier, limit)
        """
        # Check for API key
        api_key = request.headers.get("X-API-Key")
        if api_key:
            return f"api_key:{api_key}", self.settings.rate_limit_per_api_key

        # Check for JWT in Authorization header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            # Extract user ID from request state if available
            # (would be set by authentication middleware)
            user_id = getattr(request.state, "user_id", None)
            if user_id:
                return f"user:{user_id}", self.settings.rate_limit_per_user

            # If no user_id in state, use token hash as identifier
            token = auth_header.split(" ", 1)[1]
            token_hash = hash(token) % (10 ** 8)  # Use hash for privacy
            return f"token:{token_hash}", self.settings.rate_limit_per_user

        # Fallback to IP address
        # Check X-Forwarded-For header first (for reverse proxies)
        client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP", "")
        if not client_ip and request.client:
            client_ip = request.client.host

        return f"ip:{client_ip or 'unknown'}", self.settings.rate_limit_per_ip

    async def _is_admin(self, request: Request) -> bool:
        """Check if user has admin privileges.

        Args:
            request: Incoming request

        Returns:
            True if user is admin, False otherwise
        """
        # Check if user has admin role (would be set by auth middleware)
        user_roles = getattr(request.state, "user_roles", [])
        return "admin" in user_roles or "administrator" in user_roles

    def _add_rate_limit_headers(
        self,
        response: Response,
        limit: int,
        remaining: int,
        reset_at: int,
        retry_after: int | None = None,
    ) -> None:
        """Add standard rate limit headers to response.

        Headers follow the IETF draft standard:
        - X-RateLimit-Limit: Maximum requests per window
        - X-RateLimit-Remaining: Remaining requests in current window
        - X-RateLimit-Reset: Unix timestamp when window resets
        - Retry-After: Seconds until rate limit resets (if limited)

        Args:
            response: Response object to add headers to
            limit: Maximum requests allowed
            remaining: Remaining requests
            reset_at: Unix timestamp for reset
            retry_after: Seconds until reset (optional)
        """
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_at)

        if retry_after is not None:
            response.headers["Retry-After"] = str(retry_after)
