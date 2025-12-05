import pytest

from novelkit.schemas import SessionConfig

from .utils import SUPPORTED_BACKENDS, safe_create


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_proxy_basic_routing(backend, test_server, proxy_noauth_server):
    cfg = SessionConfig(
        proxy=str(proxy_noauth_server.make_url("/")),
        trust_env=False,
    )
    ok_url = str(test_server.make_url("/ok"))

    async with safe_create(backend, cfg) as s:
        r = await s.get(ok_url)

    assert r.content == b"proxied"
    assert proxy_noauth_server.seen["count"] >= 1


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_proxy_authentication(backend, test_server, proxy_auth_server):
    cfg = SessionConfig(
        proxy=str(proxy_auth_server.make_url("/")),
        proxy_user=proxy_auth_server.required_user,
        proxy_pass=proxy_auth_server.required_pass,
        trust_env=False,
    )
    ok_url = str(test_server.make_url("/ok"))

    async with safe_create(backend, cfg) as s:
        r = await s.get(ok_url)

    assert r.content == b"proxied"
    assert proxy_auth_server.seen["authed_count"] >= 1
    assert proxy_auth_server.required_header in proxy_auth_server.seen["auth_headers"]


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_proxy_url_embedded_credentials(backend, test_server, proxy_auth_server):
    """
    Proxy authentication via URL-embedded credentials:
        http://user:pass@host:port
    """
    # Build URL: http://user1:pass1@localhost:port/
    base_url = str(proxy_auth_server.make_url("/"))
    url_with_auth = base_url.replace(
        "://",
        f"://{proxy_auth_server.required_user}:{proxy_auth_server.required_pass}@",
    )

    cfg = SessionConfig(
        proxy=url_with_auth,
        trust_env=False,
    )

    ok_url = str(test_server.make_url("/ok"))

    async with safe_create(backend, cfg) as s:
        r = await s.get(ok_url)

    assert r.content == b"proxied"
    assert proxy_auth_server.required_header in proxy_auth_server.seen["auth_headers"]
    assert proxy_auth_server.seen["authed_count"] >= 1
