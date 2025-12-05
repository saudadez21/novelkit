import json

import pytest

from novelkit.schemas import SessionConfig

from .utils import SUPPORTED_BACKENDS, safe_create


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
def test_cookie_methods_noop_before_init(backend, tmp_path):
    cfg = SessionConfig()
    s = safe_create(backend, cfg)

    s.update_cookies({"token": "x"})
    assert s.get_cookie("token") is None
    assert s.save_cookies(tmp_path) is False
    assert s.load_cookies(tmp_path) is False
    s.clear_cookie("token")
    s.clear_cookies()


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_cookies_set_and_persist(backend, test_server, tmp_path):
    cfg = SessionConfig()
    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s1:
        await s1.get(base + "set-cookie")
        assert s1.save_cookies(tmp_path)

    async with safe_create(backend, cfg) as s2:
        assert s2.load_cookies(tmp_path)
        assert s2.get_cookie("token") == "abc123"


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_load_cookies_missing_file_after_init_returns_false(backend, tmp_path):
    cfg = SessionConfig()
    async with safe_create(backend, cfg) as s:
        assert s.load_cookies(tmp_path) is False


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_load_cookies_invalid_format_returns_false(backend, tmp_path):
    cfg = SessionConfig()

    async with safe_create(backend, cfg) as s1:
        s1.update_cookies({"x": "1"})
        assert s1.save_cookies(tmp_path)

    cookie_path = list(tmp_path.iterdir())[0]
    cookie_path.write_text("INVALID JSON", encoding="utf8")

    async with safe_create(backend, cfg) as s2:
        assert s2.load_cookies(tmp_path) is False


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_get_cookie_missing_after_init_returns_none(backend):
    cfg = SessionConfig()
    async with safe_create(backend, cfg) as s:
        assert s.get_cookie("nope") is None


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_clear_single_cookie(backend, test_server):
    cfg = SessionConfig()
    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s:
        await s.get(base + "set-cookie")
        assert s.get_cookie("token") == "abc123"

        r1 = await s.get(base + "echo-cookies")
        assert json.loads(r1.content.decode())["cookies"].get("token") == "abc123"

        s.clear_cookie("token")
        assert s.get_cookie("token") is None

        r2 = await s.get(base + "echo-cookies")
        assert "token" not in json.loads(r2.content.decode())["cookies"]


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_clear_all_cookies(backend, test_server):
    cfg = SessionConfig()
    base = str(test_server.make_url("/"))

    async with safe_create(backend, cfg) as s:
        await s.get(base + "set-cookie")
        assert s.get_cookie("token") == "abc123"

        s.clear_cookies()
        assert s.get_cookie("token") is None

        r = await s.get(base + "echo-cookies")
        assert json.loads(r.content.decode())["cookies"] == {}
