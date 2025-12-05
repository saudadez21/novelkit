import json

import pytest

from novelkit.schemas import SessionConfig

from .utils import SUPPORTED_BACKENDS, safe_create


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_basic_get_post(backend, test_server):
    cfg = SessionConfig()
    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s:
        r1 = await s.get(base + "ok")
        assert r1.status == 200
        assert r1.content == b"hello"

        r2 = await s.post(base + "post", json={"a": 1})
        assert json.loads(r2.content.decode()) == {"received": {"a": 1}}


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_redirect_behavior(backend, test_server):
    cfg = SessionConfig()
    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s:
        r_follow = await s.get(base + "redirect", allow_redirects=True)
        assert r_follow.status == 200

        r_no_follow = await s.get(base + "redirect", allow_redirects=False)
        assert 300 <= r_no_follow.status < 400


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_verify_and_redirect_kwargs_pass_through(backend, test_server):
    cfg = SessionConfig()
    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s:
        await s.get(base + "ok", verify=False, allow_redirects=False)
        await s.post(base + "post", json={"x": 1}, verify=False, allow_redirects=True)


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
def test_headers_property_returns_copy(backend):
    cfg = SessionConfig(headers={"A": "1", "B": "2"})
    s = safe_create(backend, cfg)

    h1 = s.headers
    h1["A"] = "999"
    h1["C"] = "new"

    assert s.headers == {"A": "1", "B": "2"}


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_user_agent_override_sent_to_server(backend, test_server):
    custom_ua = "NovelKitTestAgent/1.0"
    cfg = SessionConfig(user_agent=custom_ua)

    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s:
        r = await s.get(base + "echo-headers")
        headers = json.loads(r.content.decode())["headers"]

    assert headers.get("User-Agent") == custom_ua
