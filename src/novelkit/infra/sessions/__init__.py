"""
Session management utilities for NovelKit's infrastructure layer.

This module provides a unified interface for creating HTTP session
backends and defines the base abstractions used across the networking
components.
"""

__all__ = ["create_session", "BaseSession"]

from typing import Any

from novelkit.schemas import SessionConfig

from .base import BaseSession


def create_session(
    backend: str,
    cfg: SessionConfig | None = None,
    **kwargs: Any,
) -> BaseSession:
    """Creates and returns a session backend instance.

    Supported backends:
        * "aiohttp"
        * "httpx"
        * "curl_cffi"

    Args:
        backend: Name of the backend to use.
        cfg: Optional session configuration to pass to the backend.
        **kwargs: Additional keyword arguments forwarded directly to the
            backend constructor.

    Returns:
        BaseSession: An initialized session instance for the selected backend.

    Raises:
        ValueError: If the specified backend name is not supported.
    """
    match backend:
        case "aiohttp":
            from ._aiohttp import AiohttpSession

            return AiohttpSession(cfg, **kwargs)
        case "httpx":
            from ._httpx import HttpxSession

            return HttpxSession(cfg, **kwargs)
        case "curl_cffi":
            from ._curl_cffi import CurlCffiSession

            return CurlCffiSession(cfg, **kwargs)
        case _:
            raise ValueError(f"Unsupported backend: {backend!r}")
