"""
Utility for resolving a novel site URL into a standardized configuration.
"""

from __future__ import annotations

__all__ = ["resolve_book_url"]

import logging
import re
from collections.abc import Callable
from typing import TypedDict, TypeVar
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

BookURLFunc = Callable[[str, str], "BookURLInfo | None"]
E = TypeVar("E", bound=BookURLFunc)
_REGISTRY: dict[str, BookURLFunc] = {}


class BookURLInfo(TypedDict):
    """Structured result returned after resolving a book or chapter URL.

    Attributes:
        site_key: Identifier of the site (e.g., ``"aaatxt"``).
        book_id: Extracted book ID, or ``None`` if not applicable.
        chapter_id: Extracted chapter ID, or ``None`` if not applicable.
    """

    site_key: str
    book_id: str | None
    chapter_id: str | None


def register_extractor(hosts: list[str]) -> Callable[[E], E]:
    """Register a URL extractor function for specific host names.

    Args:
        hosts: Hostnames that should be handled by the decorated extractor.
    """

    def decorator(func: E) -> E:
        for host in hosts:
            _REGISTRY[host] = func
        return func

    return decorator


def _normalize_host_and_path(url: str) -> tuple[str, str, str]:
    """Normalize a URL into canonical host, path, and query components.

    Args:
        url: Raw URL string provided by the caller.

    Returns:
        A tuple ``(host, path, query)`` where all values are normalized.
    """
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    parsed = urlparse(url)
    return parsed.netloc.lower(), parsed.path or "/", parsed.query or ""


def _make_info(
    site_key: str, book_id: str | None, chap_id: str | None = None
) -> BookURLInfo:
    """Build a standardized :class:`BookURLInfo` entry.

    Args:
        site_key: Site identifier.
        book_id: Extracted book ID or ``None``.
        chap_id: Extracted chapter ID or ``None``.
    """
    return {
        "site_key": site_key,
        "book_id": book_id,
        "chapter_id": chap_id,
    }


def resolve_book_url(url: str) -> BookURLInfo | None:
    """Resolve a full novel-site URL into standardized metadata.

    Resolution is based on extractor functions previously registered via
    :func:`register_extractor`.

    Args:
        url: The URL string to resolve.

    Returns:
        Parsed URL information if the host is recognized and succeeds
    """
    host, path, query = _normalize_host_and_path(url)
    if extractor := _REGISTRY.get(host):
        return extractor(path, query)
    return None


@register_extractor(["www.aaatxt.com"])
def extract_aaatxt(path: str, query: str) -> BookURLInfo | None:
    if m := re.search("^/shu/(\\d+)\\.html$", path):
        return _make_info("aaatxt", m.group(1), None)
    if m := re.search(r"^/yuedu/(\d+)_(\d+)\.html$", path):
        return _make_info("aaatxt", m.group(1), m.group(2))
    return None


@register_extractor(["www.akatsuki-novels.com"])
def extract_akatsuki_novels(path: str, query: str) -> BookURLInfo | None:
    if m := re.search("/stories/view/(\\d+)/novel_id~(\\d+)", path):
        return _make_info("akatsuki_novels", m.group(2), m.group(1))
    if m := re.search("novel_id~(\\d+)", path):
        return _make_info("akatsuki_novels", m.group(1), None)
    return None
