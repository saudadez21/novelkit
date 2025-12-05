import pytest

from novelkit.schemas import SessionConfig

from .utils import SUPPORTED_BACKENDS, safe_create


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_init_close_is_idempotent(backend):
    cfg = SessionConfig()
    s = safe_create(backend, cfg)

    await s.init()
    await s.init()
    await s.close()
    await s.close()


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_get_raises_before_init(backend):
    cfg = SessionConfig()
    s = safe_create(backend, cfg)

    with pytest.raises(RuntimeError):
        await s.get("http://example.com/")


@pytest.mark.parametrize("backend", sorted(SUPPORTED_BACKENDS))
@pytest.mark.asyncio
async def test_post_raises_before_init(backend):
    cfg = SessionConfig()
    s = safe_create(backend, cfg)

    with pytest.raises(RuntimeError):
        await s.post("http://example.com/", json={"x": 1})
