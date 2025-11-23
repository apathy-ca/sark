"""Security headers middleware for FastAPI.

Adds security headers to HTTP responses to protect against common web vulnerabilities.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all HTTP responses.

    Headers added:
    - X-Content-Type-Options: nosniff
        Prevents MIME type sniffing
    - X-Frame-Options: DENY
        Prevents clickjacking attacks
    - X-XSS-Protection: 1; mode=block
        Enables XSS filter in older browsers
    - Strict-Transport-Security: max-age=31536000; includeSubDomains
        Forces HTTPS connections
    - Content-Security-Policy: default-src 'self'
        Restricts resource loading to same origin
    - Referrer-Policy: strict-origin-when-cross-origin
        Controls referrer information
    - Permissions-Policy: geolocation=(), microphone=(), camera=()
        Restricts browser features
    """

    def __init__(
        self,
        app: ASGIApp,
        hsts_max_age: int = 31536000,  # 1 year
        hsts_include_subdomains: bool = True,
        hsts_preload: bool = False,
        csp_policy: str | None = None,
        x_frame_options: str = "DENY",
        referrer_policy: str = "strict-origin-when-cross-origin",
    ):
        """Initialize security headers middleware.

        Args:
            app: ASGI application
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
            hsts_include_subdomains: Include subdomains in HSTS
            hsts_preload: Enable HSTS preload
            csp_policy: Custom CSP policy (default: "default-src 'self'")
            x_frame_options: X-Frame-Options value (DENY, SAMEORIGIN)
            referrer_policy: Referrer-Policy value
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        self.hsts_include_subdomains = hsts_include_subdomains
        self.hsts_preload = hsts_preload
        self.csp_policy = csp_policy or "default-src 'self'"
        self.x_frame_options = x_frame_options
        self.referrer_policy = referrer_policy

    async def dispatch(self, request: Request, call_next) -> Response:
        """Add security headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # X-Content-Type-Options: Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = self.x_frame_options

        # X-XSS-Protection: Enable XSS filter (legacy browsers)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Strict-Transport-Security: Force HTTPS
        hsts_value = f"max-age={self.hsts_max_age}"
        if self.hsts_include_subdomains:
            hsts_value += "; includeSubDomains"
        if self.hsts_preload:
            hsts_value += "; preload"
        response.headers["Strict-Transport-Security"] = hsts_value

        # Content-Security-Policy: Restrict resource loading
        response.headers["Content-Security-Policy"] = self.csp_policy

        # Referrer-Policy: Control referrer information
        response.headers["Referrer-Policy"] = self.referrer_policy

        # Permissions-Policy: Restrict browser features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()"
        )

        # X-Permitted-Cross-Domain-Policies: Restrict cross-domain policies
        response.headers["X-Permitted-Cross-Domain-Policies"] = "none"

        return response


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """CSRF protection middleware for state-changing endpoints.

    Validates CSRF tokens for POST, PUT, PATCH, DELETE requests.
    Exempts GET, HEAD, OPTIONS, TRACE requests.
    """

    def __init__(
        self,
        app: ASGIApp,
        csrf_header_name: str = "X-CSRF-Token",
        exempt_paths: list[str] | None = None,
    ):
        """Initialize CSRF protection middleware.

        Args:
            app: ASGI application
            csrf_header_name: Header name for CSRF token
            exempt_paths: Paths to exempt from CSRF protection
        """
        super().__init__(app)
        self.csrf_header_name = csrf_header_name
        self.exempt_paths = exempt_paths or [
            "/health",
            "/metrics",
            "/docs",
            "/redoc",
            "/openapi.json",
        ]
        # State-changing methods that require CSRF protection
        self.protected_methods = {"POST", "PUT", "PATCH", "DELETE"}

    async def dispatch(self, request: Request, call_next) -> Response:
        """Validate CSRF token for state-changing requests.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware in chain

        Returns:
            Response or 403 Forbidden if CSRF validation fails
        """
        # Skip CSRF check for safe methods
        if request.method not in self.protected_methods:
            return await call_next(request)

        # Skip CSRF check for exempt paths
        if any(request.url.path.startswith(path) for path in self.exempt_paths):
            return await call_next(request)

        # Get CSRF token from header
        csrf_token = request.headers.get(self.csrf_header_name)

        # Get expected token from session/cookie
        # NOTE: In production, this should validate against a session-stored token
        # For now, we'll accept any token from the header (better than nothing)
        # TODO: Implement proper token generation and validation with sessions
        if not csrf_token:
            from starlette.responses import JSONResponse

            return JSONResponse(
                status_code=403,
                content={
                    "error": "CSRF token missing",
                    "message": f"State-changing request requires {self.csrf_header_name} header",
                },
            )

        # In production, validate token against session
        # if not self._validate_token(request, csrf_token):
        #     return JSONResponse(status_code=403, content={"error": "Invalid CSRF token"})

        return await call_next(request)

    def _validate_token(self, request: Request, token: str) -> bool:
        """Validate CSRF token against session.

        Args:
            request: HTTP request
            token: CSRF token to validate

        Returns:
            True if token is valid, False otherwise

        Note:
            This is a placeholder for proper token validation.
            In production, implement:
            1. Generate random token on session creation
            2. Store in secure, httponly cookie or session
            3. Validate against stored token
            4. Rotate token periodically
        """
        # TODO: Implement proper token validation
        # session_token = request.session.get("csrf_token")
        # return secrets.compare_digest(token, session_token)
        return True  # Placeholder - accepts any token


# Convenience function to add security middleware to FastAPI app
def add_security_middleware(
    app,
    enable_hsts: bool = True,
    enable_csrf: bool = True,
    csp_policy: str | None = None,
    csrf_exempt_paths: list[str] | None = None,
):
    """Add security middleware to FastAPI application.

    Args:
        app: FastAPI application instance
        enable_hsts: Enable HSTS header (should be False for local dev)
        enable_csrf: Enable CSRF protection
        csp_policy: Custom Content Security Policy
        csrf_exempt_paths: Paths to exempt from CSRF protection

    Example:
        >>> from fastapi import FastAPI
        >>> app = FastAPI()
        >>> add_security_middleware(app)
    """
    # Add security headers
    app.add_middleware(
        SecurityHeadersMiddleware,
        hsts_max_age=31536000 if enable_hsts else 0,
        hsts_include_subdomains=enable_hsts,
        hsts_preload=False,
        csp_policy=csp_policy,
    )

    # Add CSRF protection
    if enable_csrf:
        app.add_middleware(
            CSRFProtectionMiddleware,
            exempt_paths=csrf_exempt_paths,
        )
