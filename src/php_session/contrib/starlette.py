"""Starlette/FastAPI middleware for PHP session management.

Sets up session context for each request by extracting PHPSESSID cookie
and storing it in both request.state and contextvars for DI access.

Note: This middleware does NOT load session data - that's done lazily
by session_manager.get() or session_manager.lock() when needed.

Install with: pip install py-php-session[starlette]
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from ..context import set_current_session_id
from ..sanitize import sanitize_phpsessid


class PHPSessionMiddleware(BaseHTTPMiddleware):
    """Middleware to set up PHP session context.

    Sets session_id in:
    - request.state.session_id (for direct access in routes)
    - contextvars (for DI access in session_manager)

    Session data is NOT loaded here - use session_manager.get() or
    session_manager.lock() to load data lazily when needed.

    Usage:
        from fastapi import FastAPI
        from php_session.contrib.starlette import PHPSessionMiddleware

        app = FastAPI()
        app.add_middleware(PHPSessionMiddleware)

        # Or with logging:
        import logging
        logger = logging.getLogger("session")
        app.add_middleware(PHPSessionMiddleware, logger=logger)
    """

    def __init__(
        self,
        app: ASGIApp,
        logger: logging.Logger | None = None,
        cookie_name: str = "PHPSESSID",
    ) -> None:
        """Initialize the middleware.

        Args:
            app: The ASGI application.
            logger: Optional logger for debugging.
            cookie_name: Name of the session cookie (default: PHPSESSID).
        """
        super().__init__(app)
        self._logger = logger
        self._cookie_name = cookie_name

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Process the request and set up session context."""
        raw_phpsessid: str | None = request.cookies.get(self._cookie_name)
        phpsessid = sanitize_phpsessid(raw_phpsessid, logger=self._logger)

        if phpsessid:
            # Store in request.state for direct access
            request.state.session_id = phpsessid
            # Store in contextvars for session_manager DI
            set_current_session_id(phpsessid)
            if self._logger:
                self._logger.debug(
                    "Session context set: %s", phpsessid[:8] + "..."
                )

        try:
            return await call_next(request)
        finally:
            # Clean up contextvars
            set_current_session_id(None)
