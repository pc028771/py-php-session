"""Tests for PHPSessionMiddleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from starlette.requests import Request
from starlette.responses import Response

from php_session import get_current_session_id, set_current_session_id
from php_session.contrib.starlette import PHPSessionMiddleware


def create_mock_request(cookies: dict[str, str] | None = None) -> Request:
    """Create a mock Starlette Request with optional cookies."""
    scope: dict[str, object] = {
        "type": "http",
        "method": "GET",
        "path": "/test",
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
    }
    if cookies:
        cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items())
        scope["headers"] = [(b"cookie", cookie_header.encode())]

    return Request(scope)


async def dummy_call_next(request: Request) -> Response:
    """Dummy call_next function that returns a simple response."""
    return Response(content="OK", status_code=200)


class TestPHPSessionMiddleware:
    """Tests for PHPSessionMiddleware class."""

    @pytest.fixture(autouse=True)
    def reset_context(self) -> None:
        """Reset context variables before each test."""
        set_current_session_id(None)

    @pytest.mark.asyncio
    async def test_sets_session_id_from_cookie(self) -> None:
        """Test middleware sets session_id when PHPSESSID cookie is present."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        session_id = "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6"
        request = create_mock_request(cookies={"PHPSESSID": session_id})

        captured_session_id: str | None = None

        async def capturing_call_next(req: Request) -> Response:
            nonlocal captured_session_id
            captured_session_id = get_current_session_id()
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_session_id == session_id

    @pytest.mark.asyncio
    async def test_sets_request_state_session_id(self) -> None:
        """Test middleware sets request.state.session_id."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        session_id = "b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7"
        request = create_mock_request(cookies={"PHPSESSID": session_id})

        captured_state_session_id: str | None = None

        async def capturing_call_next(req: Request) -> Response:
            nonlocal captured_state_session_id
            captured_state_session_id = getattr(req.state, "session_id", None)
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_state_session_id == session_id

    @pytest.mark.asyncio
    async def test_clears_context_after_request(self) -> None:
        """Test middleware clears context variable after request completes."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        request = create_mock_request(cookies={"PHPSESSID": "c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8"})

        await middleware.dispatch(request, dummy_call_next)

        assert get_current_session_id() is None

    @pytest.mark.asyncio
    async def test_clears_context_on_exception(self) -> None:
        """Test middleware clears context even when exception occurs."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        request = create_mock_request(cookies={"PHPSESSID": "d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9"})

        async def raising_call_next(req: Request) -> Response:
            raise ValueError("Test exception")

        with pytest.raises(ValueError, match="Test exception"):
            await middleware.dispatch(request, raising_call_next)

        assert get_current_session_id() is None

    @pytest.mark.asyncio
    async def test_no_cookie_skips_context_setup(self) -> None:
        """Test middleware skips context setup when no PHPSESSID cookie."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        request = create_mock_request(cookies={})

        captured_session_id: str | None = "should_be_none"

        async def capturing_call_next(req: Request) -> Response:
            nonlocal captured_session_id
            captured_session_id = get_current_session_id()
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_session_id is None

    @pytest.mark.asyncio
    async def test_no_request_state_when_no_cookie(self) -> None:
        """Test middleware doesn't set request.state.session_id when no cookie."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        request = create_mock_request(cookies={})

        has_session_id_attr = True

        async def capturing_call_next(req: Request) -> Response:
            nonlocal has_session_id_attr
            has_session_id_attr = hasattr(req.state, "session_id")
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert has_session_id_attr is False

    @pytest.mark.asyncio
    async def test_other_cookies_ignored(self) -> None:
        """Test middleware ignores other cookies, only reads PHPSESSID."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        request = create_mock_request(
            cookies={"other_cookie": "value", "session": "wrong"}
        )

        captured_session_id: str | None = "should_be_none"

        async def capturing_call_next(req: Request) -> Response:
            nonlocal captured_session_id
            captured_session_id = get_current_session_id()
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_session_id is None

    @pytest.mark.asyncio
    async def test_returns_response_from_call_next(self) -> None:
        """Test middleware returns the response from call_next."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        request = create_mock_request(cookies={"PHPSESSID": "f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1"})

        async def custom_call_next(req: Request) -> Response:
            return Response(content="Custom Response", status_code=201)

        response = await middleware.dispatch(request, custom_call_next)

        assert response.status_code == 201
        assert response.body == b"Custom Response"

    @pytest.mark.asyncio
    async def test_custom_cookie_name(self) -> None:
        """Test middleware can use custom cookie name."""
        middleware = PHPSessionMiddleware(app=AsyncMock(), cookie_name="MY_SESSION")
        request = create_mock_request(cookies={"MY_SESSION": "e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"})

        captured_session_id: str | None = None

        async def capturing_call_next(req: Request) -> Response:
            nonlocal captured_session_id
            captured_session_id = get_current_session_id()
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_session_id == "e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"

    @pytest.mark.asyncio
    async def test_rejects_invalid_session_id(self) -> None:
        """Test middleware rejects invalid session IDs."""
        middleware = PHPSessionMiddleware(app=AsyncMock())
        # Invalid: contains special characters
        request = create_mock_request(cookies={"PHPSESSID": "invalid<script>alert(1)</script>"})

        captured_session_id: str | None = "should_be_none"

        async def capturing_call_next(req: Request) -> Response:
            nonlocal captured_session_id
            captured_session_id = get_current_session_id()
            return Response(content="OK", status_code=200)

        await middleware.dispatch(request, capturing_call_next)

        assert captured_session_id is None


class TestPHPSessionMiddlewareIntegration:
    """Integration tests for PHPSessionMiddleware with FastAPI."""

    @pytest.mark.asyncio
    async def test_middleware_in_request_flow(self) -> None:
        """Test middleware works in a simulated request flow."""
        pytest.importorskip("fastapi")
        pytest.importorskip("httpx")
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()
        app.add_middleware(PHPSessionMiddleware)

        @app.get("/test-session")
        async def test_endpoint() -> dict[str, str | None]:
            return {"session_id": get_current_session_id()}

        # Test with PHPSESSID cookie
        session_id = "g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2"
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies={"PHPSESSID": session_id},
        ) as client:
            response = await client.get("/test-session")
            assert response.status_code == 200
            assert response.json()["session_id"] == session_id

        # Test without PHPSESSID cookie
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get("/test-session")
            assert response.status_code == 200
            assert response.json()["session_id"] is None
