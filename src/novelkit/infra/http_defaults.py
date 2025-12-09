"""
Provides default HTTP headers and user-agent settings used throughout the
networking layer of NovelKit.

This module defines commonly used header presets, including default
browser-like user-agent strings, Accept headers for HTML or image
retrieval, and general-purpose request headers.
"""

# -----------------------------------------------------------------------------
# Default preferences & headers
# -----------------------------------------------------------------------------

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/136.0.0.0 Safari/537.36"
)
DEFAULT_HEADERS = {"User-Agent": DEFAULT_USER_AGENT}

DEFAULT_ACCEPT = (
    "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
)

ACCEPT_IMAGE = "image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8"

ACCEPT_AUDIO = "audio/*,*/*;q=0.8"
ACCEPT_BINARY = "*/*"

DEFAULT_USER_HEADERS = {
    "Accept": DEFAULT_ACCEPT,
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "en,zh;q=0.9,zh-CN;q=0.8",
    "User-Agent": DEFAULT_USER_AGENT,
    "Connection": "keep-alive",
}

MEDIA_ACCEPT_MAP: dict[str, str] = {
    "image": ACCEPT_IMAGE,
    "audio": ACCEPT_AUDIO,
    "font": ACCEPT_BINARY,
    "css": ACCEPT_BINARY,
    "script": ACCEPT_BINARY,
    "other": ACCEPT_BINARY,
}
