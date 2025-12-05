from __future__ import annotations

from typing import Any

import pytest

from novelkit.infra.sessions import create_session
from novelkit.infra.sessions.base import BaseSession
from novelkit.schemas import SessionConfig

SUPPORTED_BACKENDS: set[str] = {"aiohttp", "httpx", "curl_cffi"}


def safe_create(
    backend: str, cfg: SessionConfig, cookies: dict[str, str] | None = None, **kw: Any
) -> BaseSession:
    """
    Create backend instance, skipping test if backend dependency is missing.
    """
    try:
        return create_session(backend, cfg, cookies=cookies, **kw)
    except ImportError as e:
        pytest.skip(f"backend {backend!r} not installed: {e}")
