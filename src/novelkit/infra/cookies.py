"""
Utility for normalizing cookie input from user configuration.
"""

__all__ = ["parse_cookies", "CookieStore"]

import json
from collections.abc import Mapping
from pathlib import Path


def parse_cookies(cookies: str | Mapping[str, str]) -> dict[str, str]:
    """Parse cookies from a string or mapping into a normalized dictionary.

    Supports input such as:

    - ``"key1=value1; key2=value2"``
    - ``{"key1": "value1", "key2": "value2"}``

    Args:
        cookies: A cookie string or a dict-like object containing cookie
            key/value pairs.

    Returns:
        A normalized cookie dictionary mapping keys to values.

    Raises:
        TypeError: If ``cookies`` is neither a string nor a mapping.
    """
    if isinstance(cookies, str):
        result: dict[str, str] = {}
        for part in cookies.split(";"):
            if "=" not in part:
                continue
            key, value = part.split("=", 1)
            key, value = key.strip(), value.strip()
            if not key:
                continue
            result[key] = value
        return result
    elif isinstance(cookies, Mapping):
        return {str(k).strip(): str(v).strip() for k, v in cookies.items()}
    raise TypeError("Unsupported cookie format: must be str or dict-like")


class CookieStore:
    """Simple cookie loader and in-memory cache for multiple client formats.

    Supported cookie files (by default):

    - ``aiohttp.cookies``
    - ``curl_cffi.cookies``
    - ``httpx.cookies``
    """

    DEFAULT_FILENAMES = ["aiohttp.cookies", "curl_cffi.cookies", "httpx.cookies"]

    def __init__(self, cookies_dir: Path, filenames: list[str] | None = None) -> None:
        """Initialize a CookieStore instance.

        Args:
            cookies_dir: Path to the directory containing cookie state files.
            filenames: Optional list of filenames to load. If omitted, defaults
                to ``DEFAULT_FILENAMES``.
        """
        self.cookies_dir = cookies_dir
        self.filenames = filenames or self.DEFAULT_FILENAMES
        self.cache: dict[str, str] = {}
        self.mtimes: dict[str, float] = {}

    def get(self, key: str) -> str:
        """Retrieve a cookie value by name.

        Args:
            key: The cookie name.

        Returns:
            str: The cookie value if present, otherwise an empty string.
        """
        self._load_all()
        return self.cache.get(key, "")

    def _load_all(self) -> None:
        """Load or refresh cookies from all configured cookie files.

        For each cookie file, this method:

        - Checks if the file exists.
        - Compares its modification time (mtime) with the last cached mtime.
        - If changed, loads and parses the JSON content.
        - Extracts each cookie's ``name`` and ``value`` fields into memory.
        """
        for filename in self.filenames:
            state_file = self.cookies_dir / filename
            if not state_file.exists():
                continue
            try:
                mtime = state_file.stat().st_mtime
                if self.mtimes.get(filename) == mtime:
                    continue
                self.mtimes[filename] = mtime
                data = json.loads(state_file.read_text(encoding="utf-8")) or []
                for c in data:
                    if "name" in c and "value" in c:
                        self.cache[c["name"]] = c["value"]
            except (OSError, json.JSONDecodeError):
                continue
