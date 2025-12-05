from __future__ import annotations

import base64

import aiohttp
import aiohttp.web
import pytest
import pytest_asyncio


@pytest.fixture(autouse=True)
def allow_ip_cookies(monkeypatch):
    """Allow cookie acceptance for localhost tests."""
    import aiohttp.cookiejar

    monkeypatch.setattr(aiohttp.cookiejar, "is_ip_address", lambda host: False)


@pytest_asyncio.fixture
async def test_server(aiohttp_server):
    async def handler_ok(request):
        return aiohttp.web.Response(text="hello", status=200)

    async def handler_post(request):
        data = await request.json()
        return aiohttp.web.json_response({"received": data})

    async def handler_set_cookie(request):
        resp = aiohttp.web.Response(text="cookie!")
        resp.set_cookie("token", "abc123")
        return resp

    async def handler_redirect(request):
        raise aiohttp.web.HTTPFound("/ok")

    async def handler_echo_headers(request):
        return aiohttp.web.json_response({"headers": dict(request.headers)})

    async def handler_echo_cookies(request):
        return aiohttp.web.json_response({"cookies": dict(request.cookies)})

    app = aiohttp.web.Application()
    app.router.add_get("/ok", handler_ok)
    app.router.add_post("/post", handler_post)
    app.router.add_get("/set-cookie", handler_set_cookie)
    app.router.add_get("/redirect", handler_redirect)
    app.router.add_get("/echo-headers", handler_echo_headers)
    app.router.add_get("/echo-cookies", handler_echo_cookies)

    server = await aiohttp_server(app)
    return server


@pytest_asyncio.fixture
async def proxy_noauth_server(aiohttp_server):
    """Proxy that always returns 200 'proxied'."""
    seen = {"count": 0, "methods": [], "paths": []}

    async def handler(request):
        seen["count"] += 1
        seen["methods"].append(request.method)
        seen["paths"].append(request.raw_path)
        return aiohttp.web.Response(text="proxied", status=200)

    app = aiohttp.web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)
    server = await aiohttp_server(app)
    server.seen = seen
    return server


@pytest_asyncio.fixture
async def proxy_auth_server(aiohttp_server):
    """Proxy enforcing Basic authentication."""
    required_user = "user1"
    required_pass = "pass1"
    token = base64.b64encode(f"{required_user}:{required_pass}".encode()).decode()
    required_header = f"Basic {token}"

    seen = {
        "count": 0,
        "auth_headers": [],
        "authed_count": 0,
        "challenged_count": 0,
    }

    async def handler(request):
        seen["count"] += 1
        auth = request.headers.get("Proxy-Authorization")
        if auth:
            seen["auth_headers"].append(auth)

        if auth != required_header:
            seen["challenged_count"] += 1
            return aiohttp.web.Response(
                text="proxy auth required",
                status=407,
                headers={"Proxy-Authenticate": "Basic"},
            )

        seen["authed_count"] += 1
        return aiohttp.web.Response(text="proxied", status=200)

    app = aiohttp.web.Application()
    app.router.add_route("*", "/{tail:.*}", handler)

    server = await aiohttp_server(app)
    server.required_user = required_user
    server.required_pass = required_pass
    server.required_header = required_header
    server.seen = seen
    return server
